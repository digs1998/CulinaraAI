import os
import json
import html
import numpy as np
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from services.mcp_orchestrator import MCPOrchestrator

# MCP tools
from services.mcp_tools import get_mcp_tools

load_dotenv()

class RecipeRAGEngine:
    """
    Policy-driven Recipe RAG + Web Fallback Engine
    """

    def __init__(
        self,
        embeddings_path: str = "/Users/Lenovo/Desktop/Education/feastron/backend/data/recipe_embeddings.npz"
    ):
        load_dotenv()

        # ---- Load embeddings
        data = np.load(embeddings_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.ids = data["ids"]
        self.metadata = json.loads(data["metadata"].item())
        self._clean_metadata()

        # ---- Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model = "models/text-embedding-004"
        self.generation_model = "gemini-2.0-flash-exp"

        # ---- MCP tools
        self.mcp_tools = get_mcp_tools()
        self.mcp_orchestrator = None

    def setup_mcp_orchestrator(self):
        if self.mcp_orchestrator is None:
            self.mcp_orchestrator = MCPOrchestrator(self, self.mcp_tools)

    def _clean_metadata(self):
        for meta in self.metadata:
            for key in ["title", "category", "cuisine"]:
                if meta.get(key):
                    meta[key] = html.unescape(meta[key])
                    
    def embed_query(self, query: str) -> np.ndarray:
        result = genai.embed_content(
            model=self.embedding_model,
            content=query,
            task_type="retrieval_query"
        )
        return np.array(result["embedding"])

    def generate_recipe_suggestion(self, query: str) -> str:
        all_terms, ingredient_terms = self._extract_key_terms(query)

        # Constrained query
        if ingredient_terms:
            web_query = f"{query} recipe with {' '.join(ingredient_terms)}"
        else:
            web_query = f"{query} recipe"

        search = self.mcp_tools.search_recipe_web(
            query=web_query,
            max_results=5
        )

        if not search.get("success"):
            return self._fallback_suggestion_only(query, ingredient_terms)

        valid_results = self._filter_web_results(
            search["results"],
            all_terms,
            ingredient_terms
        )

        if not valid_results:
            return self._fallback_suggestion_only(query, ingredient_terms)

        # Fetch recipe
        url = valid_results[0]["url"]
        recipe = self.mcp_tools.fetch_recipe_from_url(url)

        if not recipe.get("success"):
            return self._fallback_suggestion_only(query, ingredient_terms)

        # Safe summarization
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

    
    # def generate_recipe_suggestion(self, query: str, context: Optional[str] = None) -> str:
    #     """
    #     Generate a recipe suggestion using Gemini when no recipes found in database
    #     Uses grounding and safety features to minimize hallucination
        
    #     Args:
    #         query: User's recipe request
    #         context: Optional context from similar recipes
        
    #     Returns:
    #         Generated recipe suggestion with safety measures
    #     """
        
    #     # Create a safe prompt that encourages factual, helpful responses with internet access
    #     system_prompt = """You are Feastron, an AI culinary coach with attitude but also accuracy. 
    #     When a recipe is not in the database, you have access to internet search tools.
        
    #     Your workflow:
    #     1. First, acknowledge you don't have the recipe in your local database
    #     2. Use the search_recipe_web tool to find recipes from reliable cooking websites
    #     3. If you find a good recipe URL, use fetch_recipe_from_url to get detailed recipe information
    #     4. Provide the user with the recipe details from the internet source
    #     5. Always cite the source URL and encourage users to verify details
        
    #     Rules:
    #     - Only use tools when you genuinely don't have the recipe locally
    #     - Be honest about sources - always cite where you found the recipe
    #     - Never make up recipes - if tools fail, say so honestly
    #     - Provide accurate information from the fetched recipes
    #     - Keep responses conversational, helpful, and safe"""

    #     user_prompt = f"""A user is asking: "{query}"

    #     I don't have this specific recipe in my local database. 
        
    #     {f"Context from similar recipes I do have: {context}" if context else ""}

    #     Please use the available internet search tools to find this recipe online and provide the user with helpful recipe information from reliable sources."""

    #     try:
    #         # First, try to search for the recipe on the web using MCP tools
    #         print(f"🌐 Searching internet for recipe: {query}")
    #         search_result = self.mcp_tools.search_recipe_web(query=query, max_results=3)
            
    #         web_recipes_context = ""
    #         if search_result.get("success") and search_result.get("results"):
    #             web_recipes_context = "\n\nI found these recipe sources online:\n"
    #             for i, result in enumerate(search_result["results"][:3], 1):
    #                 web_recipes_context += f"{i}. {result.get('title', 'Recipe')} - {result.get('url', '')}\n"
    #                 if result.get('snippet'):
    #                     web_recipes_context += f"   {result['snippet'][:150]}...\n"
                
    #             # Try to fetch detailed recipe from first result
    #             if search_result["results"]:
    #                 first_url = search_result["results"][0].get("url")
    #                 if first_url:
    #                     print(f"📄 Fetching recipe details from: {first_url}")
    #                     recipe_details = self.mcp_tools.fetch_recipe_from_url(first_url)
    #                     if recipe_details.get("success"):
    #                         recipe_info = f"\n\nDetailed Recipe Information:\n"
    #                         if recipe_details.get("title"):
    #                             recipe_info += f"Title: {recipe_details['title']}\n"
    #                         if recipe_details.get("ingredients"):
    #                             recipe_info += f"\nIngredients:\n"
    #                             for ing in recipe_details['ingredients'][:10]:  # Limit to first 10
    #                                 recipe_info += f"- {ing}\n"
    #                         if recipe_details.get("instructions"):
    #                             recipe_info += f"\nInstructions:\n"
    #                             for i, step in enumerate(recipe_details['instructions'][:5], 1):  # Limit to first 5
    #                                 recipe_info += f"{i}. {step}\n"
    #                         if recipe_details.get("url"):
    #                             recipe_info += f"\nSource: {recipe_details['url']}\n"
    #                         web_recipes_context += recipe_info
            
    #         # Update user prompt with web search results
    #         enhanced_user_prompt = f"""A user is asking: "{query}"

    #                 I don't have this specific recipe in my local database. {web_recipes_context}

    #                 {f"Context from similar recipes I do have in the database: {context}" if context else ""}

    #                 Please provide the user with the recipe information I found online, or helpful guidance if the web search didn't find good results. Always cite sources when providing recipe information from the web."""
            
    #         # Use the stable google.generativeai API
    #         model = genai.GenerativeModel(
    #             model_name=self.generation_model,
    #             system_instruction=system_prompt
    #         )
            
    #         response = model.generate_content(
    #             enhanced_user_prompt,
    #             generation_config={
    #                 "temperature": 0.4,
    #                 "top_p": 0.8,
    #                 "top_k": 40,
    #                 "max_output_tokens": 1000,  # Increased for longer responses with recipe details
    #             }
    #         )
            
    #         return response.text
            
    #     except Exception as e:
    #         import traceback
    #         print(f"Error generating recipe suggestion with MCP: {e}")
    #         print(traceback.format_exc())
    #         return "I don't have that specific recipe in my database right now. Try searching for something similar, or check out food.com for verified recipes!"
    
    def _extract_key_terms(self, query: str) -> tuple[List[str], List[str]]:
        """
        Extract key ingredient/dish terms from query
        Returns: (all_terms, ingredient_terms)
        """
        # Common ingredient/protein keywords - these are critical
        common_ingredients = {
            'chicken', 'beef', 'pork', 'lamb', 'fish', 'salmon', 'tuna', 'shrimp', 'prawn',
            'paneer', 'tofu', 'tempeh', 'seitan',
            'cheese', 'mozzarella', 'cheddar', 'feta', 'ricotta',
            'mushroom', 'eggplant', 'zucchini', 'tomato', 'potato', 'onion', 'garlic',
            'rice', 'pasta', 'noodle', 'bread'
        }
        
        query_lower = query.lower()
        # Split and filter out common stop words
        stop_words = {'how', 'to', 'make', 'recipe', 'for', 'a', 'an', 'the', 'with', 'and', 'or', 'of', 'in'}
        all_terms = [word.rstrip('?') for word in query_lower.split() if word.rstrip('?') not in stop_words and len(word.rstrip('?')) > 2]
        
        # Separate ingredient terms from other descriptive terms
        ingredient_terms = [term for term in all_terms if term in common_ingredients]
        print(f"---- 🔍 All terms: {all_terms} | Ingredient terms: {ingredient_terms} -----")
        
        return all_terms, ingredient_terms
    
    # def _check_keyword_match(self, all_query_terms: List[str], ingredient_terms: List[str], recipe_text: str) -> tuple[float, bool]:
    #     """
    #     Check if recipe contains key terms from query
    #     Returns: (boost_score, has_all_critical_ingredients)
        
    #     - Boost for matching terms
    #     - Penalty for missing critical ingredient terms
    #     - Special penalty for conflicting ingredients (e.g., paneer vs chicken)
    #     """
    #     recipe_lower = recipe_text.lower()
        
    #     # Check for ingredient conflicts (e.g., query has paneer but recipe has chicken)
    #     ingredient_conflicts = {
    #         'paneer': ['chicken', 'beef', 'pork', 'lamb', 'meat'],
    #         'chicken': ['paneer', 'tofu', 'vegan', 'vegetarian'],
    #         'beef': ['chicken', 'paneer', 'tofu', 'vegetarian', 'vegan'],
    #         'pork': ['chicken', 'paneer', 'tofu', 'vegetarian', 'vegan'],
    #         'fish': ['chicken', 'paneer', 'vegetarian', 'vegan'],
    #     }
        
    #     # Check for conflicts
    #     has_conflict = False
    #     for ingredient in ingredient_terms:
    #         if ingredient in ingredient_conflicts:
    #             conflicting_terms = ingredient_conflicts[ingredient]
    #             if any(conflict in recipe_lower for conflict in conflicting_terms):
    #                 has_conflict = True
    #                 print(f"    ⚠️ Conflict detected: query has '{ingredient}' but recipe has conflicting ingredient")
    #                 break
        
    #     # Count matches for all terms (for boost)
    #     matches = sum(1 for term in all_query_terms if term in recipe_lower)
        
    #     # Check if all critical ingredient terms are present
    #     has_all_ingredients = True
    #     missing_ingredients = []
    #     for ingredient in ingredient_terms:
    #         if ingredient not in recipe_lower:
    #             has_all_ingredients = False
    #             missing_ingredients.append(ingredient)
        
    #     # if missing_ingredients:
    #     #     print(f"    ⚠️ Missing critical ingredients: {missing_ingredients}")
        
    #     # Calculate boost/penalty
    #     if has_conflict:
    #         # Heavy penalty for conflicts (-0.3)
    #         boost = -0.3
    #     elif not has_all_ingredients and ingredient_terms:
    #         # Penalty for missing critical ingredients (-0.2)
    #         boost = -0.2
    #     elif matches > 0:
    #         # Boost for matching terms
    #         boost = min(0.15, matches * 0.03)
    #     else:
    #         boost = 0.0
        
    #     return boost, has_all_ingredients and not has_conflict
    
    def _filter_web_results(
        self,
        results: List[Dict],
        all_terms: List[str],
        ingredient_terms: List[str]
    ):
        valid = []
        for r in results:
            blob = f"{r.get('title','')} {r.get('snippet','')}"
            _, ok = self._check_keyword_match(all_terms, ingredient_terms, blob)
            if ok:
                valid.append(r)
        return valid
    
    def _fallback_suggestion_only(self, query, ingredient_terms):
        protein = ", ".join(ingredient_terms) if ingredient_terms else "your preference"
        return f"""
                I couldn’t find a reliable online recipe that strictly matches **{query}** using **{protein}**.

                Here are a few **safe quick ideas** instead:
                • Garlic butter chicken skillet (20 min)
                • Lemon chicken with veggies
                • One-pan chicken pasta
                • Chicken stir-fry with soy & ginger

                Want me to:
                ✓ Relax ingredient constraints
                ✓ Generate a custom recipe
                ✓ Search by cuisine or calories
            """

    
    def _check_keyword_match(self, all_terms, ingredient_terms, text):
        text = text.lower()

        ingredient_conflicts = {
            "chicken": ["tofu", "paneer", "vegetarian", "vegan"],
            "paneer": ["chicken", "beef", "pork"],
            "tofu": ["chicken", "beef", "pork"]
        }

        # Conflict detection
        for ing in ingredient_terms:
            conflicts = ingredient_conflicts.get(ing, [])
            if any(c in text for c in conflicts):
                return -0.3, False

        # Missing critical ingredient
        for ing in ingredient_terms:
            if ing not in text:
                return -0.2, False

        matches = sum(1 for t in all_terms if t in text)
        boost = min(0.15, matches * 0.03)

        return boost, True

    
    def search_recipes(self, query: str, top_k: int = 5, 
                      filters: Optional[Dict] = None,
                      min_score: float = 0.0) -> List[Dict]:
        """
        Search for recipes using semantic similarity with keyword validation
        
        Args:
            query: Search query (e.g., "quick chicken dinner")
            top_k: Number of results to return
            filters: Optional filters like {"category": "Dessert"}
            min_score: Minimum similarity score (0-1)
        
        Returns:
            List of matching recipes with scores
        """
        
        # Extract key terms from query for keyword matching
        all_query_terms, ingredient_terms = self._extract_key_terms(query)
        print(f"🔍 Search query: '{query}'")
        
        # Generate query embedding
        query_embedding = self.embed_query(query)
        
        # Calculate cosine similarity
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        similarities = np.dot(embeddings_norm, query_norm)
        
        # Apply keyword boost/penalty and validation
        boosted_similarities = similarities.copy()
        keyword_match_flags = {}
        
        for i, meta in enumerate(self.metadata):
            # Combine title, category, cuisine, and ingredients for keyword matching
            recipe_text = f"{meta.get('title', '')} {meta.get('category', '')} {meta.get('cuisine', '')}"
            # Add ingredients if available
            if 'ingredients' in meta:
                if isinstance(meta['ingredients'], list):
                    recipe_text += ' ' + ' '.join(meta['ingredients'])
                else:
                    recipe_text += ' ' + str(meta['ingredients'])
            
            # Apply keyword boost/penalty and check for critical ingredient matches
            keyword_boost, has_valid_match = self._check_keyword_match(all_query_terms, ingredient_terms, recipe_text)
            boosted_similarities[i] = max(0.0, min(1.0, similarities[i] + keyword_boost))
            keyword_match_flags[i] = has_valid_match
        
        # Apply filters if provided
        valid_indices = np.arange(len(boosted_similarities))
        if filters:
            valid_mask = np.ones(len(boosted_similarities), dtype=bool)
            for key, value in filters.items():
                for i, meta in enumerate(self.metadata):
                    filter_value = meta.get(key, '').lower() if meta.get(key) else ''
                    if isinstance(value, str):
                        if filter_value != value.lower():
                            valid_mask[i] = False
                    elif isinstance(value, list):
                        # Support multiple values (OR condition)
                        if filter_value not in [v.lower() for v in value]:
                            valid_mask[i] = False
            valid_indices = np.where(valid_mask)[0]
        
        # Apply minimum score threshold
        valid_similarities = boosted_similarities[valid_indices]
        score_mask = valid_similarities >= min_score
        valid_indices = valid_indices[score_mask]
        valid_similarities = valid_similarities[score_mask]
        
        # Get top k from valid indices
        if len(valid_similarities) == 0:
            print(f"⚠️ No results above threshold {min_score}")
            return []
        
        top_valid_indices = np.argsort(valid_similarities)[-top_k:][::-1]
        top_indices = valid_indices[top_valid_indices]
        
        # Format results with keyword validation
        results = []
        for idx in top_indices:
            meta = self.metadata[idx]
            final_score = float(boosted_similarities[idx])
            has_valid_match = keyword_match_flags.get(idx, False)
            
            # Log for debugging
            match_status = "✓" if has_valid_match else "✗"
            print(f"  📋 {meta.get('title', 'N/A')[:50]} | Score: {final_score:.3f} | Valid: {match_status}")
            
            results.append({
                "id": str(self.ids[idx]),
                "score": final_score,
                "metadata": meta,
                "keyword_match": has_valid_match
            })
        
        return results
    
    def get_recipe_details(self, recipe_id: str) -> Optional[Dict]:
        """Get full details for a specific recipe"""
        # Find recipe in metadata
        idx = np.where(self.ids == recipe_id)[0]
        if len(idx) == 0:
            return None
        
        return self.metadata[idx[0]]
    
    def get_recipe_context(self, recipe_ids: List[str], detailed: bool = True) -> str:
        """
        Get formatted context for LLM from recipe IDs
        
        Args:
            recipe_ids: List of recipe IDs
            detailed: If True, include all details; if False, brief summary
        
        Returns:
            Formatted text context for LLM
        """
        context_parts = []
        
        for recipe_id in recipe_ids:
            # Find recipe metadata
            idx = np.where(self.ids == recipe_id)[0]
            if len(idx) == 0:
                continue
            
            meta = self.metadata[idx[0]]
            
            if detailed:
                # Format detailed recipe information
                context = f"""
                        Recipe: {meta['title']}
                        Category: {meta.get('category', 'N/A')}
                        Cuisine: {meta.get('cuisine', 'N/A')}
                        Preparation Time: {meta.get('prep_time', 'N/A')}
                        Cooking Time: {meta.get('cook_time', 'N/A')}
                        Total Time: {meta.get('total_time', 'N/A')}
                        Servings: {meta.get('servings', 'N/A')}
                        Calories: {meta.get('calories', 'N/A')}
                        Rating: {meta.get('rating', 'N/A')}/5 ({meta.get('review_count', 0)} reviews)
                        Ingredients: {meta.get('ingredient_count', 'N/A')} items
                        Instructions: {meta.get('step_count', 'N/A')} steps
                        URL: {meta.get('url', 'N/A')}
                        """
            else:
                # Brief summary
                context = f"""
{meta['title']} - {meta.get('category', 'N/A')} ({meta.get('total_time', 'N/A')})
Rating: {meta.get('rating', 'N/A')}/5 | URL: {meta.get('url', 'N/A')}
"""
            
            context_parts.append(context.strip())
        
        return "\n\n---\n\n".join(context_parts)
    
    def setup_mcp_orchestrator(self):
        """Setup MCP orchestrator for coordinated RAG + Web search"""
        if self.mcp_orchestrator is None:
            from services.mcp_orchestrator import MCPOrchestrator
            self.mcp_orchestrator = MCPOrchestrator(self, self.mcp_tools)
    
    def answer_question(self, question: str, top_k: int = 3,
                       filters: Optional[Dict] = None,
                       similarity_threshold: float = 0.5,
                       use_mcp_orchestrator: bool = True) -> Dict:
        """
        Answer a question using RAG with fallback to LLM generation
        Optionally uses MCP orchestrator for coordinated RAG + Web search
        
        Args:
            question: User's question
            top_k: Number of recipes to retrieve
            filters: Optional filters
            similarity_threshold: Minimum similarity score to consider recipes relevant
            use_mcp_orchestrator: If True, use MCP orchestrator for coordinated search
        
        Returns:
            Dict with answer context, sources, metadata, and generation flag
        """
        
        # Use MCP orchestrator if enabled
        if use_mcp_orchestrator:
            self.setup_mcp_orchestrator()
            orchestrator_result = self.mcp_orchestrator.process_query(
                query=question,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Convert orchestrator result to expected format
            return {
                "question": question,
                "response": orchestrator_result["message"],
                "context": None,
                "sources": orchestrator_result.get("recipes", []),
                "top_recipe": orchestrator_result["recipes"][0] if orchestrator_result["recipes"] else None,
                "generated": not orchestrator_result["has_database_results"],
                "message": None,
                "mcp_result": orchestrator_result  # Include full orchestrator result
            }
        
        # Original RAG-only flow (fallback)
        # Extract ingredient terms to check if query has specific ingredients
        _, ingredient_terms = self._extract_key_terms(question)
        
        # Search for relevant recipes
        results = self.search_recipes(question, top_k=top_k, filters=filters)
        
        # Check if we have relevant results
        # Also check for keyword matches to avoid obvious mismatches (e.g., paneer query returning chicken)
        has_relevant_results = False
        if results and len(results) > 0:
            top_result = results[0]
            score_ok = top_result['score'] >= similarity_threshold
            # Require valid keyword match (all critical ingredients present, no conflicts)
            keyword_match = top_result.get('keyword_match', False)
            
            # Require both score AND valid keyword match for results with ingredient terms
            # This prevents "paneer" queries from returning "chicken" recipes
            if ingredient_terms and len(ingredient_terms) > 0:
                # For queries with specific ingredients, we MUST have a valid keyword match
                has_relevant_results = score_ok and keyword_match
                if not keyword_match:
                    print(f"⚠️ Top result missing critical ingredients or has conflicts (query: {ingredient_terms})")
            else:
                # For general queries without specific ingredients, just check score
                has_relevant_results = score_ok
            
            if not has_relevant_results:
                print(f"⚠️ Top result score {top_result['score']:.3f} below threshold {similarity_threshold} or invalid match")
        
        if not has_relevant_results:
            # No relevant recipes found - use LLM to generate helpful response
            print(f"⚠️ No relevant recipes found (threshold: {similarity_threshold})")
            
            # Get some context from less relevant matches if available
            context = None
            if results:
                context_recipes = [r['metadata']['title'] for r in results[:2]]
                context = f"Similar recipes in database: {', '.join(context_recipes)}"
            
            generated_response = self.generate_recipe_suggestion(question, context)
            
            return {
                "question": question,
                "response": generated_response,
                "context": None,
                "sources": results[:3] if results else [],  # Still show less relevant matches
                "top_recipe": None,
                "generated": True,  # Flag that this was LLM-generated
                "message": "⚠️ This response was generated since no exact matches were found in the database."
            }
        
        # We have relevant results - use RAG approach
        recipe_ids = [r['id'] for r in results]
        context = self.get_recipe_context(recipe_ids, detailed=True)
        
        return {
            "question": question,
            "response": None,  # Frontend will format the recipes
            "context": context,
            "sources": results,
            "top_recipe": results[0] if results else None,
            "generated": False,  # This is from database
            "message": None
        }
    
    def get_similar_recipes(self, recipe_id: str, top_k: int = 5) -> List[Dict]:
        """
        Find recipes similar to a given recipe
        
        Args:
            recipe_id: Recipe ID to find similar recipes for
            top_k: Number of similar recipes to return
        
        Returns:
            List of similar recipes
        """
        # Find recipe embedding
        idx = np.where(self.ids == recipe_id)[0]
        if len(idx) == 0:
            return []
        
        recipe_embedding = self.embeddings[idx[0]]
        
        # Calculate similarities
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        recipe_norm = recipe_embedding / np.linalg.norm(recipe_embedding)
        similarities = np.dot(embeddings_norm, recipe_norm)
        
        # Get top k (excluding the recipe itself)
        top_indices = np.argsort(similarities)[-(top_k+1):-1][::-1]
        
        # Format results
        results = []
        for idx in top_indices:
            if self.ids[idx] == recipe_id:
                continue
            results.append({
                "id": str(self.ids[idx]),
                "score": float(similarities[idx]),
                "metadata": self.metadata[idx]
            })
        
        return results[:top_k]
    
    def get_statistics(self) -> Dict:
        """Get statistics about the recipe database"""
        categories = {}
        cuisines = {}
        ratings = []
        
        for meta in self.metadata:
            # Count categories
            cat = meta.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count cuisines
            cui = meta.get('cuisine')
            if cui:
                cuisines[cui] = cuisines.get(cui, 0) + 1
            
            # Collect ratings
            rating = meta.get('rating')
            if rating:
                ratings.append(float(rating))
        
        return {
            "total_recipes": len(self.metadata),
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