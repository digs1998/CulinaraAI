#!/usr/bin/env python3
"""
Daily recipe scraper using FREE APIs (no paywalls).
Stores recipes in Supabase PostgreSQL.

Free APIs used:
- TheMealDB: Unlimited, completely free
- Spoonacular: 150 calls/day free tier
- Edamam: 5,000 calls/month free tier (optional)
"""
import os
import sys
import requests
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from typing import List, Dict
import time

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
    import argparse

    parser = argparse.ArgumentParser(description='Scrape recipes from free APIs')
    parser.add_argument('--count', type=int, default=50, help='Number of recipes to scrape per source (default: 50)')
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 CULINARA AI - DAILY RECIPE SCRAPER")
    print("=" * 70)
    print(f"📅 Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Target: {args.count} recipes per source")
    print()

    # Get current stats
    total_before, embeddings_before = get_database_stats()
    if total_before is not None:
        print(f"📊 Current database: {total_before} recipes, {embeddings_before} embeddings")

    all_recipes = []

    # Scrape from multiple free sources
    # TheMealDB: Free, unlimited
    themealdb_count = min(args.count, 100)  # Cap at 100 to avoid excessive API calls
    all_recipes.extend(scrape_themealdb(num_recipes=themealdb_count))

    # Spoonacular: 150 calls/day free tier (optional)
    spoonacular_count = min(args.count, 40)  # Cap at 40 to stay within free tier
    all_recipes.extend(scrape_spoonacular(num_recipes=spoonacular_count))

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
