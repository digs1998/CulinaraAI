"""
MCP Orchestrator - Coordinates RAG DB and Web Search pipelines
User Query → MCP Orchestrator → [RAG DB → Gemini LLM] + [Web Search → Gemini LLM] → Combined Output
"""

from typing import Dict, List, Optional
import google.generativeai as genai
from groq import Groq
from services.recipe_scraper_pipeline import scrape_recipe_via_mcp

class MCPOrchestrator:
    """Orchestrates RAG DB and Web Search pipelines with Groq/Gemini LLM"""

    def __init__(self, rag_engine, mcp_tools):
        """
        Initialize MCP Orchestrator

        Args:
            rag_engine: RecipeRAGEngine instance for database search
            mcp_tools: MCPRecipeTools instance for web search
        """
        self.rag_engine = rag_engine
        self.mcp_tools = mcp_tools
        self.groq_client = None
        self.gemini_model = None

        import os
        from dotenv import load_dotenv
        load_dotenv()

        # Initialize Groq (primary LLM - fast and generous free tier)
        groq_api_key = os.getenv("GROQ_API_KEY")
        print(f"🔑 Groq API Key present: {bool(groq_api_key)}")

        if groq_api_key:
            try:
                self.groq_client = Groq(api_key=groq_api_key)
                print(f"✅ Groq client initialized successfully (primary LLM)")
            except Exception as e:
                print(f"⚠️ Failed to initialize Groq: {e}")
                self.groq_client = None

        # Initialize Gemini (fallback LLM)
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        print(f"🔑 Gemini API Key present: {bool(gemini_api_key)}")

        if gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                model_name = getattr(self.rag_engine, "generation_model", "gemini-1.5-flash")
                print(f"🤖 Initializing Gemini model: {model_name} (fallback LLM)")
                self.gemini_model = genai.GenerativeModel(model_name=model_name)
                print(f"✅ Gemini model initialized successfully")
            except Exception as e:
                print(f"⚠️ Failed to initialize Gemini model: {e}")
                self.gemini_model = None

        if not self.groq_client and not self.gemini_model:
            print("❌ No LLM available - facts generation will fail!")
        elif self.groq_client:
            print("🎯 Using Groq as primary LLM for facts generation")
        else:
            print("🎯 Using Gemini as primary LLM for facts generation")

    def process_query(self, query: str, top_k: int = 3, similarity_threshold: float = 0.50) -> Dict:
        """
        Main MCP pipeline
        
        Args:
            query: User's search query
            top_k: Number of results to return (default: 3 for top 3)
            similarity_threshold: Minimum similarity score (lowered to 0.50 for better recall)
        """
        print(f"\n{'='*60}")
        print(f"🎯 MCP Orchestrator Processing: '{query}'")
        print(f"{'='*60}\n")

        # Step 1: RAG DB - try to find in database first
        rag_result = self._process_rag_pipeline(query, top_k, similarity_threshold)

        # Step 2: Web fallback if no DB results
        web_result = None
        if not rag_result["has_results"]:
            print("\n⚠️ No results in database, falling back to web search...\n")
            web_result = self._process_web_pipeline(query)
        else:
            print("\n✓ Found results in database, skipping web search")
            web_result = {"has_results": False, "search_result": None, "summary": None, "source": "Internet"}

        # Step 3: Combine
        combined_response = self._combine_results(query, rag_result, web_result)
        return combined_response

    def _process_rag_pipeline(self, query: str, top_k: int, similarity_threshold: float) -> Dict:
        """Query RAG DB → summarize with LLM"""
        print("📚 RAG DB Pipeline:")
        print("  → Searching local database...")

        rag_results = self.rag_engine.search_recipes(query, top_k=top_k)

        rag_summary = None
        rag_facts = []
        rag_has_results = False
        filtered_results = []

        if rag_results and len(rag_results) > 0:
            # Check if we have any results above threshold OR with keyword matches
            valid_results = []
            for result in rag_results:
                score = result.get('score', 0.0)
                has_keyword = result.get('keyword_match', False)

                # Accept if: (high score) OR (decent score + keyword match) OR (keyword match with okay score)
                if score >= similarity_threshold or (score >= 0.40 and has_keyword) or (has_keyword and score >= 0.35):
                    valid_results.append(result)
                    print(f"  ✓ Accepted: {result.get('metadata', {}).get('title', 'Recipe')[:50]} (score: {score:.3f}, keyword: {has_keyword})")
                else:
                    print(f"  ✗ Rejected: {result.get('metadata', {}).get('title', 'Recipe')[:50]} (score: {score:.3f}, keyword: {has_keyword})")

            if valid_results:
                rag_has_results = True
                filtered_results = valid_results
                print(f"\n  ✓ Found {len(valid_results)} relevant recipes in database")

                recipe_ids = [r['id'] for r in valid_results]
                recipe_context = self.rag_engine.get_recipe_context(recipe_ids, detailed=True)
                print("  → Summarizing with Gemini LLM...")
                rag_summary = self._summarize_with_llm(recipe_context, query, source="local database")
                print("  → Generating culinary facts...")
                try:
                    rag_facts = self._generate_facts(recipe_context, query)
                    print(f"  ✓ Generated {len(rag_facts)} facts")
                except Exception as e:
                    print(f"  ⚠️ Failed to generate facts: {e}")
                    rag_facts = []
                print("  ✓ RAG DB summary complete")
            else:
                print(f"  ⚠️ No results met criteria (threshold: {similarity_threshold})")
        else:
            print("  ⚠️ No results found in local database")

        return {
            "has_results": rag_has_results,
            "results": filtered_results,
            "summary": rag_summary,
            "facts": rag_facts,
            "source": "RAG Database"
        }

    def _process_web_pipeline(self, query: str) -> Dict:
        """Query web → scrape URLs via MCP → summarize with LLM"""
        print("\n🌐 Web Search Pipeline:")
        print("  → Searching internet...")

        web_search_result = self.mcp_tools.search_recipe_web(query=query, max_results=5)

        web_summary = None
        web_facts = []
        web_has_results = False

        if web_search_result.get("success") and web_search_result.get("results"):
            web_has_results = True
            results = web_search_result["results"]
            print(f"  ✓ Found {len(results)} recipe sources online")

            # Scrape recipe details for each URL
            scraped_recipes = []
            for idx, r in enumerate(results[:5], 1):
                url = r.get("url")
                if url:
                    print(f"  [{idx}/5] Scraping: {url[:60]}...")
                    try:
                        recipe_data = scrape_recipe_via_mcp(url)
                        if recipe_data and recipe_data.get("title") != "Could not fetch recipe":
                            scraped_recipes.append(recipe_data)
                            print(f"    ✓ Success: {recipe_data.get('title', 'Unknown')[:50]}")
                        else:
                            print(f"    ✗ Failed to extract recipe data")
                    except Exception as e:
                        print(f"    ✗ Error: {str(e)[:80]}")

            if scraped_recipes:
                # Prepare context for LLM
                web_context = self._format_web_context(results, scraped_recipes)

                # Summarize with Gemini
                print(f"\n  → Summarizing {len(scraped_recipes)} recipes with Gemini LLM...")
                web_summary = self._summarize_with_llm(web_context, query, source="internet")
                print("  → Generating culinary facts...")
                try:
                    web_facts = self._generate_facts(web_context, query)
                    print(f"  ✓ Generated {len(web_facts)} facts")
                except Exception as e:
                    print(f"  ⚠️ Failed to generate facts: {e}")
                    web_facts = []
                print("  ✓ Web search summary complete")
            else:
                web_has_results = False
                print("  ⚠️ No recipes could be scraped successfully")
                web_summary = "I found some recipe links online, but couldn't extract the detailed information. Please try a different search."
        else:
            print("  ⚠️ No results found on internet")

        return {
            "has_results": web_has_results,
            "search_result": web_search_result,
            "summary": web_summary,
            "facts": web_facts,
            "source": "Internet"
        }

    def _format_web_context(self, search_results: List[Dict], scraped_recipes: List[Dict]) -> str:
        """Format web search results + scraped recipes for LLM"""
        context = "Recipe Sources Found Online:\n\n"
        for i, r in enumerate(search_results[:5], 1):
            context += f"{i}. {r.get('title', 'Recipe')}\n"
            context += f"   URL: {r.get('url')}\n"
            if r.get("snippet"):
                context += f"   Description: {r['snippet']}\n"
            context += "\n"

        if scraped_recipes:
            context += "\nDetailed Recipes:\n"
            for recipe in scraped_recipes:
                context += f"\n{'='*40}\n"
                context += f"Title: {recipe.get('title')}\n"
                context += "\nIngredients:\n"
                for ing in recipe.get("ingredients", [])[:15]:
                    context += f"- {ing}\n"
                context += "\nInstructions:\n"
                for idx, step in enumerate(recipe.get("instructions", [])[:8], 1):
                    context += f"{idx}. {step}\n"
                if recipe.get("facts"):
                    facts = recipe["facts"]
                    context += f"\nQuick Facts:\n"
                    if facts.get('prep_time'):
                        context += f"- Prep Time: {facts.get('prep_time')}\n"
                    if facts.get('cook_time'):
                        context += f"- Cook Time: {facts.get('cook_time')}\n"
                    if facts.get('total_time'):
                        context += f"- Total Time: {facts.get('total_time')}\n"
                    if facts.get('servings'):
                        context += f"- Servings: {facts.get('servings')}\n"
                    if facts.get('calories'):
                        context += f"- Calories: {facts.get('calories')}\n"
                context += f"\nSource: {recipe.get('source')}\n"

        return context

    def _summarize_with_llm(self, context: str, query: str, source: str) -> str:
        """Summarize recipe context using Groq or Gemini LLM"""
        prompt = f"""A user asked: "{query}"

        I found recipe information in my {source}. Please provide a helpful, conversational summary:

        {context}

        Instructions:
        - Start with a brief, friendly intro (1-2 sentences)
        - Mention how many recipes were found
        - Highlight key features (e.g., "quick and easy", "under 30 minutes", "beginner-friendly")
        - Include 1-2 specific recipe names if available
        - Keep it concise (3-4 sentences total)
        - End by encouraging the user to check the detailed recipes below

        Example tone: "I found 3 delicious paneer recipes for you! These include quick options like Garlic Paneer and Paneer Tikka that take under 30 minutes. All recipes include detailed ingredients and step-by-step instructions below."
        """

        # Try Groq first (fast and reliable)
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"    ⚠️ Groq summarization error: {e}")

        # Fallback to Gemini
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                print(f"    ⚠️ Gemini summarization error: {e}")

        # Final fallback
        return f"I found relevant recipes in the {source}. Check the detailed recipe information below for ingredients and cooking instructions."

    def _generate_facts(self, context: str, query: str) -> List[str]:
        """Generate interesting culinary facts using Groq or Gemini LLM"""

        if not self.groq_client and not self.gemini_model:
            print("    ❌ No LLM available for facts generation")
            return []

        print(f"    📋 Context length: {len(context)} characters")
        print(f"    🔍 Context preview: {context[:200]}...")

        prompt = f"""Based on the user's query: "{query}" and the following recipe information:

{context}

Generate exactly ONE fun and surprising "Did you know?" fact about one of the ingredients or dishes in these recipes. Focus on:
- Surprising historical facts (e.g., "Did you know that pasta was brought to Italy from China by Marco Polo?")
- Unusual botanical or biological facts (e.g., "Did you know that broccoli is actually a flower?")
- Interesting cultural origins (e.g., "Did you know that tofu originated in China over 2,000 years ago?")
- Mind-blowing food science (e.g., "Did you know that honey is the only food that never expires?")
- Fun trivia about the ingredients used in these recipes

The fact MUST start with "Did you know that" or "Did you know". Make it fascinating, unexpected, and educational!

Examples:
- "Did you know that broccoli, cauliflower, cabbage, and Brussels sprouts all come from the same plant species?"
- "Did you know that cashews grow on the outside of a fruit called a cashew apple?"
- "Did you know that white chocolate isn't technically chocolate because it contains no cocoa solids?"

Return ONLY the single fact, nothing else. No numbering, no introduction, no conclusion.
"""

        # Try Groq first (fast and reliable)
        if self.groq_client:
            try:
                print("    🔄 Calling Groq API for facts generation...")
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=400,
                )
                fact_text = response.choices[0].message.content.strip()
                print(f"    📝 Raw fact response: {fact_text}\n")

                # Clean up any numbering or prefixes
                fact = fact_text.lstrip('0123456789.-•) ').strip()

                print(f"    ✅ Generated fact successfully")
                print(f"       {fact[:100]}...")

                return [fact]  # Return single fact in array
            except Exception as e:
                print(f"    ⚠️ Groq facts generation error: {e}")

        # Fallback to Gemini
        if self.gemini_model:
            try:
                print("    🔄 Calling Gemini API for facts generation...")
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.7, "max_output_tokens": 400}
                )

                # Check if response was blocked
                if hasattr(response, 'prompt_feedback'):
                    print(f"    📊 Prompt feedback: {response.prompt_feedback}")

                fact_text = response.text.strip()
                print(f"    📝 Raw fact response: {fact_text}\n")

                # Clean up any numbering or prefixes
                fact = fact_text.lstrip('0123456789.-•) ').strip()

                print(f"    ✅ Generated fact successfully")
                print(f"       {fact[:100]}...")

                return [fact]  # Return single fact in array
            except Exception as e:
                print(f"    ⚠️ Gemini facts generation error: {e}")

        # Final fallback if all LLMs fail
        print("    ⚠️ All LLM attempts failed, no facts available")
        return []

    def _combine_results(self, query: str, rag_result: Dict, web_result: Dict) -> Dict:
        """Combine RAG and web results into final response"""
        print("\n🔀 Combining Results...")

        primary_facts = []

        if rag_result["has_results"]:
            primary_source = "database"
            primary_message = rag_result["summary"]
            primary_recipes = rag_result["results"]
            primary_facts = rag_result.get("facts", [])
            print(f"  ✓ Using results from: {primary_source} ({len(primary_recipes)} recipes)")
        elif web_result and web_result["has_results"]:
            primary_source = "internet"
            primary_message = web_result["summary"] or "I found some recipes online. Check the details below."
            primary_recipes = []
            primary_facts = web_result.get("facts", [])
            print(f"  ✓ Using results from: {primary_source} (web search fallback)")
        else:
            primary_source = "none"
            primary_message = "I couldn't find any recipes matching your request. Try:\n- Using different keywords (e.g., 'pasta' instead of 'noodles')\n- Being more specific (e.g., 'vegetarian pasta recipes')\n- Checking your spelling"
            primary_recipes = []
            primary_facts = []
            print(f"  ⚠️ No results found from any source")

        return {
            "question": query,
            "message": primary_message,
            "primary_source": primary_source,
            "rag_results": rag_result,
            "web_results": web_result,
            "recipes": primary_recipes,
            "facts": primary_facts,
            "has_database_results": rag_result["has_results"],
            "has_web_results": web_result["has_results"] if web_result else False
        }