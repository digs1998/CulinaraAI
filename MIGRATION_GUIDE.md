# Migration Guide: ChromaDB → Supabase

> **⚠️ MIGRATION COMPLETE - ChromaDB REMOVED**
>
> As of the latest version, CulinaraAI uses **Supabase exclusively**. ChromaDB support has been removed.
>
> This document is kept for historical reference. For current setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md) or [README.md](README.md).

## Overview

This guide documents the migration of CulinaraAI from ChromaDB to Supabase.

**Migration Benefits:**
- ✅ No re-ingestion on deployment (20 min → <1 min)
- ✅ Data persists across Railway restarts
- ✅ Scales to millions of recipes
- ✅ Better performance with pgvector
- ✅ Built-in backup & replication

**Status:** Migration complete - Supabase is now the only supported database.

---

## Migration Options

### Option A: Fresh Start (Recommended - 30 minutes)

Start with Supabase from scratch, using automated scraping.

**Steps:**
1. Set up Supabase (see below)
2. Configure GitHub Actions
3. Let it scrape 90+ recipes/day automatically
4. Deploy backend with Supabase env vars

**Pros:** Clean, automated, no migration complexity
**Cons:** Starts with 0 recipes (but fills up fast)

### Option B: Migrate Existing ChromaDB Data (45 minutes)

Export your existing ChromaDB recipes and import to Supabase.

**Steps:**
1. Export recipes from ChromaDB to JSON
2. Set up Supabase
3. Import recipes using migration script
4. Generate embeddings
5. Deploy

**Pros:** Keep existing recipes
**Cons:** Requires manual export/import

---

## Option A: Fresh Start with Supabase

### Step 1: Create Supabase Project (5 min)

1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Fill in:
   - Name: `culinara-ai`
   - Database Password: (choose strong password - save it!)
   - Region: Choose closest to your users (e.g., US East for Railway)
4. Click "Create new project"
5. Wait ~2 minutes for provisioning

### Step 2: Run Database Migration (2 min)

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy the entire contents of `supabase/migrations/001_initial_schema.sql`
4. Paste into SQL Editor
5. Click **Run** (or press Ctrl+Enter)
6. You should see: **"Success. No rows returned"**

**Verify it worked:**
```sql
-- Run this to check tables were created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('recipes', 'recipe_embeddings');
```

Should return 2 rows.

### Step 3: Get Supabase Credentials (3 min)

1. **Database Connection String:**
   - Go to **Project Settings** (gear icon) → **Database**
   - Scroll to **Connection string** section
   - Select **URI** tab
   - Copy the connection string (starts with `postgresql://postgres:...`)
   - **Important:** Replace `[YOUR-PASSWORD]` with your actual database password
   - Save this as: `SUPABASE_DATABASE_URL`

2. **API Credentials:**
   - Go to **Project Settings** → **API**
   - Copy **Project URL** → Save as: `SUPABASE_URL`
   - Copy **anon public** key → Save as: `SUPABASE_KEY`

### Step 4: Configure GitHub Secrets (5 min)

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these secrets:

| Secret Name | Value | Where to Get |
|------------|-------|--------------|
| `SUPABASE_DATABASE_URL` | `postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres` | Supabase → Settings → Database → URI |
| `SUPABASE_URL` | `https://xxx.supabase.co` | Supabase → Settings → API → Project URL |
| `SUPABASE_KEY` | `eyJhbGc...` | Supabase → Settings → API → anon public |
| `GEMINI_API_KEY` | Your Gemini key | Already set (verify it's there) |
| `SPOONACULAR_API_KEY` | Get free key | https://spoonacular.com/food-api |

### Step 5: Test Scraper Locally (Optional - 10 min)

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables for local testing
export SUPABASE_DATABASE_URL="postgresql://postgres:your-password@db.xxx.supabase.co:5432/postgres"
export GEMINI_API_KEY="your-gemini-key"
export SPOONACULAR_API_KEY="your-spoonacular-key"  # Optional

# Test scraper (will add ~90 recipes)
python scripts/scrape_recipes.py

# Expected output:
# ✅ Scraped 50 recipes from TheMealDB
# ✅ Scraped 40 recipes from Spoonacular
# ✅ Newly inserted: 90 recipes

# Test embedding generator
python scripts/generate_embeddings.py

# Expected output:
# ✅ Successfully generated: 90 embeddings
```

### Step 6: Configure Railway (3 min)

1. Go to your Railway project dashboard
2. Click on your backend service
3. Go to **Variables** tab
4. Add these environment variables:

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
GEMINI_API_KEY=your-gemini-key
```

**Note:** Do NOT add `SUPABASE_DATABASE_URL` to Railway - only the backend scraper scripts need it.

### Step 7: Deploy Backend (2 min)

```bash
# Commit and push changes
git add .
git commit -m "Add Supabase support for persistent recipe storage"
git push

# Railway will auto-deploy
# This deployment should take < 1 minute (no ingestion!)
```

**Check logs in Railway:**
```
✅ Supabase RAG Engine initialized
📊 Supabase has 90 recipes, 90 embeddings
✅ RAG Engine ready with Supabase
```

### Step 8: Trigger Automated Scraping (3 min)

1. Go to GitHub → **Actions** tab
2. Click **Daily Recipe Scraper** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait 5-10 minutes
5. Check Supabase for new recipes

**To check in Supabase:**
```sql
SELECT COUNT(*) FROM recipes;
SELECT COUNT(*) FROM recipe_embeddings;
```

**Done!** Your backend now uses Supabase and scrapes recipes daily.

---

## Option B: Migrate Existing ChromaDB Data

### Step 1: Export ChromaDB Recipes to JSON

Create `export_chromadb.py` in backend folder:

```python
#!/usr/bin/env python3
import json
from pathlib import Path
from chromadb import PersistentClient

# Path to your ChromaDB
chroma_dir = Path(__file__).parent / "chroma_db"
chroma_client = PersistentClient(path=str(chroma_dir))
collection = chroma_client.get_collection("recipes")

# Get all recipes
results = collection.get(include=["metadatas", "documents"])

recipes = []
for i, metadata in enumerate(results['metadatas']):
    recipes.append({
        'id': results['ids'][i],
        'title': metadata.get('title'),
        'ingredients': metadata.get('ingredients', []),
        'instructions': metadata.get('instructions', []),
        'source_url': metadata.get('url'),
        'source_name': 'ChromaDB Migration',
        'facts': metadata.get('facts', {})
    })

# Export to JSON
output_file = 'chromadb_export.json'
with open(output_file, 'w') as f:
    json.dump(recipes, f, indent=2)

print(f"✅ Exported {len(recipes)} recipes to {output_file}")
```

Run it:
```bash
python backend/export_chromadb.py
```

### Step 2: Set Up Supabase

Follow **Option A, Steps 1-3** to create Supabase project and get credentials.

### Step 3: Import Recipes to Supabase

```bash
# Set environment variables
export SUPABASE_DATABASE_URL="your-connection-string"
export GEMINI_API_KEY="your-gemini-key"

# Import recipes
python scripts/import_recipes.py chromadb_export.json
```

Create `scripts/import_recipes.py`:

```python
#!/usr/bin/env python3
import sys
import json
import psycopg2
from psycopg2.extras import Json

# Connect to Supabase
conn = psycopg2.connect(sys.argv[1] if len(sys.argv) > 2 else os.getenv('SUPABASE_DATABASE_URL'))
cursor = conn.cursor()

# Load recipes
with open(sys.argv[1], 'r') as f:
    recipes = json.load(f)

# Insert each recipe
for recipe in recipes:
    cursor.execute("""
        INSERT INTO recipes (title, ingredients, instructions, source_url, source_name, facts)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (title, source_name) DO NOTHING
    """, (
        recipe['title'],
        Json(recipe['ingredients']),
        Json(recipe['instructions']),
        recipe.get('source_url'),
        recipe.get('source_name', 'ChromaDB Migration'),
        Json(recipe.get('facts', {}))
    ))

conn.commit()
print(f"✅ Imported {len(recipes)} recipes")
```

### Step 4: Generate Embeddings

```bash
python scripts/generate_embeddings.py
```

### Step 5: Deploy

Follow **Option A, Steps 6-7**.

---

## Verification Checklist

After migration, verify everything works:

- [ ] Supabase tables exist (`recipes`, `recipe_embeddings`)
- [ ] Recipes imported successfully
- [ ] Embeddings generated for all recipes
- [ ] Backend connects to Supabase (check Railway logs)
- [ ] Recipe search works in frontend
- [ ] Deployment time < 1 minute
- [ ] GitHub Actions runs successfully
- [ ] New recipes appear daily

---

## Testing the Migration

### Test 1: Check Supabase Connection

In Railway logs, you should see:
```
✅ Supabase RAG Engine initialized
📊 Supabase has XXX recipes, XXX embeddings
✅ RAG Engine ready with Supabase
```

### Test 2: Test Recipe Search

In your frontend, search for "pasta" and verify:
- Results appear
- Recipes have all fields (title, ingredients, instructions)
- Similarity scores are shown

### Test 3: Check Database Stats

Run this in Supabase SQL Editor:
```sql
SELECT * FROM get_database_stats();
```

Should return:
```
total_recipes | total_embeddings | recipes_pending_embedding | unique_sources | unique_cuisines
--------------|------------------|---------------------------|----------------|----------------
     300      |       300        |            0              |       5        |      15
```

---

## Rollback Plan (If Something Goes Wrong)

The backend is **backwards compatible**. If Supabase doesn't work:

1. **Remove Supabase env vars from Railway:**
   - Delete `SUPABASE_URL`
   - Delete `SUPABASE_KEY`

2. **Redeploy:**
   - Backend will automatically fall back to ChromaDB
   - You'll see in logs: "Using ChromaDB (legacy mode)"

3. **Everything still works** (but with re-ingestion issue)

---

## Post-Migration Cleanup

Once Supabase is working:

1. **Disable ChromaDB** (optional):
   ```bash
   # Remove ChromaDB data to save space
   rm -rf backend/chroma_db/
   ```

2. **Update documentation:**
   - Update README to mention Supabase
   - Archive old ChromaDB instructions

3. **Monitor costs:**
   - Check Supabase usage: Project Settings → Usage
   - Should stay within free tier (500MB) for months

---

## Troubleshooting

### Issue: "relation 'recipes' does not exist"

**Solution:** You didn't run the migration SQL. Go to Supabase SQL Editor and run `supabase/migrations/001_initial_schema.sql`.

### Issue: Backend still uses ChromaDB

**Solution:** Check Railway environment variables. `SUPABASE_URL` and `SUPABASE_KEY` must be set.

### Issue: Search returns no results

**Solution:**
1. Check if recipes exist: `SELECT COUNT(*) FROM recipes;`
2. Check if embeddings exist: `SELECT COUNT(*) FROM recipe_embeddings;`
3. If recipes exist but no embeddings, run `python scripts/generate_embeddings.py`

### Issue: "invalid input syntax for type vector"

**Solution:** Make sure you ran the migration SQL which includes `CREATE EXTENSION vector;`

### Issue: Deployment still takes 20 minutes

**Solution:**
1. Check Railway logs - is it still using ChromaDB?
2. Verify `SUPABASE_URL` and `SUPABASE_KEY` are set
3. Check for old ingestion scripts running on startup

---

## FAQ

**Q: Can I use both ChromaDB and Supabase?**
A: Yes! The backend automatically detects which one to use based on environment variables.

**Q: Will this break my existing users?**
A: No. The backend is backwards compatible. Users won't notice any change.

**Q: How much does Supabase cost?**
A: Free tier includes 500MB database + 2GB bandwidth. You'll stay within this for thousands of recipes.

**Q: What happens to my ChromaDB data?**
A: It stays in Railway (ephemeral). You can export it to Supabase using Option B, or let GitHub Actions populate Supabase with fresh recipes.

**Q: Can I switch back to ChromaDB?**
A: Yes! Just remove `SUPABASE_URL` and `SUPABASE_KEY` from Railway, and the backend will automatically fall back.

---

## Next Steps After Migration

1. **Enable daily scraping:**
   - GitHub Actions will run automatically at 2 AM UTC
   - You can also trigger manually anytime

2. **Monitor growth:**
   - Check Supabase dashboard weekly
   - Track recipe count: `SELECT COUNT(*) FROM recipes;`

3. **Optimize as needed:**
   - Add more recipe sources
   - Adjust scraping frequency
   - Add filters (cuisine, diet tags)

4. **Focus on growth:**
   - See `SAAS_ENHANCEMENT_PLAN.md` for marketing strategy

---

**Need help?** Check troubleshooting section or create an issue in the repo.

**Migration complete?** Mark as done in `IMPLEMENTATION_SUMMARY.md` checklist!
