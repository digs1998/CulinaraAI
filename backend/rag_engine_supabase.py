"""
Supabase-based RAG Engine for Recipe Search
Uses PostgreSQL with pgvector extension for semantic search.

This replaces ChromaDB with Supabase for:
- Persistent storage across deployments
- No re-ingestion on Railway deploys
- Better scalability
"""
import os
import json
from typing import List, Dict, Optional
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class SupabaseRAGEngine:
    """
    Recipe RAG Engine using Supabase PostgreSQL + pgvector
    """

    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model = "models/text-embedding-004"
        self.generation_model = "gemini-2.0-flash-exp"

        # Initialize Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase RAG Engine initialized")

    # -------------------- Embeddings --------------------

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        result = genai.embed_content(
            model=self.embedding_model,
            content=query,
            task_type="retrieval_query",
        )
        return result["embedding"]

    # -------------------- Search --------------------

    def search_recipes(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        min_score: float = 0.35
    ) -> List[Dict]:
        """
        Search recipes using semantic similarity in Supabase pgvector.

        Args:
            query: Search query (e.g., "healthy pasta recipes")
            top_k: Number of results to return
            filters: Optional filters (e.g., {"cuisine": "Italian"})
            min_score: Minimum similarity score (0-1)

        Returns:
            List of recipe results with metadata and similarity scores
        """
        print(f"🔍 Searching Supabase for: '{query}'")

        # Generate query embedding
        query_embedding = self.embed_query(query)

        # Convert to pgvector format
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Call Supabase RPC function for vector search
        try:
            result = self.supabase.rpc(
                'search_recipes',
                {
                    'query_embedding': embedding_str,
                    'match_threshold': min_score,
                    'match_count': top_k
                }
            ).execute()

            if not result.data:
                print("⚠️ No results from Supabase")
                return []

            # Format results
            formatted_results = []
            for row in result.data:
                formatted_results.append({
                    "id": row['id'],
                    "score": row['similarity'],  # Already 0-1 from Supabase
                    "metadata": {
                        "title": row['title'],
                        "ingredients": row['ingredients'] if isinstance(row['ingredients'], list) else json.loads(row['ingredients']),
                        "instructions": row['instructions'] if isinstance(row['instructions'], list) else json.loads(row['instructions']),
                        "url": row.get('source_url'),
                        "source": row.get('source_name'),
                        "image_url": row.get('image_url'),
                        "cuisine": row.get('cuisine'),
                        "diet_tags": row.get('diet_tags', []),
                        "facts": row.get('facts', {}),
                        "prep_time": row.get('prep_time'),
                        "cook_time": row.get('cook_time'),
                        "servings": row.get('servings')
                    }
                })

            print(f"✅ Found {len(formatted_results)} results from Supabase")
            return formatted_results

        except Exception as e:
            print(f"❌ Supabase search error: {e}")
            return []

    def search_chroma(self, query: str, top_k: int = 5, filters: Optional[Dict] = None, min_score: float = 0.35):
        """
        Compatibility wrapper for existing code that calls search_chroma.
        Redirects to search_recipes (Supabase).
        """
        return self.search_recipes(query, top_k, filters, min_score)

    # -------------------- Recipe Details --------------------

    def get_recipe_details(self, recipe_id: str) -> Optional[Dict]:
        """Get full details for a specific recipe"""
        try:
            result = self.supabase.table('recipes').select('*').eq('id', recipe_id).execute()

            if not result.data:
                return None

            row = result.data[0]
            return {
                "id": row['id'],
                "title": row['title'],
                "ingredients": row['ingredients'] if isinstance(row['ingredients'], list) else json.loads(row['ingredients']),
                "instructions": row['instructions'] if isinstance(row['instructions'], list) else json.loads(row['instructions']),
                "url": row.get('source_url'),
                "source": row.get('source_name'),
                "image_url": row.get('image_url'),
                "cuisine": row.get('cuisine'),
                "diet_tags": row.get('diet_tags', []),
                "facts": row.get('facts', {}),
                "prep_time": row.get('prep_time'),
                "cook_time": row.get('cook_time'),
                "servings": row.get('servings')
            }

        except Exception as e:
            print(f"❌ Error fetching recipe {recipe_id}: {e}")
            return None

    # -------------------- Statistics --------------------

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            result = self.supabase.rpc('get_database_stats').execute()

            if result.data:
                stats = result.data[0]
                return {
                    "total_recipes": stats['total_recipes'],
                    "total_embeddings": stats['total_embeddings'],
                    "recipes_pending_embedding": stats['recipes_pending_embedding'],
                    "unique_sources": stats['unique_sources'],
                    "unique_cuisines": stats['unique_cuisines']
                }
            else:
                return {
                    "total_recipes": 0,
                    "total_embeddings": 0,
                    "recipes_pending_embedding": 0,
                    "unique_sources": 0,
                    "unique_cuisines": 0
                }

        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {
                "total_recipes": 0,
                "total_embeddings": 0,
                "recipes_pending_embedding": 0,
                "unique_sources": 0,
                "unique_cuisines": 0
            }

    # -------------------- Recipe Context (for LLM) --------------------

    def get_recipe_context(self, recipe_ids: List[str], detailed: bool = True) -> str:
        """
        Get formatted recipe context for LLM summarization
        """
        context = ""

        for recipe_id in recipe_ids:
            recipe = self.get_recipe_details(recipe_id)

            if not recipe:
                continue

            context += f"\n{'='*50}\n"
            context += f"Recipe: {recipe.get('title', 'Unknown')}\n"

            if detailed:
                # Ingredients
                ingredients = recipe.get('ingredients', [])
                if ingredients:
                    context += "\nIngredients:\n"
                    for ing in ingredients[:15]:
                        context += f"- {ing}\n"

                # Instructions
                instructions = recipe.get('instructions', [])
                if instructions:
                    context += "\nInstructions:\n"
                    for i, step in enumerate(instructions[:10], 1):
                        context += f"{i}. {step}\n"

                # Facts
                if recipe.get('prep_time') or recipe.get('cook_time'):
                    context += "\nDetails:\n"
                    if recipe.get('prep_time'):
                        context += f"- Prep Time: {recipe['prep_time']} min\n"
                    if recipe.get('cook_time'):
                        context += f"- Cook Time: {recipe['cook_time']} min\n"
                    if recipe.get('servings'):
                        context += f"- Servings: {recipe['servings']}\n"

            if recipe.get('url'):
                context += f"\nSource: {recipe['url']}\n"

        return context

    # -------------------- Compatibility Methods --------------------

    def answer_question(
        self,
        question: str,
        top_k: int = 3,
        filters: Optional[Dict] = None,
        similarity_threshold: float = 0.35,
        use_mcp_orchestrator: bool = True,
    ) -> Dict:
        """
        Compatibility method for existing code.
        """
        results = self.search_recipes(
            question,
            top_k=top_k,
            filters=filters,
            min_score=similarity_threshold
        )

        return {
            "question": question,
            "response": None,
            "sources": results,
            "generated": len(results) == 0,
        }


# Factory function to create the right engine based on environment
def create_rag_engine():
    """
    Create RAG engine based on environment variables.

    If SUPABASE_URL is set, use Supabase.
    Otherwise, fall back to ChromaDB.
    """
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        print("🔄 Using Supabase RAG Engine")
        return SupabaseRAGEngine()
    else:
        print("⚠️ SUPABASE_URL not set, falling back to ChromaDB")
        # Import and return original ChromaDB engine
        from rag_engine import RecipeRAGEngine
        from chromadb import PersistentClient
        from pathlib import Path

        chroma_dir = Path(__file__).parent / "chroma_db"
        if not chroma_dir.exists():
            raise ValueError("ChromaDB not found and Supabase not configured!")

        chroma_client = PersistentClient(path=str(chroma_dir))
        collection = chroma_client.get_or_create_collection("recipes")
        return RecipeRAGEngine(chroma_collection=collection)
