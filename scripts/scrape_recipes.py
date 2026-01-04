#!/usr/bin/env python3
"""
Daily recipe scraper using FREE APIs (no paywalls).
Stores recipes in Supabase PostgreSQL.

Free APIs used:
- TheMealDB: Unlimited, completely free (no API key needed)
- Edamam: 5,000 calls/month free tier (requires app_id + app_key)
- Recipe Puppy: Completely free (no API key needed)
- Tasty (via RapidAPI): 500 requests/month free tier (requires RapidAPI key)
- Spoonacular: 150 calls/day free tier (requires API key)
"""
import os
import sys
import requests
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from typing import List, Dict
import time
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    """Connect to Supabase PostgreSQL"""
    db_url = os.getenv('SUPABASE_DATABASE_URL')
    if not db_url:
        print("❌ SUPABASE_DATABASE_URL not set!")
        sys.exit(1)
    return psycopg2.connect(db_url)

def scrape_themealdb(num_recipes: int = 100) -> List[Dict]:
    """
    Scrape from TheMealDB (completely free, unlimited)
    API: https://www.themealdb.com/api.php
    """
    print(f"\n🍳 Scraping TheMealDB (target: {num_recipes} recipes)...")
    recipes = []
    url = 'https://www.themealdb.com/api/json/v1/1/random.php'

    for i in range(num_recipes):
        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if not data.get('meals'):
                    continue

                meal = data['meals'][0]

                # Extract ingredients (stored as strIngredient1, strIngredient2, etc.)
                ingredients = []
                for j in range(1, 21):  # Up to 20 ingredients
                    ingredient = meal.get(f'strIngredient{j}')
                    measure = meal.get(f'strMeasure{j}')
                    if ingredient and ingredient.strip():
                        ingredients.append(f"{measure} {ingredient}".strip())

                # Parse instructions into steps
                instructions_text = meal.get('strInstructions', '')
                instructions = [
                    step.strip()
                    for step in instructions_text.split('\n')
                    if step.strip()
                ]

                recipes.append({
                    'title': meal.get('strMeal'),
                    'ingredients': ingredients,
                    'instructions': instructions,
                    'source_url': meal.get('strSource') or f"https://www.themealdb.com/meal/{meal.get('idMeal')}",
                    'source_name': 'TheMealDB',
                    'image_url': meal.get('strMealThumb'),
                    'cuisine': meal.get('strArea'),
                    'diet_tags': [meal.get('strCategory')] if meal.get('strCategory') else [],
                    'facts': {
                        'category': meal.get('strCategory'),
                        'area': meal.get('strArea')
                    }
                })

            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{num_recipes} recipes...")

            # Small delay to be respectful to API
            time.sleep(0.2)

        except Exception as e:
            print(f"⚠️ Error fetching recipe {i+1}: {e}")
            continue

    print(f"✅ Scraped {len(recipes)} recipes from TheMealDB")
    return recipes

def scrape_edamam(num_recipes: int = 100) -> List[Dict]:
    """
    Scrape from Edamam Recipe API (5,000 calls/month free tier)
    Get key at: https://developer.edamam.com/
    """
    api_id = os.getenv('EDAMAM_APP_ID')
    api_key = os.getenv('EDAMAM_APP_KEY')

    if not api_id or not api_key:
        print("⚠️ EDAMAM_APP_ID or EDAMAM_APP_KEY not set. Skipping Edamam.")
        return []

    print(f"\n🍲 Scraping Edamam (target: {num_recipes} recipes)...")
    recipes = []
    url = 'https://api.edamam.com/api/recipes/v2'

    # Common recipe search terms to get variety
    search_terms = [
        'chicken', 'beef', 'pasta', 'salad', 'soup', 'fish', 'vegetarian',
        'dessert', 'breakfast', 'lunch', 'dinner', 'snack', 'bread', 'rice',
        'curry', 'sandwich', 'pizza', 'burger', 'steak', 'cake'
    ]

    recipes_per_term = max(1, num_recipes // len(search_terms))

    for term in search_terms:
        if len(recipes) >= num_recipes:
            break

        try:
            response = requests.get(
                url,
                params={
                    'type': 'public',
                    'q': term,
                    'app_id': api_id,
                    'app_key': api_key,
                    'to': recipes_per_term,
                    'random': 'true'
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()

                for hit in data.get('hits', []):
                    recipe = hit.get('recipe', {})

                    # Parse ingredients
                    ingredients = recipe.get('ingredientLines', [])

                    # Edamam doesn't provide instructions, so we note that
                    instructions = [
                        f"See original recipe at: {recipe.get('url', 'N/A')}"
                    ]

                    # Get nutrition info
                    total_nutrients = recipe.get('totalNutrients', {})

                    recipes.append({
                        'title': recipe.get('label'),
                        'ingredients': ingredients,
                        'instructions': instructions,
                        'source_url': recipe.get('url'),
                        'source_name': 'Edamam',
                        'prep_time': None,
                        'cook_time': recipe.get('totalTime'),
                        'servings': recipe.get('yield'),
                        'image_url': recipe.get('image'),
                        'cuisine': recipe.get('cuisineType', [''])[0] if recipe.get('cuisineType') else None,
                        'diet_tags': recipe.get('dietLabels', []) + recipe.get('healthLabels', []),
                        'facts': {
                            'calories': total_nutrients.get('ENERC_KCAL', {}).get('quantity'),
                            'protein': total_nutrients.get('PROCNT', {}).get('quantity'),
                            'carbohydrates': total_nutrients.get('CHOCDF', {}).get('quantity'),
                            'fat': total_nutrients.get('FAT', {}).get('quantity'),
                            'fiber': total_nutrients.get('FIBTG', {}).get('quantity'),
                            'meal_type': recipe.get('mealType', []),
                            'dish_type': recipe.get('dishType', [])
                        }
                    })

                print(f"  ✓ Found {len(data.get('hits', []))} recipes for '{term}'")

            elif response.status_code == 429:
                print(f"⚠️ Edamam API rate limit reached")
                break
            else:
                print(f"⚠️ Edamam API failed for '{term}': {response.status_code}")

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"⚠️ Error fetching from Edamam for '{term}': {e}")
            continue

    print(f"✅ Scraped {len(recipes)} recipes from Edamam")
    return recipes

def scrape_recipepuppy(num_recipes: int = 100) -> List[Dict]:
    """
    Scrape from Recipe Puppy API (completely free, no API key needed!)
    API: http://www.recipepuppy.com/about/api/
    Note: API is sometimes slow or unreliable
    """
    print(f"\n🐶 Scraping Recipe Puppy (target: {num_recipes} recipes)...")
    recipes = []
    url = 'http://www.recipepuppy.com/api/'

    # Search with various ingredients
    search_terms = [
        'chicken', 'beef', 'pasta', 'rice', 'fish', 'eggs', 'cheese',
        'potato', 'tomato', 'garlic', 'onion', 'carrot', 'mushroom'
    ]

    recipes_per_term = max(1, num_recipes // len(search_terms))

    for term in search_terms:
        if len(recipes) >= num_recipes:
            break

        try:
            response = requests.get(
                url,
                params={
                    'i': term,
                    'p': 1  # page number
                },
                timeout=20  # Recipe Puppy can be slow
            )

            if response.status_code == 200:
                data = response.json()

                for recipe in data.get('results', []):
                    # Parse ingredients (comma-separated string)
                    ingredients_str = recipe.get('ingredients', '')
                    ingredients = [
                        ing.strip()
                        for ing in ingredients_str.split(',')
                        if ing.strip()
                    ]

                    # Recipe Puppy doesn't provide instructions
                    instructions = [
                        f"See original recipe at: {recipe.get('href', 'N/A')}"
                    ]

                    recipes.append({
                        'title': recipe.get('title'),
                        'ingredients': ingredients,
                        'instructions': instructions,
                        'source_url': recipe.get('href'),
                        'source_name': 'Recipe Puppy',
                        'image_url': recipe.get('thumbnail'),
                        'facts': {}
                    })

                print(f"  ✓ Found {len(data.get('results', []))} recipes for '{term}'")

            else:
                print(f"⚠️ Recipe Puppy failed for '{term}': {response.status_code}")

            time.sleep(1.0)  # Be gentle with free API

        except Exception as e:
            print(f"⚠️ Error fetching from Recipe Puppy for '{term}': {e}")
            continue

    print(f"✅ Scraped {len(recipes)} recipes from Recipe Puppy")
    return recipes

def scrape_tasty(num_recipes: int = 50) -> List[Dict]:
    """
    Scrape from Tasty API via RapidAPI (500 requests/month free tier)
    Get key at: https://rapidapi.com/apidojo/api/tasty/
    """
    api_key = os.getenv('RAPIDAPI_KEY')

    if not api_key:
        print("⚠️ RAPIDAPI_KEY not set. Skipping Tasty API.")
        return []

    print(f"\n🍽️ Scraping Tasty API (target: {num_recipes} recipes)...")
    recipes = []
    url = 'https://tasty.p.rapidapi.com/recipes/list'

    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'tasty.p.rapidapi.com'
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params={
                'from': 0,
                'size': min(num_recipes, 40)  # API limit
            },
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()

            for recipe in data.get('results', []):
                # Parse ingredients
                ingredients = []
                for section in recipe.get('sections', []):
                    for component in section.get('components', []):
                        raw_text = component.get('raw_text', '')
                        if raw_text:
                            ingredients.append(raw_text)

                # Parse instructions
                instructions = []
                for instruction in recipe.get('instructions', []):
                    display_text = instruction.get('display_text', '')
                    if display_text:
                        instructions.append(display_text)

                # Get nutrition info
                nutrition = recipe.get('nutrition', {})

                recipes.append({
                    'title': recipe.get('name'),
                    'ingredients': ingredients,
                    'instructions': instructions,
                    'source_url': recipe.get('original_video_url') or f"https://tasty.co/recipe/{recipe.get('slug', '')}",
                    'source_name': 'Tasty',
                    'prep_time': recipe.get('prep_time_minutes'),
                    'cook_time': recipe.get('cook_time_minutes'),
                    'servings': recipe.get('num_servings'),
                    'image_url': recipe.get('thumbnail_url'),
                    'diet_tags': [tag.get('name') for tag in recipe.get('tags', [])],
                    'facts': {
                        'calories': nutrition.get('calories'),
                        'protein': nutrition.get('protein'),
                        'carbohydrates': nutrition.get('carbohydrates'),
                        'fat': nutrition.get('fat'),
                        'fiber': nutrition.get('fiber'),
                        'sugar': nutrition.get('sugar')
                    }
                })

            print(f"✅ Scraped {len(recipes)} recipes from Tasty")

        elif response.status_code == 429:
            print("⚠️ Tasty API quota exceeded (500 calls/month limit)")
        else:
            print(f"❌ Tasty API failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Tasty API error: {e}")

    return recipes

def scrape_spoonacular(num_recipes: int = 50) -> List[Dict]:
    """
    Scrape from Spoonacular API (150 free calls/day)
    Get key at: https://spoonacular.com/food-api
    """
    api_key = os.getenv('SPOONACULAR_API_KEY')

    if not api_key:
        print("⚠️ SPOONACULAR_API_KEY not set. Skipping Spoonacular.")
        return []

    print(f"\n🥘 Scraping Spoonacular (target: {num_recipes} recipes)...")
    recipes = []
    url = 'https://api.spoonacular.com/recipes/random'

    try:
        # Get random recipes in bulk (more efficient than individual calls)
        response = requests.get(
            url,
            params={
                'apiKey': api_key,
                'number': min(num_recipes, 100)  # Max 100 per call
            },
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()

            for recipe in data.get('recipes', []):
                # Parse ingredients
                ingredients = [
                    ing.get('original', '')
                    for ing in recipe.get('extendedIngredients', [])
                ]

                # Parse instructions
                instructions_data = recipe.get('analyzedInstructions', [])
                instructions = []

                if instructions_data:
                    for instruction_set in instructions_data:
                        for step in instruction_set.get('steps', []):
                            instructions.append(step.get('step', ''))
                elif recipe.get('instructions'):
                    # Fallback to text instructions
                    instructions = [
                        s.strip()
                        for s in recipe['instructions'].split('.')
                        if s.strip()
                    ]

                # Get nutrition info
                nutrition = recipe.get('nutrition', {})
                nutrients = nutrition.get('nutrients', [])

                calories = next(
                    (n['amount'] for n in nutrients if n['name'] == 'Calories'),
                    None
                )
                protein = next(
                    (n['amount'] for n in nutrients if n['name'] == 'Protein'),
                    None
                )
                carbs = next(
                    (n['amount'] for n in nutrients if n['name'] == 'Carbohydrates'),
                    None
                )

                recipes.append({
                    'title': recipe.get('title'),
                    'ingredients': ingredients,
                    'instructions': instructions,
                    'source_url': recipe.get('sourceUrl'),
                    'source_name': 'Spoonacular',
                    'prep_time': recipe.get('preparationMinutes'),
                    'cook_time': recipe.get('cookingMinutes'),
                    'servings': recipe.get('servings'),
                    'image_url': recipe.get('image'),
                    'cuisine': recipe.get('cuisines', [''])[0] if recipe.get('cuisines') else None,
                    'diet_tags': recipe.get('diets', []),
                    'facts': {
                        'calories': calories,
                        'protein': protein,
                        'carbohydrates': carbs,
                        'ready_in_minutes': recipe.get('readyInMinutes')
                    }
                })

            print(f"✅ Scraped {len(recipes)} recipes from Spoonacular")

        elif response.status_code == 402:
            print("⚠️ Spoonacular API quota exceeded (150 calls/day limit)")
        else:
            print(f"❌ Spoonacular API failed: {response.status_code} - {response.text[:200]}")

    except Exception as e:
        print(f"❌ Spoonacular error: {e}")

    return recipes

def insert_recipes(recipes: List[Dict]) -> tuple:
    """Insert recipes into Supabase PostgreSQL"""
    if not recipes:
        return 0, 0

    print(f"\n💾 Inserting {len(recipes)} recipes into database...")

    conn = connect_db()
    cursor = conn.cursor()

    inserted = 0
    duplicates = 0

    for recipe in recipes:
        try:
            # Check if recipe already exists (by title + source)
            cursor.execute(
                "SELECT id FROM recipes WHERE title = %s AND source_name = %s",
                (recipe['title'], recipe['source_name'])
            )

            if cursor.fetchone():
                duplicates += 1
                continue

            # Insert new recipe
            cursor.execute("""
                INSERT INTO recipes (
                    title, ingredients, instructions, source_url, source_name,
                    prep_time, cook_time, servings, image_url, cuisine, diet_tags, facts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                recipe['title'],
                Json(recipe['ingredients']),
                Json(recipe['instructions']),
                recipe.get('source_url'),
                recipe['source_name'],
                recipe.get('prep_time'),
                recipe.get('cook_time'),
                recipe.get('servings'),
                recipe.get('image_url'),
                recipe.get('cuisine'),
                recipe.get('diet_tags', []),
                Json(recipe.get('facts', {}))
            ))

            inserted += 1

        except Exception as e:
            print(f"❌ Failed to insert '{recipe.get('title', 'Unknown')}': {e}")
            continue

    conn.commit()
    cursor.close()
    conn.close()

    return inserted, duplicates

def get_database_stats():
    """Get current database statistics"""
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM recipes")
        total_recipes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM recipe_embeddings")
        total_embeddings = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return total_recipes, total_embeddings
    except Exception as e:
        print(f"⚠️ Could not get database stats: {e}")
        return None, None

def main():
    print("=" * 70)
    print("🚀 CULINARA AI - DAILY RECIPE SCRAPER")
    print("=" * 70)
    print(f"📅 Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    # Get current stats
    total_before, embeddings_before = get_database_stats()
    if total_before is not None:
        print(f"📊 Current database: {total_before} recipes, {embeddings_before} embeddings")

    all_recipes = []

    # Scrape from multiple free sources
    # TheMealDB: Free, unlimited
    all_recipes.extend(scrape_themealdb(num_recipes=1000))

    # Edamam: 5,000 calls/month free tier (optional)
    all_recipes.extend(scrape_edamam(num_recipes=500))

    # Recipe Puppy: Completely free, no API key needed
    all_recipes.extend(scrape_recipepuppy(num_recipes=200))

    # Tasty API: 500 requests/month free tier (optional)
    all_recipes.extend(scrape_tasty(num_recipes=50))

    # Spoonacular: 150 calls/day free tier (optional)
    all_recipes.extend(scrape_spoonacular(num_recipes=100))

    # Insert into database
    if all_recipes:
        inserted, duplicates = insert_recipes(all_recipes)

        print("\n" + "=" * 70)
        print("📊 SCRAPING SUMMARY")
        print("=" * 70)
        print(f"✅ Total scraped: {len(all_recipes)} recipes")
        print(f"✅ Newly inserted: {inserted} recipes")
        print(f"⏭️  Duplicates skipped: {duplicates} recipes")

        # Get updated stats
        total_after, embeddings_after = get_database_stats()
        if total_after is not None:
            print(f"📊 Database now has: {total_after} recipes, {embeddings_after} embeddings")

        print("=" * 70)
    else:
        print("\n⚠️ No recipes scraped from any source")

if __name__ == "__main__":
    main()
