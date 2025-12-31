import os
import numpy as np
from typing import List, Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# MCP tools
from services.mcp_tools import get_mcp_tools
from services.mcp_orchestrator import MCPOrchestrator

load_dotenv()


class RecipeRAGEngine:
    """
    Recipe RAG Engine
    Uses:
      - ChromaDB collection (injected)
      - Gemini embeddings + generation
      - MCP orchestration fallback
    """

    def __init__(self, chroma_collection):
        """
        chroma_collection: chromadb.api.models.Collection.Collection
        """
        # ---------------- Gemini ----------------
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        self.embedding_model = "models/text-embedding-004"
        self.generation_model = "gemini-2.0-flash-exp"

        # ---------------- Chroma ----------------
        self.collection = chroma_collection

        # ---------------- MCP ----------------
        self.mcp_tools = get_mcp_tools()
        self.mcp_orchestrator: Optional[MCPOrchestrator] = None

    # -------------------- MCP Orchestrator --------------------

    def setup_mcp_orchestrator(self):
        if self.mcp_orchestrator is None:
            self.mcp_orchestrator = MCPOrchestrator(self, self.mcp_tools)

    # -------------------- Embeddings --------------------

    def embed_query(self, query: str) -> np.ndarray:
        result = genai.embed_content(
            model=self.embedding_model,
            content=query,
            task_type="retrieval_query",
        )
        return np.array(result["embedding"], dtype=np.float32)

    # -------------------- Keyword Utilities --------------------

    def _extract_key_terms(self, query: str):
        """Extract searchable terms from query"""
        common_ingredients = {
            "chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna",
            "shrimp", "prawn", "paneer", "tofu", "cheese", "mushroom", 
            "tomato", "potato", "onion", "garlic", "ginger", "rice", 
            "pasta", "noodle", "bread", "egg", "spinach", "beans",
            "lentil", "dal", "curry", "tikka", "masala", "biryani",
        }

        cooking_methods = {
            "grilled", "fried", "baked", "roasted", "steamed", "boiled",
            "sauteed", "stir-fry", "slow-cook", "instant", "quick",
        }

        meal_types = {
            "breakfast", "lunch", "dinner", "snack", "appetizer", 
            "dessert", "soup", "salad", "main", "side",
        }

        stop_words = {
            "how", "to", "make", "recipe", "for", "a", "an",
            "the", "with", "and", "or", "of", "in", "some", "get", "me",
        }

        # Extract words
        words = [
            w.strip("?,.!").lower()
            for w in query.split()
            if w.lower() not in stop_words and len(w) > 2
        ]

        # Categorize terms
        ingredients = [w for w in words if w in common_ingredients]
        methods = [w for w in words if w in cooking_methods]
        meal_type = [w for w in words if w in meal_types]
        
        # All searchable terms
        all_terms = list(set(ingredients + methods + meal_type + words))
        
        return all_terms, ingredients, methods, meal_type
    
    def search_recipes(self, query: str, top_k: int = 5, min_score: float = 0.35):
        """
        MCP compatibility wrapper.
        Internally uses Chroma search with balanced threshold for reliable results.
        """
        return self.search_chroma(
            query=query,
            top_k=top_k,
            filters=None,
            min_score=min_score  # Pass through threshold parameter
        )

    def _check_keyword_match(self, all_terms, ingredient_terms, methods, text):
        """
        Improved keyword matching - more lenient
        Returns: (boost_score, has_keyword_match, match_details)
        """
        text = text.lower()

        # Check for conflicting ingredients (optional filtering)
        ingredient_conflicts = {
            "chicken": ["tofu", "vegan", "vegetarian"],
            "tofu": ["chicken", "beef", "pork", "meat"],
            "paneer": [],  # Paneer rarely conflicts
            "beef": ["vegan", "vegetarian"],
            "pork": ["halal", "kosher"],
        }

        # Soft conflict check - don't reject, just reduce score slightly
        conflict_penalty = 0.0
        for ing in ingredient_terms:
            for conflict in ingredient_conflicts.get(ing, []):
                if conflict in text:
                    conflict_penalty -= 0.1  # Small penalty, not rejection

        # Check if ANY ingredient term matches (not all required)
        ingredient_matches = sum(1 for ing in ingredient_terms if ing in text)
        has_ingredient_match = ingredient_matches > 0
        
        # Check if ANY cooking method matches
        method_matches = sum(1 for method in methods if method in text)
        
        # Check overall term matches
        overall_matches = sum(1 for t in all_terms if t in text)
        
        # Calculate boost based on matches
        boost = 0.0
        
        # Boost for ingredient matches (most important)
        if ingredient_matches > 0:
            boost += min(0.20, ingredient_matches * 0.08)
        
        # Boost for method matches
        if method_matches > 0:
            boost += min(0.10, method_matches * 0.05)
        
        # Boost for overall term matches
        if overall_matches > 0:
            boost += min(0.15, overall_matches * 0.03)
        
        # Apply conflict penalty
        boost += conflict_penalty
        
        # Has keyword match if we found ingredients OR methods OR multiple terms
        has_keyword_match = (
            ingredient_matches > 0 or 
            method_matches > 0 or 
            overall_matches >= 2
        )
        
        match_details = {
            "ingredient_matches": ingredient_matches,
            "method_matches": method_matches,
            "overall_matches": overall_matches,
        }

        return boost, has_keyword_match, match_details

    # -------------------- Search --------------------

    def _parse_metadata(self, meta: dict) -> dict:
        """
        Parse JSON strings back to Python objects for ingredients/instructions
        """
        import json
        
        parsed = meta.copy()
        
        # Parse JSON string fields back to lists/dicts
        for key in ['ingredients', 'instructions']:
            if key in parsed and isinstance(parsed[key], str):
                try:
                    parsed[key] = json.loads(parsed[key])
                except:
                    # If parsing fails, treat as single-item list
                    parsed[key] = [parsed[key]]
        
        # Parse facts if stored as JSON string
        if 'facts' in parsed and isinstance(parsed['facts'], str):
            try:
                parsed['facts'] = json.loads(parsed['facts'])
            except:
                parsed['facts'] = {}
        
        # Build facts from individual fields if not already a dict
        if 'facts' not in parsed or not parsed['facts']:
            parsed['facts'] = {}
            for key in ['prep_time', 'cook_time', 'total_time', 'servings', 'calories']:
                if key in parsed and parsed[key]:
                    parsed['facts'][key] = parsed[key]
        
        return parsed

    def search_chroma(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        min_score: float = 0.35,  # Balanced threshold for reliable results
    ) -> List[Dict]:
        """
        Search ChromaDB with semantic similarity + keyword matching
        """
        print(f"    🔍 Searching ChromaDB for: '{query}'")
        print(f"    📊 Parameters: top_k={top_k}, min_score={min_score}")

        # Extract search terms
        all_terms, ingredient_terms, methods, meal_types = self._extract_key_terms(query)
        print(f"    🔑 Key terms: {all_terms[:5]}")
        print(f"    🥘 Ingredients: {ingredient_terms}")
        print(f"    👨‍🍳 Methods: {methods}")
        
        # Get embedding
        embedding = self.embed_query(query)

        # Query ChromaDB - get more results for filtering
        results = self.collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=min(top_k * 5, 50),  # Get more candidates
            include=["metadatas", "distances"],
        )

        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        if not metadatas:
            print(f"    ⚠️ No results from ChromaDB")
            return []

        print(f"    📋 ChromaDB returned {len(metadatas)} candidates")

        final = []

        for meta, dist in zip(metadatas, distances):
            # Create searchable text blob from metadata
            text_blob = " ".join([
                str(meta.get("title", "")),
                str(meta.get("category", "")),
                str(meta.get("cuisine", "")),
                " ".join(meta.get("ingredients", [])) if isinstance(meta.get("ingredients"), list) else str(meta.get("ingredients", "")),
            ])

            # Check keyword matching
            boost, has_keyword_match, match_details = self._check_keyword_match(
                all_terms, ingredient_terms, methods, text_blob
            )

            # Calculate final score (distance is 0-2, similarity is 1-distance)
            # Keep score in 0-1 range, don't multiply by 100 here
            base_score = max(0.0, 1.0 - dist)  # Convert distance to similarity (0-1)
            final_score = max(0.0, min(1.0, base_score + boost))  # Add boost, clamp to 0-1

            # Log matching details for debugging
            title = meta.get("title", "Unknown")[:40]
            print(f"      • {title}: base={base_score:.3f}, boost={boost:.3f}, final={final_score:.3f}, keyword={has_keyword_match}")

            # Skip if below threshold (but keep if strong keyword match)
            if final_score < min_score and not (has_keyword_match and base_score > 0.30):
                continue

            # Apply additional filters if provided
            if filters:
                passed = True
                for k, v in filters.items():
                    val = str(meta.get(k, "")).lower()
                    if isinstance(v, str) and val != v.lower():
                        passed = False
                    if isinstance(v, list) and val not in [x.lower() for x in v]:
                        passed = False
                if not passed:
                    continue

            # Add to results
            final.append({
                "id": meta.get("id", "unknown"),
                "score": final_score,
                "metadata": self._parse_metadata(meta),  # Parse JSON strings back to lists
                "keyword_match": has_keyword_match,
                "match_details": match_details,
            })

        # Sort by score
        final.sort(key=lambda x: x["score"], reverse=True)
        
        top_results = final[:top_k]
        print(f"    ✅ Returning {len(top_results)} results (after filtering)")
        
        return top_results

    # -------------------- Recipe Context --------------------
    
    def get_recipe_context(self, recipe_ids: List[str], detailed: bool = True) -> str:
        """
        Get formatted recipe context for LLM summarization
        """
        context = ""
        
        for recipe_id in recipe_ids:
            result = self.collection.get(ids=[recipe_id], include=["metadatas"])
            
            if not result["metadatas"] or not result["metadatas"][0]:
                continue
            
            meta = self._parse_metadata(result["metadatas"][0])  # Parse JSON strings
            
            context += f"\n{'='*50}\n"
            context += f"Recipe: {meta.get('title', 'Unknown')}\n"
            
            if detailed:
                # Ingredients
                ingredients = meta.get('ingredients', [])
                if ingredients:
                    context += "\nIngredients:\n"
                    for ing in ingredients[:15]:
                        context += f"- {ing}\n"
                
                # Instructions
                instructions = meta.get('instructions', [])
                if instructions:
                    context += "\nInstructions:\n"
                    for i, step in enumerate(instructions[:10], 1):
                        context += f"{i}. {step}\n"
                
                # Facts
                if meta.get('prep_time') or meta.get('cook_time'):
                    context += "\nDetails:\n"
                    if meta.get('prep_time'):
                        context += f"- Prep Time: {meta['prep_time']}\n"
                    if meta.get('cook_time'):
                        context += f"- Cook Time: {meta['cook_time']}\n"
                    if meta.get('total_time'):
                        context += f"- Total Time: {meta['total_time']}\n"
                    if meta.get('servings'):
                        context += f"- Servings: {meta['servings']}\n"
                    if meta.get('calories'):
                        context += f"- Calories: {meta['calories']}\n"
            
            if meta.get('url'):
                context += f"\nSource: {meta['url']}\n"
        
        return context

    # -------------------- Recipe Details --------------------

    def get_recipe_details(self, recipe_id: str) -> Optional[Dict]:
        result = self.collection.get(ids=[recipe_id])
        if not result["metadatas"] or not result["metadatas"][0]:
            return None
        return self._parse_metadata(result["metadatas"][0])  # Parse JSON strings

    # -------------------- Similar Recipes --------------------

    def get_similar_recipes(self, recipe_id: str, top_k: int = 5) -> List[Dict]:
        recipe = self.get_recipe_details(recipe_id)
        if not recipe:
            return []

        # Get recipe embedding from metadata or re-embed title
        if "embedding" in recipe:
            query_embedding = recipe["embedding"]
        else:
            # Re-embed using title
            query_embedding = self.embed_query(recipe.get("title", "")).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k + 1,
            include=["metadatas", "distances"],
        )

        similar = []
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            if meta.get("id") == recipe_id:
                continue
            similar.append({
                "id": meta.get("id"),
                "score": 1 - dist,
                "metadata": meta,
            })

        return similar[:top_k]

    # -------------------- LLM Generation --------------------

    def generate_recipe_suggestion(self, query: str) -> str:
        search = self.mcp_tools.search_recipe_web(query=query, max_results=5)

        if not search.get("success") or not search.get("results"):
            return f"I couldn't find a recipe for **{query}**."

        recipe_url = search["results"][0]["url"]
        recipe = self.mcp_tools.fetch_recipe_from_url(recipe_url)

        if not recipe.get("success"):
            return f"I found a recipe but couldn't fetch details."

        model = genai.GenerativeModel(
            model_name=self.generation_model,
            system_instruction=(
                "Only summarize the given recipe. "
                "Do not invent ingredients or steps."
            ),
        )

        prompt = f"""
            Title: {recipe.get('title')}
            Ingredients: {recipe.get('ingredients')}
            Instructions: {recipe.get('instructions')}
            Source: {recipe.get('url')}
            """

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 200},
        )

        return response.text

    # -------------------- RAG Entry --------------------

    def answer_question(
        self,
        question: str,
        top_k: int = 3,
        filters: Optional[Dict] = None,
        similarity_threshold: float = 0.35,  # Lowered from 0.5
        use_mcp_orchestrator: bool = True,
    ) -> Dict:

        if use_mcp_orchestrator:
            self.setup_mcp_orchestrator()
            result = self.mcp_orchestrator.process_query(
                query=question,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            return {
                "question": question,
                "response": result["message"],
                "sources": result.get("recipes", []),
                "generated": not result["has_database_results"],
            }

        results = self.search_chroma(
            question,
            top_k=top_k,
            filters=filters,
            min_score=similarity_threshold,
        )

        if not results:
            return {
                "question": question,
                "response": self.generate_recipe_suggestion(question),
                "sources": [],
                "generated": True,
            }

        return {
            "question": question,
            "response": None,
            "sources": results,
            "generated": False,
        }

    # -------------------- Stats --------------------

    def get_statistics(self) -> Dict:
        try:
            metadatas = self.collection.get(include=["metadatas"])["metadatas"]
            
            # Handle empty collection
            if not metadatas or not metadatas[0]:
                return {
                    "total_recipes": 0,
                    "categories": {},
                    "cuisines": {},
                    "average_rating": 0.0,
                }

            categories, cuisines, ratings = {}, {}, []

            for meta in metadatas[0]:
                categories[meta.get("category", "Unknown")] = (
                    categories.get(meta.get("category", "Unknown"), 0) + 1
                )

                if meta.get("cuisine"):
                    cuisines[meta["cuisine"]] = cuisines.get(meta["cuisine"], 0) + 1

                if meta.get("rating"):
                    try:
                        ratings.append(float(meta["rating"]))
                    except:
                        pass

            return {
                "total_recipes": len(metadatas[0]),
                "categories": categories,
                "cuisines": cuisines,
                "average_rating": float(np.mean(ratings)) if ratings else 0.0,
            }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {
                "total_recipes": 0,
                "categories": {},
                "cuisines": {},
                "average_rating": 0.0,
            }