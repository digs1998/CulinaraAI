"""
MCP Orchestrator - Coordinates RAG DB and Web Search pipelines
Following the architecture:
User Query → MCP Orchestrator → [RAG DB → Gemini LLM] + [Web Search → Gemini LLM] → Combined Output
"""

from typing import Dict, List, Optional, Tuple
import google.generativeai as genai


class MCPOrchestrator:
    """Orchestrates RAG DB and Web Search pipelines with Gemini LLM summarization"""
    
    def __init__(self, rag_engine, mcp_tools):
        """
        Initialize MCP Orchestrator
        
        Args:
            rag_engine: RecipeRAGEngine instance for database search
            mcp_tools: MCPRecipeTools instance for web search
        """
        self.rag_engine = rag_engine
        self.mcp_tools = mcp_tools
        self.llm_model = None
        
        # Initialize Gemini model for summarization
        import os
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            # Configure if not already configured
            try:
                genai.configure(api_key=api_key)
            except:
                pass  # Already configured
            
            self.llm_model = genai.GenerativeModel(
                model_name=self.rag_engine.generation_model
            )
    
    def process_query(self, query: str, top_k: int = 3, 
                     similarity_threshold: float = 0.65) -> Dict:
        """
        Process user query through MCP orchestrator
        
        Pipeline:
        1. Query → MCP Orchestrator
        2. First try RAG DB search → Gemini LLM (summarize + facts)
        3. If no results found, then Web Search → Gemini LLM (summarize + facts)
        4. Return results (from DB if found, otherwise from web)
        
        Args:
            query: User query
            top_k: Number of results to retrieve from RAG DB
            similarity_threshold: Minimum similarity for RAG DB results
            
        Returns:
            Response from RAG DB (if found) or Web Search (as fallback)
        """
        print(f"\n{'='*60}")
        print(f"🎯 MCP Orchestrator Processing: '{query}'")
        print(f"{'='*60}\n")
        
        # Step 1: Try RAG DB first
        rag_result = self._process_rag_pipeline(query, top_k, similarity_threshold)
        
        # Step 2: Only do web search if RAG DB didn't find results
        web_result = None
        if not rag_result["has_results"]:
            print("\n⚠️ No results in database, falling back to web search...\n")
            web_result = self._process_web_pipeline(query)
        else:
            print("\n✓ Found results in database, skipping web search")
            web_result = {
                "has_results": False,
                "search_result": None,
                "summary": None,
                "source": "Internet"
            }
        
        # Step 3: Combine results (will prioritize RAG DB if found)
        combined_response = self._combine_results(query, rag_result, web_result)
        
        return combined_response
    
    def _process_rag_pipeline(self, query: str, top_k: int, 
                             similarity_threshold: float) -> Dict:
        """
        Process query through RAG DB → Gemini LLM pipeline
        
        Args:
            query: User query
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            Dict with RAG results and LLM-summarized response
        """
        print("📚 RAG DB Pipeline:")
        print("  → Searching local database...")
        
        # Search RAG database
        rag_results = self.rag_engine.search_recipes(query, top_k=top_k)
        
        rag_summary = None
        rag_has_results = False
        
        if rag_results and len(rag_results) > 0:
            # Check if results meet threshold
            top_result = rag_results[0]
            if top_result['score'] >= similarity_threshold and top_result.get('keyword_match', False):
                rag_has_results = True
                print(f"  ✓ Found {len(rag_results)} relevant recipes (top score: {top_result['score']:.3f})")
                
                # Get recipe context
                recipe_ids = [r['id'] for r in rag_results]
                recipe_context = self.rag_engine.get_recipe_context(recipe_ids, detailed=True)
                
                # Summarize with Gemini LLM
                print("  → Summarizing with Gemini LLM...")
                rag_summary = self._summarize_with_llm(
                    context=recipe_context,
                    query=query,
                    source="local database"
                )
                print("  ✓ RAG DB summary complete")
            else:
                print(f"  ⚠️ Results below threshold (score: {top_result['score']:.3f})")
        else:
            print("  ⚠️ No results found in local database")
        
        return {
            "has_results": rag_has_results,
            "results": rag_results if rag_has_results else [],
            "summary": rag_summary,
            "source": "RAG Database"
        }
    
    def _process_web_pipeline(self, query: str) -> Dict:
        """
        Process query through Web Search → Gemini LLM pipeline
        
        Args:
            query: User query
            
        Returns:
            Dict with web search results and LLM-summarized response
        """
        print("\n🌐 Web Search Pipeline:")
        print("  → Searching internet...")
        
        # Search web
        web_search_result = self.mcp_tools.search_recipe_web(query=query, max_results=3)
        
        web_summary = None
        web_has_results = False
        
        if web_search_result.get("success") and web_search_result.get("results"):
            web_has_results = True
            results = web_search_result["results"]
            print(f"  ✓ Found {len(results)} recipe sources online")
            
            # Fetch detailed recipe from first result
            recipe_details = None
            if results:
                first_url = results[0].get("url")
                if first_url:
                    print(f"  → Fetching recipe details from: {first_url[:50]}...")
                    recipe_details = self.mcp_tools.fetch_recipe_from_url(first_url)
            
            # Prepare context for LLM
            web_context = self._format_web_context(results, recipe_details)
            
            # Summarize with Gemini LLM
            print("  → Summarizing with Gemini LLM...")
            web_summary = self._summarize_with_llm(
                context=web_context,
                query=query,
                source="internet"
            )
            print("  ✓ Web search summary complete")
        else:
            print("  ⚠️ No results found on internet")
        
        return {
            "has_results": web_has_results,
            "search_result": web_search_result,
            "summary": web_summary,
            "source": "Internet"
        }
    
    def _format_web_context(self, search_results: List[Dict], 
                           recipe_details: Optional[Dict]) -> str:
        """Format web search results into context for LLM"""
        context = "Recipe Sources Found Online:\n\n"
        
        for i, result in enumerate(search_results[:3], 1):
            context += f"{i}. {result.get('title', 'Recipe')}\n"
            context += f"   URL: {result.get('url', '')}\n"
            if result.get('snippet'):
                context += f"   Description: {result['snippet']}\n"
            context += "\n"
        
        if recipe_details and recipe_details.get("success"):
            context += "\nDetailed Recipe Information:\n"
            if recipe_details.get("title"):
                context += f"Title: {recipe_details['title']}\n"
            if recipe_details.get("ingredients"):
                context += "\nIngredients:\n"
                for ing in recipe_details['ingredients'][:15]:
                    context += f"- {ing}\n"
            if recipe_details.get("instructions"):
                context += "\nInstructions:\n"
                for i, step in enumerate(recipe_details['instructions'][:8], 1):
                    context += f"{i}. {step}\n"
            if recipe_details.get("url"):
                context += f"\nSource URL: {recipe_details['url']}\n"
        
        return context
    
    def _summarize_with_llm(self, context: str, query: str, source: str) -> str:
        """
        Use Gemini LLM to summarize and extract facts from context
        
        Args:
            context: Recipe context from RAG DB or web
            query: Original user query
            source: Source of the context ("local database" or "internet")
            
        Returns:
            LLM-generated summary with facts
        """
        if not self.llm_model:
            return context  # Fallback to raw context
        
        prompt = f"""A user asked: "{query}"

I found recipe information in my {source}. Please summarize this information in a helpful, conversational way:

{context}

Instructions:
- Provide a clear, concise summary of the recipe(s)
- Include key details like ingredients, cooking time, and main steps
- Be conversational and helpful
- If this is from the internet, always cite the source URL
- Highlight the most relevant information for the user's query
- Keep it engaging and accurate"""

        try:
            response = self.llm_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"    ⚠️ LLM summarization error: {e}")
            return context  # Fallback to raw context
    
    def _combine_results(self, query: str, rag_result: Dict, 
                        web_result: Dict) -> Dict:
        """
        Combine results from pipelines into final output
        Prioritizes RAG DB results, falls back to web if no DB results
        
        Args:
            query: Original user query
            rag_result: Results from RAG DB pipeline
            web_result: Results from Web Search pipeline (may be None if not executed)
            
        Returns:
            Response dictionary with primary source results
        """
        print(f"\n🔀 Combining Results...")
        
        # Determine primary source (RAG DB takes priority)
        if rag_result["has_results"]:
            primary_source = "database"
            primary_message = rag_result["summary"]
            primary_recipes = rag_result["results"]
            print(f"  ✓ Using results from: {primary_source} ({len(primary_recipes)} recipes)")
        elif web_result and web_result["has_results"]:
            primary_source = "internet"
            primary_message = web_result["summary"]
            primary_recipes = []
            print(f"  ✓ Using results from: {primary_source} (web search fallback)")
        else:
            # Neither pipeline found results
            primary_source = "none"
            primary_message = "I couldn't find any recipes matching your request in my database or online. Please try a different query or be more specific."
            primary_recipes = []
            print(f"  ⚠️ No results found from any source")
        
        return {
            "question": query,
            "message": primary_message,
            "primary_source": primary_source,
            "rag_results": rag_result,
            "web_results": web_result,
            "recipes": primary_recipes,
            "has_database_results": rag_result["has_results"],
            "has_web_results": web_result["has_results"] if web_result else False
        }

