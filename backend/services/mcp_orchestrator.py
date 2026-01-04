"""
MCP Orchestrator - Coordinates RAG DB and Web Search pipelines
User Query → MCP Orchestrator → [RAG DB → Gemini LLM] + [Web Search → Gemini LLM] → Combined Output
"""

from typing import Dict, List, Optional
import asyncio
import time
import google.generativeai as genai
from groq import Groq
from services.recipe_scraper_pipeline import scrape_recipe_via_mcp, scrape_recipes_parallel

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

    def process_query(self, query: str, top_k: int = 10, similarity_threshold: float = 0.35, preferences=None) -> Dict:
        """
        Main MCP pipeline

        Args:
            query: User's search query
            top_k: Number of results to search initially (default: 10, will be filtered to top 3)
            similarity_threshold: Minimum similarity score (lowered to 0.50 for better recall)
            preferences: Optional user preferences (diets, skill, servings, goal)
        """
        print(f"\n{'='*60}")
        print(f"🎯 MCP Orchestrator Processing: '{query}'")
        if preferences:
            print(f"👤 User Preferences Applied:")
            print(f"   • Diets: {preferences.diets}")
            print(f"   • Skill: {preferences.skill}")
            print(f"   • Servings: {preferences.servings}")
            print(f"   • Goal: {preferences.goal}")
        print(f"{'='*60}\n")

        # Step 1: Build search query incorporating ALL 4 preferences
        # Strategy: Always use the user's query as the BASE, enhance with preferences
        
        # Expanded list of food-related terms to detect specific queries
        specific_dishes = ['paneer', 'chicken', 'tofu', 'salmon', 'lentil', 'pasta',
                          'beef', 'pork', 'shrimp', 'tikka', 'curry', 'biryani',
                          'stir fry', 'salad', 'soup', 'rice', 'noodles',
                          'lobster', 'crab', 'fish', 'tuna', 'cod', 'tilapia',
                          'broccoli', 'spinach', 'kale', 'mushroom', 'potato',
                          'lamb', 'duck', 'turkey', 'egg', 'prawn', 'scallop',
                          'steak', 'burger', 'sandwich', 'wrap', 'bowl',
                          'cake', 'cookie', 'pie', 'bread', 'muffin']

        query_lower = query.lower()
        has_specific_dish = any(dish in query_lower for dish in specific_dishes)
        
        # Check if query seems like a specific recipe request (has food-related words)
        # or a generic preference-based request (like "what should I cook?")
        generic_query_indicators = [
            'what should i', 'recommend', 'suggest', 'what can i', 
            'give me', 'show me', 'find me', 'what dishes',
            'what do you recommend', 'any ideas', 'something'
        ]
        is_generic_query = any(indicator in query_lower for indicator in generic_query_indicators)
        
        # If user has a specific query (mentions food items), USE IT as the base
        if has_specific_dish or not is_generic_query:
            # User specified something specific - enhance with preferences but KEEP their query
            search_parts = []

            # Add skill modifier
            if preferences and preferences.skill == 'Beginner':
                search_parts.append('easy')
            elif preferences and preferences.skill == 'Advanced':
                search_parts.append('gourmet')

            # Add dietary preference if it adds value
            if preferences and preferences.diets:
                dietary = preferences.diets[0]
                # Only add dietary if it's specific (not generic)
                if dietary not in ['No Preference']:
                    # Don't add "non-vegetarian" to a query like "lobster" - it's redundant
                    if dietary != 'Non-Vegetarian' or not has_specific_dish:
                        search_parts.append(dietary.lower())

            # Combine with original query - USER'S QUERY IS PRIMARY
            search_query = f"{' '.join(search_parts)} {query}" if search_parts else query
            print(f"🔍 Enhanced search query: '{search_query}'")

        elif preferences and preferences.diets:
            # Generic query like "what should I cook?" - generate based on preferences
            # Use more varied and sensible search terms
            dietary = preferences.diets[0]
            skill = preferences.skill if preferences.skill else 'Intermediate'
            goal = preferences.goal if hasattr(preferences, 'goal') and preferences.goal else None

            search_parts = []

            # Add skill level modifier - use more search-friendly terms
            skill_modifiers = {
                'Beginner': 'easy quick',
                'Intermediate': 'homemade',
                'Advanced': 'gourmet restaurant-style'
            }
            search_parts.append(skill_modifiers.get(skill, 'easy'))

            # Add dietary-appropriate search terms
            # Instead of hardcoding "chicken", use the dietary term itself for searching
            dietary_search_terms = {
                'Vegetarian': 'vegetarian dinner',
                'Vegan': 'vegan meal',
                'Non-Vegetarian': 'meat dinner',  # More generic than "chicken"
                'Gluten Free': 'gluten free meal',
                'Dairy Free': 'dairy free dinner',
                'Low Carb': 'low carb keto meal',
                'Paleo': 'paleo whole30',
                'No Preference': 'dinner'
            }
            search_parts.append(dietary_search_terms.get(dietary, 'dinner recipe'))

            # Add goal modifier if present
            if goal:
                goal_modifiers = {
                    'Energy': 'high protein',
                    'Weight Loss': 'healthy low calorie',
                    'Muscle Gain': 'high protein',
                    'General Health': 'nutritious balanced'
                }
                if goal in goal_modifiers:
                    search_parts.insert(0, goal_modifiers[goal])

            search_query = ' '.join(search_parts)
            print(f"🔍 Generated preference-based query: '{search_query}'")

        else:
            # No preferences - use original query
            search_query = query
            print(f"🔍 Database search query: '{search_query}'")

        # Step 1: RAG DB - try to find in database first
        rag_result = self._process_rag_pipeline(search_query, top_k, similarity_threshold, preferences)

        # Step 2: Web fallback if no DB results
        web_result = None
        if not rag_result["has_results"]:
            print("\n⚠️ No results in database, falling back to web search...\n")
            web_result = self._process_web_pipeline(query, preferences)
        else:
            print("\n✓ Found results in database, skipping web search")
            web_result = {"has_results": False, "search_result": None, "summary": None, "source": "Internet"}

        # Step 3: Combine
        combined_response = self._combine_results(query, rag_result, web_result)
        return combined_response

    def _process_rag_pipeline(self, query: str, top_k: int, similarity_threshold: float, preferences=None) -> Dict:
        """Query RAG DB → summarize with LLM"""
        pipeline_start = time.time()
        print("📚 RAG DB Pipeline:")
        print("  → Searching local database...")

        # Detect if user asked for a SPECIFIC protein/main ingredient FIRST
        # This is critical - if user says "lamb curry", they want LAMB, not prawn!
        import re
        query_lower = query.lower()
        
        # List of main proteins/ingredients that users might specifically request
        specific_proteins = ['lamb', 'beef', 'chicken', 'pork', 'fish', 'salmon', 'tuna', 
                            'shrimp', 'prawn', 'lobster', 'crab', 'turkey', 'duck',
                            'tofu', 'paneer', 'tempeh', 'seitan']
        
        # Find which specific protein the user asked for
        requested_protein = None
        for protein in specific_proteins:
            if protein in query_lower:
                requested_protein = protein
                print(f"  🎯 User specifically requested: {protein.upper()}")
                break
        
        # If user requested a specific protein, get MORE candidates with LOWER threshold
        # This allows us to find recipes that match the protein even if semantic similarity is lower
        if requested_protein:
            # Get more candidates with much lower threshold - we'll filter after boosting
            rag_results = self.rag_engine.search_recipes(query, top_k=top_k * 5, min_score=0.10)
            print(f"  📊 Expanded search for '{requested_protein}': got {len(rag_results)} candidates")
        else:
            rag_results = self.rag_engine.search_recipes(query, top_k=top_k)

        rag_summary = None
        rag_facts = []
        rag_has_results = False
        filtered_results = []
        collection_pages = []  # Track collection pages to extract from

        if rag_results and len(rag_results) > 0:
            # Check if we have any results above threshold OR with keyword matches
            valid_results = []
            for result in rag_results:
                score = result.get('score', 0.0)
                has_keyword = result.get('keyword_match', False)
                title = result.get('metadata', {}).get('title', '')

                # Detect collection pages - DON'T filter them out, scrape them for individual recipes!
                import re

                # Check if title has number + recipes/snacks/dishes (e.g., "56 vegan snacks")
                has_number_list = bool(re.search(r'\d+\s+(vegan|vegetarian|paleo|keto)?\s*(snacks|recipes|dishes)', title.lower()))

                # Check if title ends with " recipes" (e.g., "Easy vegetarian recipes", "Dinner recipes")
                # But NOT single-dish recipes like "Chicken curry recipe"
                title_lower = title.lower()
                ends_with_recipes = title_lower.endswith(' recipes') or title_lower.endswith('recipes |')

                collection_keywords = ['best', 'top', 'ideas', 'collection',
                                      'easy recipes', 'batch cooking recipes', 'dinner recipes',
                                      'lunch recipes', 'breakfast recipes', 'snack recipes']

                is_collection = any(keyword in title_lower for keyword in collection_keywords) or has_number_list or ends_with_recipes

                if is_collection:
                    # Collection page found - we'll scrape it for individual recipes
                    print(f"  📚 Collection page found: {title[:60]}")
                    collection_url = result.get('metadata', {}).get('url', '')
                    if collection_url:
                        print(f"     URL: {collection_url[:70]}")
                        collection_pages.append({
                            'title': title,
                            'url': collection_url,
                            'from_database': True
                        })
                    continue

                # Apply dietary preference filtering
                if preferences and preferences.diets:
                    recipe_title = title.lower()
                    recipe_ingredients = ' '.join(result.get('metadata', {}).get('ingredients', [])).lower()

                    # Check if recipe matches dietary preferences
                    dietary_match = self._check_dietary_compatibility(
                        recipe_title,
                        recipe_ingredients,
                        preferences.diets
                    )

                    if not dietary_match:
                        print(f"  ⚬ Filtered (diet): {title[:50]} (not {', '.join(preferences.diets).lower()})")
                        continue

                # Apply servings filtering (if specified)
                if preferences and preferences.servings:
                    recipe_metadata = result.get('metadata', {})
                    recipe_servings_text = str(recipe_metadata.get('facts', {}).get('servings', ''))
                    recipe_title_lower = title.lower()

                    # Check if recipe is for the requested servings
                    # Look for servings in metadata or title (e.g., "for two", "serves 2")
                    if preferences.servings == 2:
                        # Looking for 2 servings
                        matches_servings = (
                            'for two' in recipe_title_lower or
                            'for 2' in recipe_title_lower or
                            '2' in recipe_servings_text or
                            'two' in recipe_servings_text
                        )
                        # Boost score if it matches servings perfectly
                        if matches_servings:
                            score = min(1.0, score + 0.05)  # 5% boost for matching servings
                    elif preferences.servings == 4:
                        matches_servings = (
                            '4' in recipe_servings_text or
                            'four' in recipe_servings_text or
                            '3-4' in recipe_servings_text or
                            '4-6' in recipe_servings_text
                        )
                        if matches_servings:
                            score = min(1.0, score + 0.05)

                # Apply skill level boost (don't filter, just boost scores)
                if preferences and preferences.skill:
                    recipe_title_lower = title.lower()
                    recipe_instructions = result.get('metadata', {}).get('instructions', [])
                    num_steps = len(recipe_instructions) if isinstance(recipe_instructions, list) else 0

                    if preferences.skill == 'Beginner':
                        # Boost easy/quick/simple recipes
                        if any(word in recipe_title_lower for word in ['easy', 'simple', 'quick', 'minute']):
                            score = min(1.0, score + 0.03)
                        # Boost recipes with fewer steps
                        if num_steps > 0 and num_steps <= 5:
                            score = min(1.0, score + 0.02)
                    elif preferences.skill == 'Advanced':
                        # Boost complex recipes
                        if any(word in recipe_title_lower for word in ['gourmet', 'classic', 'traditional']):
                            score = min(1.0, score + 0.03)
                        # Boost recipes with more steps
                        if num_steps > 8:
                            score = min(1.0, score + 0.02)

                # CRITICAL: Apply MAJOR boost for recipes matching user's specific protein request
                # If user asked for "lamb curry", a lamb recipe should rank much higher than prawn!
                if requested_protein:
                    recipe_title_lower = title.lower()
                    recipe_ingredients = ' '.join(result.get('metadata', {}).get('ingredients', [])).lower()
                    
                    # Check if recipe contains the requested protein
                    protein_in_title = requested_protein in recipe_title_lower
                    protein_in_ingredients = requested_protein in recipe_ingredients
                    
                    if protein_in_title:
                        # Major boost if protein is in title (most relevant)
                        score = min(1.0, score + 0.30)
                        print(f"    🎯 +30% boost: '{title[:40]}' has {requested_protein} in title")
                    elif protein_in_ingredients:
                        # Moderate boost if protein is in ingredients
                        score = min(1.0, score + 0.15)
                        print(f"    🎯 +15% boost: '{title[:40]}' has {requested_protein} in ingredients")

                # Update the score in the result after all boosts
                result['score'] = score

                # Accept only if score meets high threshold for reliable results
                if score >= similarity_threshold:
                    valid_results.append(result)
                    print(f"  ✓ Accepted: {result.get('metadata', {}).get('title', 'Recipe')[:50]} (score: {score:.3f}, keyword: {has_keyword})")
                else:
                    print(f"  ✗ Rejected: {result.get('metadata', {}).get('title', 'Recipe')[:50]} (score: {score:.3f}, keyword: {has_keyword})")

            # Re-sort valid_results by score after all boosts have been applied
            if valid_results:
                valid_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                
            if valid_results:
                # If user requested a specific protein, check if ANY result contains it
                # If not, we should fall back to web search
                found_requested_protein = False
                if requested_protein:
                    for result in valid_results:
                        result_title = result.get('metadata', {}).get('title', '').lower()
                        result_ingredients = ' '.join(result.get('metadata', {}).get('ingredients', [])).lower()
                        if requested_protein in result_title or requested_protein in result_ingredients:
                            found_requested_protein = True
                            break
                    
                    if not found_requested_protein:
                        print(f"\n  ⚠️ No recipes found with {requested_protein.upper()} - will try web search")
                        rag_has_results = False
                        filtered_results = []
                    else:
                        rag_has_results = True
                        # Limit to exactly 3 recipes
                        filtered_results = valid_results[:3]
                        print(f"\n  ✓ Found {len(valid_results)} relevant recipes (including {requested_protein}), limited to {len(filtered_results)}")
                else:
                    rag_has_results = True
                    # Limit to exactly 3 recipes
                    filtered_results = valid_results[:3]
                    print(f"\n  ✓ Found {len(valid_results)} relevant recipes, limited to {len(filtered_results)}")

                # Skip AI summary - just return recipes directly
                rag_summary = ""  # No AI text, just show recipe cards

                recipe_ids = [r['id'] for r in filtered_results]
                recipe_context = self.rag_engine.get_recipe_context(recipe_ids, detailed=True)

                print("  → Generating culinary facts...")
                try:
                    rag_facts = self._generate_facts(recipe_context, query)
                    print(f"  ✓ Generated {len(rag_facts)} facts")
                except Exception as e:
                    print(f"  ⚠️ Failed to generate facts: {e}")
                    rag_facts = []
                print("  ✓ RAG DB processing complete")
            else:
                print(f"  ⚠️ No results met criteria (threshold: {similarity_threshold})")
        else:
            print("  ⚠️ No results found in local database")

        # If we only found collection pages in database, mark as no results to trigger web search
        if collection_pages and not filtered_results:
            print(f"\n  → Found {len(collection_pages)} collection pages in database (not individual recipes)")
            print(f"  → Database has no individual recipes - will fall back to web search")
            rag_has_results = False

        pipeline_time = time.time() - pipeline_start
        print(f"  ⏱️  RAG pipeline took {pipeline_time:.2f}s")

        return {
            "has_results": rag_has_results,
            "results": filtered_results,
            "summary": rag_summary,
            "facts": rag_facts,
            "source": "RAG Database"
        }

    def _check_dietary_compatibility(self, title: str, ingredients: str, diet_preferences: List[str]) -> bool:
        """Check if a recipe matches dietary preferences"""
        # Common non-vegan/non-vegetarian ingredients
        non_vegan_ingredients = ['chicken', 'beef', 'pork', 'fish', 'lamb', 'turkey', 'bacon', 'sausage',
                                 'meat', 'egg', 'milk', 'cheese', 'butter', 'cream', 'yogurt', 'honey',
                                 'whey', 'gelatin', 'lard']
        non_vegetarian_ingredients = ['chicken', 'beef', 'pork', 'fish', 'lamb', 'turkey', 'bacon',
                                      'sausage', 'meat', 'seafood', 'prawn', 'shrimp', 'salmon', 'tuna',
                                      'duck', 'venison', 'steak', 'meatball', 'ham']

        # Check if user has both non-vegetarian and low-carb preferences
        has_non_veg = any(d.lower() in ['non-vegetarian', 'non vegetarian'] for d in diet_preferences)
        has_low_carb = any(d.lower() in ['keto', 'low carb'] for d in diet_preferences)

        # Check if recipe has meat (for combined preference handling)
        has_meat = any(ingredient in ingredients.lower() or ingredient in title.lower()
                      for ingredient in non_vegetarian_ingredients)

        # Check each dietary preference
        for diet in diet_preferences:
            diet_lower = diet.lower()

            if diet_lower == 'vegan':
                # For vegan, check if recipe contains any non-vegan ingredients
                for ingredient in non_vegan_ingredients:
                    if ingredient in ingredients or ingredient in title:
                        return False

            elif diet_lower == 'vegetarian':
                # For vegetarian, check if recipe contains meat/fish
                for ingredient in non_vegetarian_ingredients:
                    if ingredient in ingredients or ingredient in title:
                        return False

            elif diet_lower == 'non-vegetarian' or diet_lower == 'non vegetarian':
                # For non-vegetarian, recipe MUST contain meat/fish
                if not has_meat:
                    return False  # Reject if no meat found

            elif diet_lower in ['keto', 'low carb']:
                # Keto/low carb - avoid high-carb ingredients
                # IMPORTANT: If user also selected Non-Vegetarian, be lenient on carbs
                # Many meat dishes come with rice/pasta, and user wants meat primarily
                high_carb = ['rice', 'pasta', 'bread', 'potato', 'noodle', 'flour', 'sugar']
                has_high_carb = any(carb in ingredients or carb in title for carb in high_carb)

                # If user wants both non-veg AND low-carb, only reject very high-carb dishes without meat
                if has_non_veg and has_low_carb:
                    # For combined preference: allow meat dishes even with some carbs
                    # Only reject if it's very high-carb (pasta/bread/noodles) AND explicitly vegetarian/vegan
                    very_high_carb = ['pasta', 'bread', 'noodle', 'flour']
                    is_very_high_carb = any(carb in ingredients.lower() or carb in title.lower() for carb in very_high_carb)
                    if is_very_high_carb and not has_meat:
                        if not any(kw in title.lower() for kw in ['keto', 'low carb', 'cauliflower']):
                            return False
                else:
                    # Standard low-carb check (when NOT combined with non-veg)
                    if has_high_carb and not any(kw in title for kw in ['keto', 'low carb', 'cauliflower']):
                        return False

            elif diet_lower == 'gluten free':
                # Gluten free - avoid wheat, barley, rye
                gluten_ingredients = ['wheat', 'flour', 'pasta', 'bread', 'barley', 'rye', 'noodle']
                # Allow if explicitly says gluten-free
                if any(g in ingredients for g in gluten_ingredients):
                    if 'gluten free' not in title and 'gluten-free' not in ingredients:
                        return False

            elif diet_lower == 'dairy free':
                # Dairy free
                dairy = ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'whey']
                if any(d in ingredients for d in dairy):
                    if 'dairy free' not in title and 'dairy-free' not in ingredients:
                        return False

            elif diet_lower == 'paleo':
                # Paleo - avoid grains, legumes, dairy, refined sugar
                non_paleo = ['grain', 'rice', 'wheat', 'pasta', 'bread', 'oat', 'bean', 'lentil',
                            'peanut', 'soy', 'tofu', 'dairy', 'milk', 'cheese', 'sugar', 'corn']
                # Allow if explicitly says paleo
                has_non_paleo = any(item in ingredients.lower() or item in title.lower() for item in non_paleo)
                if has_non_paleo and 'paleo' not in title.lower():
                    return False

        return True

    def _is_valid_recipe(self, recipe: Dict) -> bool:
        """
        Validate that a scraped result is actually a recipe with real food content.
        Filters out navigation pages, news articles, and other non-recipe content.
        """
        title = recipe.get('title', '').lower()
        ingredients = recipe.get('ingredients', [])

        # Check for non-recipe indicators in title
        invalid_titles = ['news', 'trends', 'subscribe', 'newsletter', 'sign up',
                         'download', 'app', 'contact', 'about', 'privacy']
        if any(invalid in title for invalid in invalid_titles):
            return False

        # Must have ingredients
        if not ingredients or len(ingredients) == 0:
            return False

        # Check if ingredients look like real food
        # Non-food "ingredients" that indicate this isn't a recipe
        non_food_terms = ['subscribe', 'newsletter', 'sign up', 'download', 'app',
                         'social', 'follow', 'facebook', 'instagram', 'twitter',
                         'email', 'contact', 'privacy', 'terms', 'policy',
                         'advertisement', 'sponsored', 'affiliate']

        ingredients_text = ' '.join(ingredients).lower()

        # If more than 30% of ingredients contain non-food terms, reject
        non_food_count = sum(1 for term in non_food_terms if term in ingredients_text)
        if non_food_count > len(ingredients) * 0.3:
            return False

        # Check for at least some real food ingredients
        real_food_indicators = ['chicken', 'beef', 'pork', 'fish', 'rice', 'pasta',
                               'tomato', 'onion', 'garlic', 'salt', 'pepper', 'oil',
                               'flour', 'sugar', 'butter', 'milk', 'egg', 'cheese',
                               'vegetable', 'fruit', 'herb', 'spice', 'water',
                               'paneer', 'tofu', 'lentil', 'bean', 'chickpea',
                               'potato', 'carrot', 'broccoli', 'spinach', 'kale',
                               'quinoa', 'oat', 'almond', 'cashew', 'coconut']

        has_real_food = any(food in ingredients_text for food in real_food_indicators)

        return has_real_food

    def _process_web_pipeline(self, query: str, preferences=None) -> Dict:
        """Query web → scrape URLs via MCP → summarize with LLM"""
        pipeline_start = time.time()
        print("\n🌐 Web Search Pipeline:")
        print("  → Searching internet...")

        # Build search query: ALWAYS include user's query, enhance with preferences
        query_lower = query.lower()
        
        # Check if query already has "recipe" in it
        has_recipe_word = 'recipe' in query_lower
        
        # Check if user's query mentions specific foods (not just generic preference requests)
        specific_food_terms = ['lobster', 'chicken', 'salmon', 'beef', 'pork', 'lamb', 'fish',
                               'shrimp', 'crab', 'tofu', 'paneer', 'broccoli', 'pasta', 'rice',
                               'curry', 'soup', 'salad', 'steak', 'burger', 'cake', 'bread']
        has_specific_food = any(term in query_lower for term in specific_food_terms)
        
        # Generic queries that indicate user wants preferences-based suggestions
        generic_indicators = ['what should', 'recommend', 'suggest', 'what can', 'any ideas', 'what dishes']
        is_generic_query = any(indicator in query_lower for indicator in generic_indicators)
        
        if has_specific_food or not is_generic_query:
            # User has a specific query - USE IT, optionally enhance with preferences
            if has_recipe_word:
                search_query = query
            else:
                search_query = f"{query} recipe"
            
            # Add dietary modifier only if it adds value and isn't redundant
            if preferences and preferences.diets and preferences.diets[0] not in ['No Preference']:
                dietary = preferences.diets[0].lower()
                # Don't add "non-vegetarian" to queries with specific meats - redundant
                if dietary == 'non-vegetarian' and has_specific_food:
                    pass  # Skip, it's redundant
                elif dietary not in search_query.lower():
                    search_query = f"{dietary} {search_query}"
            
            print(f"  → Searching for: '{search_query}'")
        else:
            # Generic query - generate based on preferences
            if preferences and preferences.diets and preferences.diets[0] not in ['No Preference']:
                primary_diet = preferences.diets[0].lower()
                search_query = f'{primary_diet} recipe'
            else:
                search_query = f"{query} recipe"
            print(f"  → Searching for: '{search_query}'")

        search_start = time.time()
        web_search_result = self.mcp_tools.search_recipe_web(query=search_query, max_results=5)
        search_time = time.time() - search_start
        print(f"  ⏱️  DuckDuckGo search took {search_time:.2f}s")

        web_summary = None
        web_facts = []
        web_has_results = False
        collection_pages = []
        actual_recipes = []

        if web_search_result.get("success") and web_search_result.get("results"):
            web_has_results = True
            results = web_search_result["results"]
            print(f"  ✓ Found {len(results)} recipe sources online")

            # Scrape recipe details for each URL IN PARALLEL for faster performance
            urls_to_scrape = [r.get("url") for r in results[:5] if r.get("url")]

            print(f"  → Scraping {len(urls_to_scrape)} recipes in parallel...")
            scrape_start = time.time()
            try:
                # Use asyncio.run to execute parallel scraping
                scraped_recipes = asyncio.run(scrape_recipes_parallel(urls_to_scrape))
                scrape_time = time.time() - scrape_start
                print(f"  ⏱️  Parallel scraping took {scrape_time:.2f}s")

                # Filter out failed recipes
                valid_recipes = []
                for idx, recipe_data in enumerate(scraped_recipes, 1):
                    if recipe_data and recipe_data.get("title") != "Could not fetch recipe":
                        valid_recipes.append(recipe_data)
                        print(f"  [{idx}] ✓ Success: {recipe_data.get('title', 'Unknown')[:50]}")
                    else:
                        print(f"  [{idx}] ✗ Failed to extract recipe data")

                scraped_recipes = valid_recipes
                print(f"  ✓ Successfully scraped {len(scraped_recipes)} recipes")
            except Exception as e:
                print(f"  ✗ Parallel scraping failed: {str(e)[:80]}")
                scraped_recipes = []

            if scraped_recipes:
                # Check for obvious collection indicators (MORE COMPREHENSIVE)
                # Note: These are checked against LOWERCASE title
                collection_keywords = [
                    'best', 'top', 'ideas', 'collection', 'recipes |',
                    'non-vegetarian recipes', 'vegetarian recipes', 'vegan recipes',
                    'non veg recipes', 'veg recipes', 'easy recipes',
                    '10 best', '14 best', '9 best', '20 best', '40+', '672',  # Number patterns
                    'dinner recipes', 'lunch recipes', 'breakfast recipes',
                    'keto recipes', 'paleo recipes', 'low carb recipes', 'low-carb recipes',
                    'gluten free recipes', 'gluten-free recipes', 'dairy free recipes', 'dairy-free recipes',
                    'free paleo', 'favorite paleo', 'healthy vegan',
                    'mouthwatering', 'crave-worthy', 'add to your', 'weekly menu',
                    # Generic collection endings
                    'recipes for', 'recipe ideas', 'meal ideas', 'dinner ideas',
                    # Catch standalone "X Recipes" patterns
                    'healthy recipes', 'quick recipes', 'simple recipes',
                    # Very short generic titles that are likely categories, not dishes
                    'paneer recipes', 'chicken recipes', 'beef recipes', 'fish recipes',
                    'pasta recipes', 'salad recipes', 'soup recipes', 'curry recipes',
                ]
                collection_page_urls = []

                for recipe in scraped_recipes:
                    title = recipe.get('title', '').lower().strip()
                    
                    # Skip very short titles - likely category names, not dish names
                    # e.g., "Non-Veg", "Paneer", "Recipes"
                    if len(title) < 10:
                        collection_url = recipe.get('source', '')
                        collection_page_urls.append(collection_url)
                        collection_pages.append({
                            'title': recipe.get('title', 'Recipe Collection'),
                            'url': collection_url
                        })
                        print(f"    📚 Too short, likely category: {recipe.get('title', 'Recipe')[:60]}")
                        continue

                    # Check for collection keywords OR number patterns (e.g., "14 Best...")
                    is_collection = any(keyword in title for keyword in collection_keywords)
                    
                    # Check if title ends with "Recipes" (plural) - strong collection indicator
                    # e.g., "Low-Carb Recipes", "Gluten-Free Recipes", "Vegan Recipes"
                    # BUT NOT "Paneer Curry Recipe" (singular) - that's a real dish!
                    import re
                    if re.search(r'\brecipes\s*$', title):  # Ends with "recipes" (PLURAL)
                        is_collection = True
                    
                    # Check for "X-Y Recipes" pattern like "Low-Carb Recipes", "Gluten-Free Recipes"
                    # BUT NOT "X-Y Recipe" (singular)
                    if re.search(r'\w+-\w+\s+recipes\b', title):  # Must be plural "recipes"
                        is_collection = True

                    # Also check if title has number patterns (strong indicator of listicle)
                    # Patterns: "672 Low Carb", "41 Keto", "40+ of Our", "100 Mouthwatering"
                    if re.search(r'\d+[\+]?\s+(low carb|keto|paleo|vegan|recipes?|of our|favorite|healthy|easy|best|paneer|chicken)', title):
                        is_collection = True
                    # Pattern: Starts with number (like "21 Easy Paneer Recipes", "35+ Indian Recipes")
                    if re.match(r'^\d+[\+]?\s+', title):
                        is_collection = True
                    
                    # Pattern: Title contains colon followed by list indicators
                    # e.g., "Gluten-Free Recipes: Cakes, Cookies, Bread & More"
                    if ':' in title and any(word in title for word in ['&', 'and more', 'more']):
                        is_collection = True

                    if not is_collection:
                        actual_recipes.append(recipe)
                        print(f"    ✅ {recipe.get('title', 'Recipe')[:60]}")
                    else:
                        # This is a collection page - save URL to extract recipes from it
                        collection_url = recipe.get('source', '')
                        collection_page_urls.append(collection_url)
                        collection_pages.append({
                            'title': recipe.get('title', 'Recipe Collection'),
                            'url': collection_url
                        })
                        print(f"    📚 Collection page found: {recipe.get('title', 'Recipe')[:60]}")

                # ALWAYS extract from collection pages if we found them, even if we have some recipes
                # This ensures we get actual dish recipes instead of collection page titles
                if collection_page_urls:
                    print(f"\n  → Found {len(collection_page_urls)} collection pages")
                    print(f"  → Current actual_recipes: {len(actual_recipes)}")
                    print(f"  → Extracting individual recipes from collection pages...")

                    collection_start = time.time()
                    from services.recipe_scraper_pipeline import scrape_recipes_from_collection
                    
                    def is_collection_title(title: str) -> bool:
                        """Check if a title indicates a collection/listicle rather than a single dish"""
                        import re
                        title_lower = title.lower().strip()
                        
                        # Very short titles are likely categories, not dishes
                        if len(title_lower) < 10:
                            return True
                        
                        # Direct keyword match
                        if any(kw in title_lower for kw in collection_keywords):
                            return True
                        
                        # Ends with "Recipes" (PLURAL) - collection indicator
                        # BUT NOT "Recipe" (singular) - that's a real dish!
                        if re.search(r'\brecipes\s*$', title_lower):
                            return True
                        
                        # "X-Y Recipes" pattern like "Low-Carb Recipes", "Gluten-Free Recipes"
                        # BUT NOT "X-Y Recipe" (singular)
                        if re.search(r'\w+-\w+\s+recipes\b', title_lower):
                            return True
                        
                        # Starts with a number (like "21 Easy Paneer Recipes")
                        if re.match(r'^\d+[\+]?\s+', title_lower):
                            return True
                        
                        # Contains colon followed by list indicators
                        if ':' in title_lower and any(word in title_lower for word in ['&', 'and more', 'more']):
                            return True
                        
                        return False

                    for col_url in collection_page_urls[:2]:  # Check first 2 collection pages
                        print(f"\n  📚 Extracting from collection: {col_url[:70]}...")

                        try:
                            # Use scrape_recipes_from_collection which handles both:
                            # 1. Rich ItemList (recipes embedded in JSON-LD) 
                            # 2. Multi-page collections (separate URLs to scrape)
                            collection_result = scrape_recipes_from_collection(col_url, max_recipes=5)
                            
                            extracted_recipes = collection_result.get('recipes', [])
                            collection_type = collection_result.get('type', 'unknown')
                            
                            if extracted_recipes:
                                print(f"    ✓ Got {len(extracted_recipes)} recipes from collection (type: {collection_type})")

                                # Process each extracted recipe
                                for individual_recipe in extracted_recipes[:3]:  # Get top 3 recipes
                                    try:
                                        recipe_title = individual_recipe.get('title', 'Recipe')
                                        
                                        if individual_recipe and recipe_title != "Could not fetch recipe":
                                            # Verify it's not another collection page using comprehensive check
                                            if not is_collection_title(recipe_title):
                                                # For rich-itemlist type, recipes may not have ingredients
                                                # Still add them if they have title and description
                                                if collection_type == 'rich-itemlist':
                                                    # Rich ItemList recipes have title, description, image but no ingredients
                                                    if individual_recipe.get('title') and individual_recipe.get('description'):
                                                        actual_recipes.append(individual_recipe)
                                                        print(f"      ✅ {recipe_title[:50]}")
                                                        
                                                        if len(actual_recipes) >= 3:
                                                            break
                                                    else:
                                                        print(f"      ⚬ Skipped (no description): {recipe_title[:40]}")
                                                else:
                                                    # Multi-page recipes should have ingredients
                                                    if self._is_valid_recipe(individual_recipe):
                                                        actual_recipes.append(individual_recipe)
                                                        print(f"      ✅ {recipe_title[:50]}")

                                                        if len(actual_recipes) >= 3:
                                                            break
                                                    else:
                                                        print(f"      ⚬ Skipped (invalid/non-recipe content): {recipe_title[:40]}")
                                            else:
                                                print(f"      ⚬ Skipped (another collection): {recipe_title[:40]}")
                                    except Exception as e:
                                        print(f"      ✗ Failed processing recipe: {str(e)[:60]}")

                                if len(actual_recipes) >= 3:
                                    print(f"    ✓ Successfully extracted {len(actual_recipes)} recipes from collection page")
                                    break
                            else:
                                print(f"    ⚠️ No recipes found in collection page")

                        except Exception as e:
                            print(f"    ✗ Error extracting from collection: {str(e)[:60]}")

                    collection_time = time.time() - collection_start
                    print(f"  ⏱️  Collection extraction took {collection_time:.2f}s")

                if not actual_recipes:
                    print(f"  ⚠️ All scraped pages were collections/listicles, no individual recipes found")
                    web_has_results = False
                    web_summary = "I found some recipe collections online, but couldn't extract specific dish recipes. Try being more specific (e.g., 'chicken tikka recipe' instead of 'non-vegetarian recipes')."
                    collection_pages = []  # Clear collection pages so frontend doesn't show them
                else:
                    # Limit to exactly 3 recipes for the recommendation
                    actual_recipes = actual_recipes[:3]
                    print(f"  → Limited to {len(actual_recipes)} recipes for recommendation")

                    # Skip AI summary - just return empty string so recipes are shown directly
                    web_summary = ""  # No AI text, recipes will be displayed as cards

                    # Prepare context for facts generation
                    web_context = self._format_web_context(results, actual_recipes)

                    print("  → Generating culinary facts...")
                    facts_start = time.time()
                    try:
                        web_facts = self._generate_facts(web_context, query)
                        facts_time = time.time() - facts_start
                        print(f"  ⏱️  Facts generation took {facts_time:.2f}s")
                        print(f"  ✓ Generated {len(web_facts)} facts")
                    except Exception as e:
                        print(f"  ⚠️ Failed to generate facts: {e}")
                        web_facts = []

                    pipeline_time = time.time() - pipeline_start
                    print(f"  ⏱️  Total web pipeline took {pipeline_time:.2f}s")
                    print("  ✓ Web search complete")
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
            "source": "Internet",
            "collection_pages": collection_pages,
            "recipes": actual_recipes  # Return the filtered, scraped recipes
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

        I found recipe information in my {source}. Please provide a personalized recommendation for EXACTLY 3 DISHES:

        {context}

        CRITICAL INSTRUCTIONS:
        - Act as a friendly AI chef giving personalized recommendations
        - Recommend EXACTLY 3 SPECIFIC DISH NAMES from the recipes found
        - ONLY mention actual dish names (e.g., "Grilled Chicken Tikka", "Palak Paneer", "Chickpea Curry")
        - DO NOT mention collection pages or listicle titles (DON'T say "9 best recipes")
        - Briefly explain WHY these 3 dishes match their preferences (diet, skill level, goal)
        - Format: "Based on your preferences, I recommend: [Dish 1], [Dish 2], and [Dish 3]. [Brief reason]."
        - Maximum 3 sentences total

        BAD examples (DON'T DO THIS):
        ❌ "I found 3 delicious paneer recipes for you!"
        ❌ "Check out these 9 best non vegetarian recipes"
        ❌ "Here are some vegan options"

        GOOD examples (DO THIS):
        ✅ "Based on your preferences, I recommend: Palak Paneer, Paneer Butter Masala, and Garlic Paneer. All three are vegetarian, beginner-friendly, and packed with protein!"
        ✅ "I suggest: Chickpea Buddha Bowl, Mediterranean Quinoa Salad, and Lentil Curry. These vegan dishes are quick to make and perfect for weight loss!"
        ✅ "Try: Grilled Chicken Tikka, Butter Chicken, and Tandoori Chicken. All are easy to prepare and high in protein for muscle gain!"
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
            "has_web_results": web_result["has_results"] if web_result else False,
            "collection_pages": web_result.get("collection_pages", []) if web_result else []
        }