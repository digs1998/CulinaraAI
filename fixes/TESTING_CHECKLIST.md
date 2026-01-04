# Testing Checklist for Supabase Integration

## ⚠️ IMPORTANT: Code Was NOT Tested Locally

**Status:** Code has been syntactically validated but **NOT runtime tested** with actual Supabase connection.

**Validation Done:**
- ✅ Python syntax check (compiles without errors)
- ✅ Import structure verified
- ✅ Core logic tested (JSON parsing, embedding format)
- ✅ Method signatures match between engines

**Not Validated:**
- ❌ Actual Supabase connection
- ❌ pgvector search functionality
- ❌ End-to-end recipe search
- ❌ Embedding generation with real data

---

## 🧪 REQUIRED TESTS BEFORE PRODUCTION

### Test 1: Supabase Connection (5 min)

```bash
# Set environment variables
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="your-anon-key"
export GEMINI_API_KEY="your-key"

# Test connection
python3 << 'EOF'
from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

try:
    supabase = create_client(url, key)
    print("✅ Supabase connection successful!")

    # Test database query
    result = supabase.rpc('get_database_stats').execute()
    print(f"✅ Database stats: {result.data}")

except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
EOF
```

**Expected:** Connection succeeds, stats returned

---

### Test 2: Recipe Scraper (10 min)

```bash
cd /home/user/CulinaraAI

# Run scraper to add test recipes
python scripts/scrape_recipes.py

# Expected output:
# ✅ Scraped 50 recipes from TheMealDB
# ✅ Scraped 40 recipes from Spoonacular
# ✅ Newly inserted: 90 recipes
```

**Expected:** At least 50+ recipes inserted into Supabase

---

### Test 3: Embedding Generation (10 min)

```bash
# Generate embeddings for scraped recipes
python scripts/generate_embeddings.py

# Expected output:
# ✅ Successfully generated: 90 embeddings
```

**Expected:** All recipes get embeddings

---

### Test 4: Backend Startup with Supabase (5 min)

```bash
cd /home/user/CulinaraAI/backend

# Install dependencies first
pip install -r requirements.txt

# Start backend
python main.py

# Expected in logs:
# 📊 Using Supabase PostgreSQL + pgvector
# ✅ Supabase RAG Engine initialized
# 📊 Supabase has X recipes, X embeddings
# ✅ RAG Engine ready with Supabase
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Expected:** Backend starts without errors, shows Supabase mode

---

### Test 5: Recipe Search API (5 min)

```bash
# Test search endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "healthy pasta recipes",
    "preferences": {
      "diets": [],
      "skill": "beginner",
      "servings": 2,
      "goal": "healthy"
    }
  }' | jq

# Expected response:
# {
#   "response": "I found X recipes...",
#   "recipes": [
#     {
#       "title": "...",
#       "ingredients": [...],
#       "instructions": [...],
#       "score": 0.85
#     }
#   ],
#   "facts": [...]
# }
```

**Expected:** Recipes returned with scores > 0

---

### Test 6: Backward Compatibility (5 min)

```bash
# Remove Supabase env vars to test ChromaDB fallback
unset SUPABASE_URL
unset SUPABASE_KEY

# Restart backend
python main.py

# Expected in logs:
# 📊 Using ChromaDB (legacy mode - consider migrating to Supabase)
# 📁 Found ChromaDB at: ...
# ✅ RAG Engine ready with ChromaDB
```

**Expected:** Falls back to ChromaDB without errors

---

## 🐛 KNOWN POTENTIAL ISSUES

### Issue 1: JSONB Data Type Handling

**Location:** `backend/rag_engine_supabase.py:104-105`

**Code:**
```python
"ingredients": row['ingredients'] if isinstance(row['ingredients'], list) else json.loads(row['ingredients']),
```

**Potential Bug:** If Supabase returns JSONB as dict instead of list, this could fail.

**Fix if needed:**
```python
def safe_json_parse(value):
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except:
        return []

"ingredients": safe_json_parse(row['ingredients']),
```

---

### Issue 2: pgvector Extension Not Enabled

**Symptom:** Error: `type "vector" does not exist`

**Fix:** Run this in Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

### Issue 3: RPC Function Not Found

**Symptom:** Error: `function search_recipes does not exist`

**Fix:** Make sure you ran the full migration SQL from `supabase/migrations/001_initial_schema.sql`

---

### Issue 4: Embedding Dimension Mismatch

**Symptom:** Error: `dimension mismatch: expected 768, got X`

**Cause:** Using wrong Gemini embedding model

**Fix:** Ensure using `models/text-embedding-004` (768 dimensions)

---

## 🔍 DEBUGGING CHECKLIST

If backend fails to start:

- [ ] Check SUPABASE_URL format: `https://xxx.supabase.co`
- [ ] Check SUPABASE_KEY is the "anon public" key (not service role)
- [ ] Verify pgvector extension enabled: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- [ ] Verify tables exist: `SELECT * FROM recipes LIMIT 1;`
- [ ] Check Railway logs for specific error messages
- [ ] Try fallback to ChromaDB (remove SUPABASE_URL)

If search returns no results:

- [ ] Check recipes exist: `SELECT COUNT(*) FROM recipes;`
- [ ] Check embeddings exist: `SELECT COUNT(*) FROM recipe_embeddings;`
- [ ] Verify search function works: Run SQL `SELECT * FROM search_recipes(...);`
- [ ] Check similarity threshold (try lowering min_score to 0.1)

---

## 📊 VALIDATION CHECKLIST

Before deploying to production:

- [ ] **Test 1:** Supabase connection works
- [ ] **Test 2:** Recipe scraper adds recipes successfully
- [ ] **Test 3:** Embedding generation completes without errors
- [ ] **Test 4:** Backend starts in Supabase mode
- [ ] **Test 5:** Search API returns relevant results
- [ ] **Test 6:** Backward compatibility with ChromaDB verified
- [ ] **Test 7:** Deployment time < 1 minute (no re-ingestion)
- [ ] **Test 8:** Data persists after Railway redeploy

---

## 🚀 RECOMMENDED TESTING ORDER

1. **Local Testing (30 min)**
   - Run Tests 1-6 locally
   - Fix any issues found
   - Commit fixes

2. **Staging Deployment (15 min)**
   - Deploy to staging Railway environment
   - Test with small dataset
   - Verify logs

3. **Production Deployment (5 min)**
   - Update Railway env vars
   - Deploy to production
   - Monitor logs
   - Test search functionality

---

## 💡 TESTING TIPS

**Use Supabase SQL Editor for debugging:**
```sql
-- Check recipe count
SELECT COUNT(*) FROM recipes;

-- Check embedding count
SELECT COUNT(*) FROM recipe_embeddings;

-- Test search function manually
SELECT title, similarity
FROM search_recipes(
    (SELECT embedding FROM recipe_embeddings LIMIT 1),
    0.3,
    5
);

-- Check database stats
SELECT * FROM get_database_stats();
```

**Check Railway logs for errors:**
```bash
# In Railway dashboard
# Click on your service → Logs
# Look for:
# ✅ "Using Supabase PostgreSQL + pgvector"
# ✅ "Supabase has X recipes"
# ❌ Any error messages
```

---

## ⚠️ DISCLAIMER

**This code was written based on:**
- Supabase Python client documentation
- pgvector extension specs
- Google Gemini API docs
- Similar production systems

**It has NOT been:**
- Runtime tested with actual Supabase
- Load tested with multiple users
- Tested with large datasets (10K+ recipes)

**Recommendation:**
- Run all tests above before production deployment
- Start with staging environment
- Monitor logs closely on first deploy
- Have rollback plan ready (remove SUPABASE_URL to use ChromaDB)

---

## 🛟 ROLLBACK PLAN

If Supabase integration fails in production:

1. **Immediate rollback:**
   ```bash
   # In Railway → Environment Variables
   # Remove: SUPABASE_URL
   # Remove: SUPABASE_KEY
   # Click "Redeploy"
   ```

2. **Verify fallback:**
   ```bash
   # Check logs show:
   # "Using ChromaDB (legacy mode)"
   ```

3. **Fix issues locally**, then retry Supabase migration

---

**Bottom line:** The code is **syntactically correct** and **logically sound**, but needs **integration testing** before production use.

**Estimated testing time:** 40-60 minutes for all tests
**Risk level:** Medium (new integration, untested)
**Mitigation:** Backward compatibility ensures safe rollback
