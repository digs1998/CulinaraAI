import os
import json
import html
import numpy as np
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# ChromaDB
from chromadb import Client
from chromadb.config import Settings

# MCP tools
from services.mcp_tools import get_mcp_tools
from services.mcp_orchestrator import MCPOrchestrator

load_dotenv()

class RecipeRAGEngine:
    """
    Recipe RAG Engine with ChromaDB + MCP Fallback + LLM Generation
    """

    def __init__(self, chroma_dir: str = "./chroma_db"):
        load_dotenv()

        # ---- Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model = "models/text-embedding-004"
        self.generation_model = "gemini-2.0-flash-exp"

        # ---- ChromaDB
        self.client = Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=chroma_dir))
        self.collection = self.client.get_collection("recipes")

        # ---- MCP tools
        self.mcp_tools = get_mcp_tools()
        self.mcp_orchestrator = None

    # -------------------- MCP Orchestrator --------------------
    def setup_mcp_orchestrator(self):
        if self.mcp_orchestrator is None:
            self.mcp_orchestrator = MCPOrchestrator(self, self.mcp_tools)

    # -------------------- Embeddings --------------------
    def embed_query(self, query: str) -> np.ndarray:
        result = genai.embed_content(
            model=self.embedding_model,
            content=query,
            task_type="retrieval_query"
        )
        return np.array(result["embedding"])

    # -------------------- Keyword Extraction --------------------
    def _extract_key_terms(self, query: str) -> tuple[List[str], List[str]]:
        common_ingredients = {
            'chicken', 'beef', 'pork', 'lamb', 'fish', 'salmon', 'tuna', 'shrimp', 'prawn',
            'paneer', 'tofu', 'tempeh', 'seitan',
            'cheese', 'mozzarella', 'cheddar', 'feta', 'ricotta',
            'mushroom', 'eggplant', 'zucchini', 'tomato', 'potato', 'onion', 'garlic',
            'rice', 'pasta', 'noodle', 'bread'
        }
        stop_words = {'how', 'to', 'make', 'recipe', 'for', 'a', 'an', 'the', 'with', 'and', 'or', 'of', 'in'}
        query_lower = query.lower()
        all_terms = [word.rstrip('?') for word in query_lower.split() if word.rstrip('?') not in stop_words and len(word.rstrip('?')) > 2]
        ingredient_terms = [term for term in all_terms if term in common_ingredients]
        return all_terms, ingredient_terms

    # -------------------- Keyword Match Check --------------------
    def _check_keyword_match(self, all_terms, ingredient_terms, text):
        text = text.lower()
        ingredient_conflicts = {
            "chicken": ["tofu", "paneer", "vegetarian", "vegan"],
            "paneer": ["chicken", "beef", "pork"],
            "tofu": ["chicken", "beef", "pork"]
        }
        for ing in ingredient_terms:
            conflicts = ingredient_conflicts.get(ing, [])
            if any(c in text for c in conflicts):
                return -0.3, False
        for ing in ingredient_terms:
            if ing not in text:
                return -0.2, False
        matches = sum(1 for t in all_terms if t in text)
        boost = min(0.15, matches * 0.03)
        return boost, True

    # -------------------- Recipe Search --------------------
    def search_recipes(self, query: str, top_k: int = 5, filters: Optional[Dict] = None, min_score: float = 0.0) -> List[Dict]:
        all_terms, ingredient_terms = self._extract_key_terms(query)
        query_embedding = self.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k*3,
            include=["metadatas", "documents", "distances"]
        )

        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        filtered_results = []

        for i, meta in enumerate(metadatas):
            text_blob = f"{meta.get('title','')} {meta.get('category','')} {meta.get('cuisine','')} {meta.get('ingredients','')}"
            boost, valid = self._check_keyword_match(all_terms, ingredient_terms, text_blob)
            similarity = max(0.0, min(1.0, 1 - distances[i] + boost))

            # Apply filters
            passes_filter = True
            if filters:
                for k, v in filters.items():
                    val = meta.get(k, '').lower() if meta.get(k) else ''
                    if isinstance(v, str):
                        if val != v.lower():
                            passes_filter = False
                    elif isinstance(v, list):
                        if val not in [x.lower() for x in v]:
                            passes_filter = False

            if similarity >= min_score and valid and passes_filter:
                filtered_results.append({
                    "id": meta['id'],
                    "score": similarity,
                    "metadata": meta,
                    "keyword_match": valid
                })

        filtered_results.sort(key=lambda x: x['score'], reverse=True)
        return filtered_results[:top_k]

    # -------------------- Recipe Details --------------------
    def get_recipe_details(self, recipe_id: str) -> Optional[Dict]:
        result = self.collection.get(ids=[recipe_id])
        if not result['metadatas'] or len(result['metadatas'][0]) == 0:
            return None
        return result['metadatas'][0][0]

    # -------------------- Similar Recipes --------------------
    def get_similar_recipes(self, recipe_id: str, top_k: int = 5) -> List[Dict]:
        recipe = self.get_recipe_details(recipe_id)
        if not recipe or 'embedding' not in recipe:
            return []

        results = self.collection.query(
            query_embeddings=[recipe['embedding']],
            n_results=top_k+1,
            include=["metadatas", "documents", "distances"]
        )

        similar = []
        for meta, dist in zip(results['metadatas'][0], results['distances'][0]):
            if meta['id'] == recipe_id:
                continue
            similar.append({
                "id": meta['id'],
                "score": 1 - dist,
                "metadata": meta
            })
        return similar[:top_k]

    # -------------------- Recipe Context --------------------
    def get_recipe_context(self, recipe_ids: List[str], detailed: bool = True) -> str:
        context_parts = []
        for rid in recipe_ids:
            meta = self.get_recipe_details(rid)
            if not meta:
                continue
            if detailed:
                context = f"""
                    Recipe: {meta['title']}
                    Category: {meta.get('category', 'N/A')}
                    Cuisine: {meta.get('cuisine', 'N/A')}
                    Prep Time: {meta.get('prep_time', 'N/A')}
                    Cook Time: {meta.get('cook_time', 'N/A')}
                    Total Time: {meta.get('total_time', 'N/A')}
                    Servings: {meta.get('servings', 'N/A')}
                    Calories: {meta.get('calories', 'N/A')}
                    Ingredients: {meta.get('ingredient_count', 'N/A')} items
                    Instructions: {meta.get('step_count', 'N/A')} steps
                    URL: {meta.get('url', 'N/A')}
                    """
            else:
                context = f"{meta['title']} - {meta.get('category','N/A')} ({meta.get('total_time','N/A')}) | Rating: {meta.get('rating','N/A')}/5 | URL: {meta.get('url','N/A')}"
            context_parts.append(context.strip())
        return "\n\n---\n\n".join(context_parts)

    # -------------------- LLM Recipe Suggestion --------------------
    def generate_recipe_suggestion(self, query: str) -> str:
        all_terms, ingredient_terms = self._extract_key_terms(query)
        web_query = f"{query} with {' '.join(ingredient_terms)}" if ingredient_terms else query

        search = self.mcp_tools.search_recipe_web(query=web_query, max_results=5)

        if not search.get("success") or not search.get("results"):
            protein = ", ".join(ingredient_terms) if ingredient_terms else "your preference"
            return f"I couldn’t find a recipe for **{query}** using **{protein}**. Try relaxing ingredients or checking online sources!"

        # Fetch top recipe
        recipe_url = search["results"][0]["url"]
        recipe = self.mcp_tools.fetch_recipe_from_url(recipe_url)
        if not recipe.get("success"):
            return f"I found a recipe URL but couldn't fetch details. Try visiting {recipe_url}"

        model = genai.GenerativeModel(
            model_name=self.generation_model,
            system_instruction="""
                You may ONLY summarize the provided recipe.
                Do NOT invent ingredients or steps.
                Do NOT substitute proteins.
            """
        )
        prompt = f"""
User query: {query}
Title: {recipe.get('title')}
Ingredients: {recipe.get('ingredients')}
Instructions: {recipe.get('instructions')}
Source: {recipe.get('url')}
"""
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 800}
        )
        return response.text

    # -------------------- Answer Question --------------------
    def answer_question(self, question: str, top_k: int = 3,
                        filters: Optional[Dict] = None,
                        similarity_threshold: float = 0.5,
                        use_mcp_orchestrator: bool = True) -> Dict:
        if use_mcp_orchestrator:
            self.setup_mcp_orchestrator()
            orchestrator_result = self.mcp_orchestrator.process_query(
                query=question,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            return {
                "question": question,
                "response": orchestrator_result["message"],
                "context": None,
                "sources": orchestrator_result.get("recipes", []),
                "top_recipe": orchestrator_result["recipes"][0] if orchestrator_result["recipes"] else None,
                "generated": not orchestrator_result["has_database_results"],
                "mcp_result": orchestrator_result
            }

        results = self.search_recipes(question, top_k=top_k, filters=filters, min_score=similarity_threshold)
        if not results:
            return {
                "question": question,
                "response": self.generate_recipe_suggestion(question),
                "context": None,
                "sources": [],
                "top_recipe": None,
                "generated": True,
                "message": "No database matches."
            }

        context = self.get_recipe_context([r['id'] for r in results], detailed=True)
        return {
            "question": question,
            "response": None,
            "context": context,
            "sources": results,
            "top_recipe": results[0],
            "generated": False
        }

    # -------------------- Statistics --------------------
    def get_statistics(self) -> Dict:
        metadatas = self.collection.get(include=["metadatas"])['metadatas'][0]
        categories, cuisines, ratings = {}, {}, []
        for meta in metadatas:
            categories[meta.get('category','Unknown')] = categories.get(meta.get('category','Unknown'),0)+1
            if meta.get('cuisine'):
                cuisines[meta.get('cuisine')] = cuisines.get(meta.get('cuisine'),0)+1
            if meta.get('rating'):
                ratings.append(float(meta['rating']))
        return {
            "total_recipes": len(metadatas),
            "categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
            "cuisines": dict(sorted(cuisines.items(), key=lambda x: x[1], reverse=True)),
            "average_rating": np.mean(ratings) if ratings else 0,
            "top_categories": list(categories.keys())[:5],
            "top_cuisines": list(cuisines.keys())[:5] if cuisines else []
        }



# Example usage and testing
if __name__ == "__main__":
    print("🚀 Recipe RAG Engine - Enhanced Version")
    print("="*80)
    
    # Initialize RAG engine
    rag = RecipeRAGEngine()
    
    # Show statistics
    print("\n📊 Recipe Database Statistics:")
    stats = rag.get_statistics()
    print(f"   Total recipes: {stats['total_recipes']}")
    print(f"   Average rating: {stats['average_rating']:.2f}/5")
    print(f"   Top categories: {', '.join(stats['top_categories'])}")
    if stats['top_cuisines']:
        print(f"   Top cuisines: {', '.join(stats['top_cuisines'])}")
    
    # Test queries
    print("\n" + "="*80)
    print("🔍 Testing Search Queries")
    print("="*80)
    
    queries = [
        {"query": "quick chicken dinner", "filters": None},
        {"query": "healthy vegetarian recipes", "filters": None},
        {"query": "chocolate dessert", "filters": None},
        {"query": "pasta", "filters": {"category": "Chicken"}},
    ]
    
    for test in queries:
        query = test["query"]
        filters = test["filters"]
        
        print(f"\n🔍 Query: '{query}'")
        if filters:
            print(f"   Filters: {filters}")
        
        results = rag.search_recipes(query, top_k=3, filters=filters)
        
        if results:
            print(f"\n   Top 3 results:")
            for i, result in enumerate(results):
                meta = result['metadata']
                print(f"\n   {i+1}. {meta['title']}")
                print(f"      Score: {result['score']:.4f}")
                print(f"      Category: {meta.get('category', 'N/A')}")
                print(f"      Time: {meta.get('total_time', 'N/A')}")
                print(f"      Rating: {meta.get('rating', 'N/A')}/5")
                print(f"      URL: {meta.get('url', 'N/A')}")
        else:
            print("   No results found")
    
    # Test similar recipes
    print("\n" + "="*80)
    print("🔗 Testing Similar Recipes")
    print("="*80)
    
    if len(rag.ids) > 0:
        test_recipe_id = rag.ids[0]
        recipe_details = rag.get_recipe_details(test_recipe_id)
        print(f"\nBase Recipe: {recipe_details['title']}")
        
        similar = rag.get_similar_recipes(test_recipe_id, top_k=3)
        print(f"\nSimilar recipes:")
        for i, result in enumerate(similar):
            meta = result['metadata']
            print(f"   {i+1}. {meta['title']} (similarity: {result['score']:.4f})")
    
    # Test full RAG answer
    print("\n" + "="*80)
    print("💬 Testing RAG Answer Generation")
    print("="*80)
    
    answer = rag.answer_question("What's a good recipe for a quick weeknight dinner?", top_k=2)
    print(f"\nQuestion: {answer['question']}")
    print(f"\nContext generated for LLM:")
    print(answer['context'][:500] + "...")
    print(f"\nNumber of sources: {len(answer['sources'])}")
    
    print("\n" + "="*80)
    print("✅ All tests complete!")
    print("="*80)