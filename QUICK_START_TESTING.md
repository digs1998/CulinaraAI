# Quick Start: Testing CulinaraAI with Supabase

**Time required:** 30-40 minutes

---

## 🚀 Step-by-Step Testing Guide

### Step 1: Set Up Supabase (10 min)

**1.1 Create Supabase Project:**
```bash
# Go to: https://supabase.com/dashboard
# Click: "New Project"
# Fill in:
#   - Name: culinara-ai-test
#   - Database Password: [choose a strong password - SAVE IT!]
#   - Region: [choose closest to you]
# Click: "Create new project"
# Wait: ~2 minutes for initialization
```

**1.2 Get Your Credentials:**

Once your project is ready:

```bash
# In Supabase Dashboard:

# 1. Get Project URL
#    Settings → API → Project URL
#    Copy: https://xxxxx.supabase.co

# 2. Get Anon/Public Key
#    Settings → API → Project API keys → anon public
#    Copy: eyJhbGci...

# 3. Get Database Connection String
#    Settings → Database → Connection string → URI
#    Copy: postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
#    IMPORTANT: Replace [YOUR-PASSWORD] with your actual database password!
```

**1.3 Fill in `.env.test`:**

```bash
# Open the file
nano .env.test  # or use your preferred editor

# Fill in these values:
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
SUPABASE_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres
GEMINI_API_KEY=your-gemini-key

# Save and exit (Ctrl+X, then Y, then Enter in nano)
```

---

### Step 2: Run Database Migration (2 min)

**2.1 Go to Supabase SQL Editor:**
```bash
# In Supabase Dashboard:
# Click: "SQL Editor" (left sidebar)
# Click: "New Query"
```

**2.2 Copy Migration SQL:**
```bash
# In your terminal, display the migration SQL:
cat supabase/migrations/001_initial_schema.sql

# Select all and copy
```

**2.3 Run Migration:**
```bash
# In Supabase SQL Editor:
# 1. Paste the SQL
# 2. Click "Run" (or Ctrl+Enter)
# 3. You should see: "Success. No rows returned"
```

**2.4 Verify Migration:**
```sql
-- Run this query to verify tables were created:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('recipes', 'recipe_embeddings');

-- Should return 2 rows
```

---

### Step 3: Run Automated Tests (20-30 min)

Now that Supabase is set up, run the automated test suite:

```bash
# Load environment variables
source .env.test

# Run all tests
./run_tests.sh
```

**What the test script does:**
1. ✅ Installs dependencies
2. ✅ Tests Supabase connection
3. ✅ Verifies database schema
4. ✅ Runs recipe scraper (~50 recipes)
5. ✅ Generates embeddings
6. ✅ Tests backend startup
7. ✅ Tests recipe search API
8. ✅ Tests backward compatibility

**Expected output:**
```
==========================================
✅ ALL TESTS PASSED!
==========================================

📊 Summary:
  ✅ Supabase connection working
  ✅ Database schema migrated
  ✅ Recipe scraper functional
  ✅ Embedding generation working
  ✅ Backend starts in Supabase mode
  ✅ Recipe search API functional
  ✅ Backward compatibility verified

🚀 Your CulinaraAI backend is ready for deployment!
```

---

## 🐛 Troubleshooting

### Error: "connection refused"

**Problem:** Can't connect to Supabase

**Solutions:**
1. Check SUPABASE_URL format: `https://xxx.supabase.co` (must start with https://)
2. Verify project is fully initialized (go to Supabase dashboard, should show green status)
3. Try pinging: `curl https://your-project.supabase.co`

---

### Error: "relation 'recipes' does not exist"

**Problem:** Migration SQL not run

**Solution:**
1. Go to Supabase → SQL Editor
2. Run the migration SQL from `supabase/migrations/001_initial_schema.sql`
3. Verify with: `SELECT * FROM recipes LIMIT 1;`

---

### Error: "type 'vector' does not exist"

**Problem:** pgvector extension not enabled

**Solution:**
```sql
-- Run this in Supabase SQL Editor:
CREATE EXTENSION IF NOT EXISTS vector;

-- Then re-run the migration SQL
```

---

### Error: "API quota exceeded" (Gemini)

**Problem:** Hit Gemini API free tier limit

**Solution:**
1. Free tier: 1,500 requests/day
2. Wait 24 hours, or
3. Reduce recipe count in scraper:
   ```bash
   # Edit scripts/scrape_recipes.py
   # Change: scrape_themealdb(num_recipes=50)
   # To:     scrape_themealdb(num_recipes=10)
   ```

---

### Error: Backend fails to start

**Solutions:**
1. Check logs: `cat /tmp/backend_test.log`
2. Verify all environment variables are set: `env | grep SUPABASE`
3. Try starting backend manually:
   ```bash
   cd backend
   python3 main.py
   # Check output for specific error
   ```

---

## 📊 Verify Everything Works

After tests pass, do a manual verification:

**1. Check Supabase Dashboard:**
```bash
# Go to: Table Editor → recipes
# You should see ~50+ recipes
```

**2. Check Recipe Count:**
```sql
-- In SQL Editor:
SELECT COUNT(*) FROM recipes;
SELECT COUNT(*) FROM recipe_embeddings;

-- Both should return the same number (e.g., 50)
```

**3. Test Search Manually:**
```bash
# Start backend
cd backend
python3 main.py

# In another terminal:
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pasta recipes"}' | jq

# Should return JSON with recipes array
```

---

## ✅ Success Checklist

- [ ] Supabase project created
- [ ] `.env.test` filled with credentials
- [ ] Migration SQL run successfully
- [ ] `./run_tests.sh` completed with all tests passing
- [ ] Can see recipes in Supabase Table Editor
- [ ] Backend starts showing "Using Supabase PostgreSQL + pgvector"
- [ ] API returns recipes when searched

---

## 🚀 Ready for Production?

Once all tests pass:

**1. Deploy to Railway:**
```bash
# Add these environment variables in Railway:
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
GEMINI_API_KEY=your-key

# Push code (Railway auto-deploys)
git push
```

**2. Verify Production Deployment:**
```bash
# Check Railway logs should show:
# "Using Supabase PostgreSQL + pgvector"
# "Supabase has X recipes, X embeddings"
```

**3. Test Production API:**
```bash
curl -X POST https://your-app.up.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "healthy pasta"}' | jq
```

**4. Set Up Daily Scraping:**
```bash
# GitHub → Settings → Secrets
# Add the same Supabase credentials
# GitHub Actions will run daily at 2 AM UTC
```

---

## 📞 Get Help

**If tests fail:**
1. Check `TESTING_CHECKLIST.md` for detailed troubleshooting
2. Review error logs in `/tmp/backend_test.log`
3. Try individual tests one by one
4. Check Supabase dashboard for connection status

**If everything works:**
1. Commit your changes
2. Deploy to Railway
3. Set up GitHub Actions
4. Start growing your user base!

---

**Estimated time breakdown:**
- Supabase setup: 10 min
- Migration SQL: 2 min
- Running tests: 20-30 min
- Troubleshooting (if needed): 10-20 min

**Total: 30-60 minutes** for complete testing and validation
