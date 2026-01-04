# CulinaraAI Data Pipeline Architecture
## Airflow + PostgreSQL + Free Recipe Sources

---

## 🎯 YOUR CONCERNS ADDRESSED

### Problem 1: Paywall/Subscription Sites
**Current issue:** Web search hits sites like America's Test Kitchen, NYT Cooking (require subscription)

**Solution:** Target **free, open recipe sources only**

### Problem 2: Re-ingestion on Deployment
**Your solution:** ✅ Airflow DAG for async data collection + PostgreSQL storage

**This is the RIGHT approach!** Here's how to implement it:

---

## 🏗️ ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    AIRFLOW (Data Collection)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  DAG 1: Daily Recipe Scraper                         │   │
│  │  • Runs daily at 2 AM                                │   │
│  │  • Scrapes free recipe sites                         │   │
│  │  • Stores raw data in PostgreSQL                     │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │  DAG 2: Embedding Generator                          │   │
│  │  • Triggers after DAG 1                              │   │
│  │  • Generates embeddings for new recipes              │   │
│  │  • Updates vector database (Pinecone/Supabase)      │   │
│  └───────────────────┬──────────────────────────────────┘   │
└────────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                POSTGRESQL DATABASE                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  recipes                                              │   │
│  │  • id (UUID, primary key)                            │   │
│  │  • title (TEXT)                                      │   │
│  │  • ingredients (JSONB)                               │   │
│  │  • instructions (JSONB)                              │   │
│  │  • source_url (TEXT)                                 │   │
│  │  • facts (JSONB) - prep_time, cook_time, etc.       │   │
│  │  • embedding_status (ENUM: pending, completed)       │   │
│  │  • created_at, updated_at                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  recipe_embeddings (if using Postgres pgvector)      │   │
│  │  • recipe_id (UUID, foreign key)                     │   │
│  │  • embedding (VECTOR(768))                           │   │
│  │  • created_at                                        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                VECTOR DATABASE (Choose One)                  │
│                                                              │
│  Option A: Pinecone (Recommended - no re-deployment)        │
│  Option B: Supabase pgvector (All-in-one)                   │
│  Option C: Qdrant (Self-hosted if needed)                   │
└────────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│             BACKEND API (FastAPI - Railway)                  │
│  • Reads from PostgreSQL (recipe details)                   │
│  • Queries vector DB (semantic search)                      │
│  • NO re-ingestion on deployment                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 🆓 FREE RECIPE SOURCES (No Paywall)

### ✅ Best Free Sources

| Source | Recipes | API? | Scraping Difficulty | License |
|--------|---------|------|---------------------|---------|
| **Tasty (BuzzFeed)** | 10,000+ | ❌ No | Easy | Fair use |
| **BBC Good Food** | 15,000+ | ❌ No | Easy | Fair use |
| **AllRecipes** | 50,000+ | ❌ No | Medium | Fair use |
| **Food.com** | 500,000+ | ❌ No | Medium | Fair use |
| **Serious Eats** | 5,000+ | ❌ No | Medium | Fair use |
| **Recipe Puppy** | 1M+ | ✅ YES! | N/A (API) | Free API |
| **Edamam** | 2.3M+ | ✅ YES! | N/A (API) | 5K calls/month free |
| **Spoonacular** | 360,000+ | ✅ YES! | N/A (API) | 150 calls/day free |
| **TheMealDB** | 300+ | ✅ YES! | N/A (API) | Free |

### 🚀 RECOMMENDED STRATEGY

**Phase 1:** Use free APIs (fast, legal, no scraping complexity)
**Phase 2:** Scrape free sites (more recipes, but slower)

---

## 📋 IMPLEMENTATION PLAN

### **OPTION A: Airflow on Railway (Recommended)**

**Pros:**
- ✅ Same infrastructure (Railway)
- ✅ Built-in scheduling
- ✅ Web UI for monitoring
- ✅ Retry logic built-in

**Cons:**
- ❌ Needs separate container ($5-10/month)
- ❌ Requires PostgreSQL (Railway or Supabase)

### **OPTION B: GitHub Actions (FREE!)**

**Pros:**
- ✅ Completely FREE
- ✅ No infrastructure needed
- ✅ Easy to set up (30 min)
- ✅ Integrated with your repo

**Cons:**
- ❌ 2,000 minutes/month limit (but you only need ~10 min/day = 300/month)
- ❌ Less powerful than Airflow

**👉 I RECOMMEND GITHUB ACTIONS for your use case** - it's FREE and perfect for daily scraping.

---

## ✅ IMPLEMENTATION: GitHub Actions + Supabase

### Step 1: Set Up Supabase (FREE tier - 500MB database)

1. **Create Supabase project:** https://supabase.com
2. **Create tables:**

```sql
-- recipes table
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    ingredients JSONB NOT NULL DEFAULT '[]',
    instructions JSONB NOT NULL DEFAULT '[]',
    source_url TEXT,
    source_name TEXT,
    facts JSONB DEFAULT '{}',
    cuisine TEXT,
    diet_tags TEXT[], -- e.g., ['vegan', 'gluten-free']
    prep_time INTEGER, -- minutes
    cook_time INTEGER,
    servings INTEGER,
    calories INTEGER,
    image_url TEXT,
    embedding_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable pgvector extension (for embeddings in same DB)
CREATE EXTENSION IF NOT EXISTS vector;

-- recipe_embeddings table
CREATE TABLE recipe_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID REFERENCES recipes(id) ON DELETE CASCADE,
    embedding VECTOR(768), -- Gemini embedding dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_recipes_embedding_status ON recipes(embedding_status);
CREATE INDEX idx_recipes_created_at ON recipes(created_at DESC);
CREATE INDEX idx_recipe_embeddings_recipe_id ON recipe_embeddings(recipe_id);

-- pgvector HNSW index for fast similarity search
CREATE INDEX ON recipe_embeddings USING hnsw (embedding vector_cosine_ops);
```

3. **Get your connection string:**
   - Go to Project Settings → Database
   - Copy "Connection String" (Postgres format)
   - Add to GitHub Secrets as `SUPABASE_DATABASE_URL`

### Step 2: Create GitHub Actions Workflow

**File: `.github/workflows/daily_recipe_scraper.yml`**

```yaml
name: Daily Recipe Scraper

on:
  schedule:
    # Runs at 2 AM UTC every day
    - cron: '0 2 * * *'
  workflow_dispatch: # Allow manual trigger

jobs:
  scrape-and-embed:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install requests psycopg2-binary google-generativeai python-dotenv

      - name: Scrape recipes from APIs
        env:
          SUPABASE_DATABASE_URL: ${{ secrets.SUPABASE_DATABASE_URL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python scripts/scrape_recipes.py

      - name: Generate embeddings for new recipes
        env:
          SUPABASE_DATABASE_URL: ${{ secrets.SUPABASE_DATABASE_URL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python scripts/generate_embeddings.py

      - name: Send notification (optional)
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"Recipe scraper failed! Check GitHub Actions."}'
```

### Step 3: Create Scraper Script

**File: `scripts/scrape_recipes.py`**

```python
#!/usr/bin/env python3
"""
Daily recipe scraper using free APIs.
Stores recipes in Supabase PostgreSQL.
"""
import os
import requests
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from typing import List, Dict

# Free recipe APIs
RECIPE_APIS = {
    'edamam': {
        'url': 'https://api.edamam.com/api/recipes/v2',
        'app_id': os.getenv('EDAMAM_APP_ID'),  # Get free at https://developer.edamam.com/
        'app_key': os.getenv('EDAMAM_APP_KEY'),
        'limit_per_day': 5000  # Free tier
    },
    'spoonacular': {
        'url': 'https://api.spoonacular.com/recipes/random',
        'api_key': os.getenv('SPOONACULAR_API_KEY'),  # Get free at https://spoonacular.com/food-api
        'limit_per_day': 150  # Free tier
    },
    'themealdb': {
        'url': 'https://www.themealdb.com/api/json/v1/1/random.php',
        'free': True,
        'no_limit': True
    }
}

def connect_db():
    """Connect to Supabase PostgreSQL"""
    return psycopg2.connect(os.getenv('SUPABASE_DATABASE_URL'))

def scrape_spoonacular(num_recipes: int = 50) -> List[Dict]:
    """Scrape from Spoonacular API (150 free calls/day)"""
    api_key = RECIPE_APIS['spoonacular']['api_key']

    if not api_key:
        print("⚠️ Spoonacular API key not set. Skipping.")
        return []

    recipes = []

    # Get random recipes in bulk (more efficient)
    response = requests.get(
        RECIPE_APIS['spoonacular']['url'],
        params={
            'apiKey': api_key,
            'number': min(num_recipes, 100)  # Max 100 per call
        }
    )

    if response.status_code == 200:
        data = response.json()

        for recipe in data.get('recipes', []):
            recipes.append({
                'title': recipe.get('title'),
                'ingredients': [ing['original'] for ing in recipe.get('extendedIngredients', [])],
                'instructions': recipe.get('instructions', '').split('\n'),
                'source_url': recipe.get('sourceUrl'),
                'source_name': 'Spoonacular',
                'prep_time': recipe.get('preparationMinutes'),
                'cook_time': recipe.get('cookingMinutes'),
                'servings': recipe.get('servings'),
                'image_url': recipe.get('image'),
                'cuisine': recipe.get('cuisines', [''])[0] if recipe.get('cuisines') else None,
                'diet_tags': recipe.get('diets', []),
                'facts': {
                    'calories': recipe.get('nutrition', {}).get('nutrients', [{}])[0].get('amount') if recipe.get('nutrition') else None,
                    'protein': next((n['amount'] for n in recipe.get('nutrition', {}).get('nutrients', []) if n['name'] == 'Protein'), None),
                    'carbs': next((n['amount'] for n in recipe.get('nutrition', {}).get('nutrients', []) if n['name'] == 'Carbohydrates'), None),
                }
            })

        print(f"✅ Scraped {len(recipes)} recipes from Spoonacular")
    else:
        print(f"❌ Spoonacular API failed: {response.status_code}")

    return recipes

def scrape_themealdb(num_recipes: int = 100) -> List[Dict]:
    """Scrape from TheMealDB (completely free, unlimited)"""
    recipes = []

    for i in range(num_recipes):
        response = requests.get(RECIPE_APIS['themealdb']['url'])

        if response.status_code == 200:
            data = response.json()
            meal = data['meals'][0]

            # Extract ingredients (stored as strIngredient1, strIngredient2, etc.)
            ingredients = []
            for j in range(1, 21):  # Up to 20 ingredients
                ingredient = meal.get(f'strIngredient{j}')
                measure = meal.get(f'strMeasure{j}')
                if ingredient and ingredient.strip():
                    ingredients.append(f"{measure} {ingredient}".strip())

            recipes.append({
                'title': meal.get('strMeal'),
                'ingredients': ingredients,
                'instructions': meal.get('strInstructions', '').split('\n'),
                'source_url': meal.get('strSource'),
                'source_name': 'TheMealDB',
                'image_url': meal.get('strMealThumb'),
                'cuisine': meal.get('strArea'),
                'diet_tags': [meal.get('strCategory')] if meal.get('strCategory') else [],
                'facts': {}
            })

        if (i + 1) % 10 == 0:
            print(f"  Scraped {i + 1}/{num_recipes} recipes from TheMealDB...")

    print(f"✅ Scraped {len(recipes)} recipes from TheMealDB")
    return recipes

def insert_recipes(recipes: List[Dict]):
    """Insert recipes into Supabase PostgreSQL"""
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
            print(f"❌ Failed to insert {recipe['title']}: {e}")
            continue

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n📊 Results:")
    print(f"   ✅ Inserted: {inserted} new recipes")
    print(f"   ⏭️  Skipped: {duplicates} duplicates")

def main():
    print("🚀 Starting daily recipe scraper...")
    print(f"📅 Run time: {datetime.now()}")

    all_recipes = []

    # Scrape from multiple sources
    all_recipes.extend(scrape_themealdb(num_recipes=50))  # Free, unlimited
    all_recipes.extend(scrape_spoonacular(num_recipes=50))  # 150/day limit

    # Insert into database
    if all_recipes:
        insert_recipes(all_recipes)
        print(f"\n✅ Successfully scraped {len(all_recipes)} recipes total")
    else:
        print("⚠️ No recipes scraped")

if __name__ == "__main__":
    main()
```

### Step 4: Create Embedding Generator Script

**File: `scripts/generate_embeddings.py`**

```python
#!/usr/bin/env python3
"""
Generate embeddings for new recipes and store in Supabase pgvector.
"""
import os
import psycopg2
from psycopg2.extras import Json
import google.generativeai as genai
from typing import List, Tuple
import time

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def connect_db():
    return psycopg2.connect(os.getenv('SUPABASE_DATABASE_URL'))

def get_pending_recipes(limit: int = 100) -> List[Tuple]:
    """Get recipes that don't have embeddings yet"""
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.id, r.title, r.ingredients, r.instructions
        FROM recipes r
        LEFT JOIN recipe_embeddings e ON r.id = e.recipe_id
        WHERE e.id IS NULL
        LIMIT %s
    """, (limit,))

    recipes = cursor.fetchall()
    cursor.close()
    conn.close()

    return recipes

def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Gemini"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]

def create_recipe_text(title: str, ingredients: List[str], instructions: List[str]) -> str:
    """Create searchable text from recipe"""
    text = f"Recipe: {title}\n\n"
    text += "Ingredients:\n" + "\n".join([f"- {ing}" for ing in ingredients[:15]])
    text += "\n\nInstructions:\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(instructions[:10])])
    return text

def insert_embedding(recipe_id: str, embedding: List[float]):
    """Insert embedding into Supabase"""
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO recipe_embeddings (recipe_id, embedding)
        VALUES (%s, %s)
        ON CONFLICT (recipe_id) DO NOTHING
    """, (recipe_id, embedding))

    conn.commit()
    cursor.close()
    conn.close()

def main():
    print("⚡ Generating embeddings for new recipes...")

    # Get recipes without embeddings
    pending = get_pending_recipes(limit=200)  # Adjust based on API limits

    if not pending:
        print("✅ All recipes already have embeddings!")
        return

    print(f"📝 Found {len(pending)} recipes needing embeddings")

    successful = 0
    failed = 0

    for i, (recipe_id, title, ingredients, instructions) in enumerate(pending, 1):
        try:
            # Create searchable text
            recipe_text = create_recipe_text(title, ingredients, instructions)

            # Generate embedding
            embedding = generate_embedding(recipe_text)

            # Store in database
            insert_embedding(recipe_id, embedding)

            successful += 1

            if i % 10 == 0:
                print(f"  ✅ Processed {i}/{len(pending)} recipes...")

            # Rate limiting (Gemini free tier: 1500 requests/day)
            time.sleep(0.1)  # Small delay to avoid rate limits

        except Exception as e:
            print(f"❌ Failed for '{title}': {e}")
            failed += 1
            continue

    print(f"\n📊 Results:")
    print(f"   ✅ Success: {successful} embeddings")
    print(f"   ❌ Failed: {failed}")

if __name__ == "__main__":
    main()
```

### Step 5: Update Backend to Use Supabase

**File: `backend/main.py`** (replace ChromaDB with Supabase)

```python
import os
from supabase import create_client, Client
import numpy as np
import google.generativeai as genai

# Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def embed_query(query: str) -> List[float]:
    """Generate embedding for search query"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    return result["embedding"]

@app.post("/api/search")
def search_recipes(query: str, top_k: int = 5):
    """Search recipes using pgvector similarity"""

    # Generate query embedding
    query_embedding = embed_query(query)

    # Search using pgvector (cosine similarity)
    result = supabase.rpc('search_recipes', {
        'query_embedding': query_embedding,
        'match_threshold': 0.3,  # Minimum similarity
        'match_count': top_k
    }).execute()

    return {
        'success': True,
        'results': result.data
    }
```

**Create PostgreSQL function for vector search:**

```sql
-- In Supabase SQL Editor
CREATE OR REPLACE FUNCTION search_recipes(
    query_embedding VECTOR(768),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    ingredients JSONB,
    instructions JSONB,
    source_url TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.title,
        r.ingredients,
        r.instructions,
        r.source_url,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM recipes r
    JOIN recipe_embeddings e ON r.id = e.recipe_id
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## 💰 COST BREAKDOWN

### Free Tier (Your Current Scale)

| Service | Free Tier | Cost if Exceeded |
|---------|-----------|------------------|
| **Supabase** | 500MB DB, 2GB bandwidth | $25/month (Pro) |
| **GitHub Actions** | 2,000 min/month | $0.008/min |
| **Spoonacular API** | 150 calls/day | $60/month (Grow plan) |
| **TheMealDB API** | Unlimited | FREE forever |
| **Gemini API** | 1,500 calls/day | $0.00025/call |
| **Railway (Backend)** | $5 credit/month | $5-10/month |
| **Vercel (Frontend)** | 100GB bandwidth | $20/month (Pro) |

**Total cost at current scale: $0-10/month** ✅

### At 10,000 Users

| Service | Estimated Cost |
|---------|---------------|
| Supabase (2GB DB) | $25/month |
| Railway (backend) | $10-20/month |
| Vercel | $0 (within free tier) |
| Pinecone (if switching) | $70/month |

**Total: ~$35-50/month**

---

## 🚀 DEPLOYMENT STEPS

### Day 1: Set up infrastructure (2 hours)
```bash
# 1. Create Supabase project
# - Go to https://supabase.com/dashboard
# - Create new project
# - Run SQL migrations (tables + functions)

# 2. Get API keys
# - Spoonacular: https://spoonacular.com/food-api
# - Edamam: https://developer.edamam.com/

# 3. Add GitHub Secrets
# - SUPABASE_DATABASE_URL
# - SUPABASE_URL
# - SUPABASE_KEY
# - GEMINI_API_KEY
# - SPOONACULAR_API_KEY
# - EDAMAM_APP_ID
# - EDAMAM_APP_KEY

# 4. Create scripts directory
mkdir -p scripts
# Add scrape_recipes.py and generate_embeddings.py

# 5. Create GitHub Actions workflow
mkdir -p .github/workflows
# Add daily_recipe_scraper.yml

# 6. Test manually
python scripts/scrape_recipes.py
python scripts/generate_embeddings.py
```

### Day 2: Update backend (3 hours)
```bash
# 1. Update backend/main.py to use Supabase
# 2. Update backend/rag_engine.py
# 3. Test locally
# 4. Deploy to Railway
# 5. Verify no re-ingestion on deployment
```

### Day 3: Launch automation (1 hour)
```bash
# 1. Commit all changes
git add .
git commit -m "Add automated recipe scraping pipeline"
git push

# 2. Manually trigger GitHub Action to test
# - Go to Actions tab
# - Run "Daily Recipe Scraper"
# - Verify recipes are added to Supabase

# 3. Set up monitoring
# - Check Supabase logs
# - Set up alerts for failed runs
```

---

## 📊 EXPECTED RESULTS

### After 1 Week
- ✅ 350-700 recipes (50-100/day from free APIs)
- ✅ 0 deployment delays (no re-ingestion)
- ✅ $0 infrastructure cost (all free tiers)

### After 1 Month
- ✅ 1,500-3,000 recipes
- ✅ Diverse cuisine coverage
- ✅ Still within free tiers

### After 3 Months
- ✅ 5,000-10,000 recipes
- ✅ May need to upgrade Supabase ($25/month)
- ✅ Production-ready scale

---

## 🔄 AVOIDING PAYWALLS - ALTERNATIVE STRATEGIES

### Strategy 1: User-Generated Content
**Add recipe submission feature:**
- Users can submit their favorite recipes
- You manually approve (quality control)
- Growth = more recipes (network effect)

### Strategy 2: RSS Feed Scraping
**Many food blogs have free RSS feeds:**
```python
# Free recipe blogs with RSS
free_sources = [
    'https://minimalistbaker.com/feed/',
    'https://www.budgetbytes.com/feed/',
    'https://www.skinnytaste.com/feed/',
    'https://cookieandkate.com/feed/',
]
```

### Strategy 3: Partner with Food Bloggers
**Offer:**
- "We'll feature your recipes and link back to your blog"
- Win-win: they get traffic, you get content
- No legal issues (with permission)

---

## ✅ FINAL RECOMMENDATION

**Your architecture should be:**

```
FREE RECIPE APIs (Spoonacular, TheMealDB)
    ↓
GITHUB ACTIONS (daily scraping - FREE)
    ↓
SUPABASE POSTGRESQL + pgvector (500MB free)
    ↓
RAILWAY BACKEND (no re-ingestion!)
    ↓
VERCEL FRONTEND
```

**Benefits:**
- ✅ **$0 cost** at current scale
- ✅ **No re-ingestion** on deployment
- ✅ **No paywalls** - all legal, free APIs
- ✅ **Scales** to 10K users on free tiers
- ✅ **Simple** - no Airflow complexity needed

**Next Steps:**
1. Set up Supabase (30 min)
2. Create GitHub Actions workflow (1 hour)
3. Update backend to use Supabase (2 hours)
4. Deploy and test (1 hour)

**Total time: ~5 hours to solve both problems!**

Let me know if you want me to help implement any of these scripts.
