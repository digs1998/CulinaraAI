# 🚀 Fully Automated CulinaraAI Setup

**Time required:** 5 minutes of your time + 30 minutes automated

This is the **easiest way** to set up CulinaraAI with Supabase.

---

## 📋 What You Need

1. **Supabase account** (free): https://supabase.com/dashboard
2. **Gemini API key** (free): https://aistudio.google.com/app/apikey
3. **Optional - Spoonacular API key** (free): https://spoonacular.com/food-api

---

## ⚡ Quick Setup (5 minutes)

### Step 1: Create Supabase Project (2 min)

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in:
   - Name: `culinara-ai`
   - Database Password: Choose strong password (SAVE IT!)
   - Region: Select closest to you
4. Click **"Create new project"**
5. Wait ~2 minutes for initialization

### Step 2: Get Credentials (3 min)

Once your project is ready:

**A. Get Project URL:**
```
Settings → API → Project URL
Copy: https://xxxxxxxxxxxxx.supabase.co
```

**B. Get Anon Key:**
```
Settings → API → Project API keys → anon public
Copy: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**C. Get Database URL:**
```
Settings → Database → Connection string → URI
Copy: postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres

IMPORTANT: Replace [YOUR-PASSWORD] with your actual database password!
```

### Step 3: Fill in .env.test (1 min)

```bash
# Open the file
nano .env.test

# Fill in these values:
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres
GEMINI_API_KEY=your-gemini-api-key
SPOONACULAR_API_KEY=your-spoonacular-key  # Optional

# Save and exit (Ctrl+X, Y, Enter)
```

---

## 🎯 Run Everything Automatically

Now just run this **one command**:

```bash
source .env.test && ./run_tests.sh
```

**That's it!** The script will automatically:

1. ✅ Install all dependencies
2. ✅ **Create database tables in Supabase** (automated!)
3. ✅ Test Supabase connection
4. ✅ Verify database schema
5. ✅ Scrape ~50 recipes from free APIs
6. ✅ Generate embeddings for all recipes
7. ✅ Test backend startup
8. ✅ Test recipe search API
9. ✅ Test backward compatibility

**Total time:** 30-40 minutes (automated - you can walk away!)

---

## 📊 What Happens During the Run

```
Running automated setup...

[1/9] Installing dependencies... ✅ (2 min)
[2/9] Creating database tables... ✅ (10 sec)
      → Connects to Supabase
      → Creates recipes table
      → Creates recipe_embeddings table
      → Creates search functions
      → Enables pgvector extension

[3/9] Testing connection... ✅ (5 sec)
[4/9] Verifying schema... ✅ (5 sec)
[5/9] Scraping recipes... ✅ (5 min)
      → TheMealDB: 50 recipes
      → Spoonacular: 40 recipes

[6/9] Generating embeddings... ✅ (10 min)
      → Using Gemini API
      → 90 embeddings created

[7/9] Testing backend... ✅ (10 sec)
[8/9] Testing API... ✅ (10 sec)
[9/9] Testing fallback... ✅ (10 sec)

========================================
✅ ALL TESTS PASSED!
========================================
```

---

## ✅ Expected Output

When everything works, you'll see:

```
========================================
✅ ALL TESTS PASSED!
========================================

📊 Summary:
  ✅ Supabase connection working
  ✅ Database schema migrated
  ✅ Recipe scraper functional
  ✅ Embedding generation working
  ✅ Backend starts in Supabase mode
  ✅ Recipe search API functional
  ✅ Backward compatibility verified

🚀 Your CulinaraAI backend is ready for deployment!

Next steps:
  1. Review test logs above for any warnings
  2. Deploy to Railway with Supabase credentials
  3. Set up GitHub Actions for daily scraping
```

---

## 🐛 Troubleshooting

### Error: "SUPABASE_DATABASE_URL not set"

**Fix:**
```bash
# Make sure you ran:
source .env.test

# Or export manually:
export $(cat .env.test | grep -v '^#' | xargs)
```

---

### Error: "Connection refused"

**Fix:**
1. Check SUPABASE_URL format: `https://xxx.supabase.co`
2. Check SUPABASE_DATABASE_URL has your actual password
3. Verify Supabase project is running (green status in dashboard)

---

### Error: "password authentication failed"

**Fix:**
```bash
# In .env.test, make sure you replaced [YOUR-PASSWORD]:
# WRONG: postgresql://postgres:[YOUR-PASSWORD]@db...
# RIGHT: postgresql://postgres:MyActualPassword123@db...
```

---

### Error: "quota exceeded" (Gemini)

**Fix:**
Free tier: 1,500 requests/day. Either:
- Wait 24 hours, or
- Reduce recipe count in `scripts/scrape_recipes.py`:
  ```python
  scrape_themealdb(num_recipes=10)  # Changed from 50
  ```

---

## 🎉 What You Get After Setup

**Database:**
- ✅ ~90 recipes in Supabase
- ✅ ~90 embeddings ready for search
- ✅ All tables and indexes created
- ✅ Search functions ready

**Backend:**
- ✅ Connects to Supabase automatically
- ✅ Recipe search works
- ✅ API endpoints functional
- ✅ Ready for deployment

**Automation:**
- ✅ GitHub Actions ready (daily scraping)
- ✅ No re-ingestion on deployment
- ✅ Data persists forever

---

## 🚀 Deploy to Production

Once all tests pass:

**1. Add env vars to Railway:**
```bash
# In Railway dashboard → Your service → Variables:
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
GEMINI_API_KEY=your-key
```

**2. Push code:**
```bash
git push
# Railway auto-deploys
```

**3. Verify deployment:**
```bash
# Check Railway logs should show:
# "Using Supabase PostgreSQL + pgvector"
# "Supabase has 90 recipes, 90 embeddings"
```

**4. Test production API:**
```bash
curl -X POST https://your-app.up.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pasta recipes"}' | jq
```

**Done!** Your app is live with:
- ✅ <1 minute deployments (no re-ingestion!)
- ✅ Persistent recipe storage
- ✅ Automated daily scraping
- ✅ $0-5/month cost

---

## 🔁 Daily Automated Scraping

GitHub Actions will run daily at 2 AM UTC to scrape new recipes.

**To enable:**

1. Go to GitHub → Settings → Secrets → Actions
2. Add these secrets:
   - `SUPABASE_DATABASE_URL`
   - `GEMINI_API_KEY`
   - `SPOONACULAR_API_KEY` (optional)

**That's it!** New recipes added daily automatically.

---

## 📞 Need Help?

**If setup fails:**
1. Check error message carefully
2. Verify all credentials in `.env.test`
3. Try running `python3 migrate_supabase.py` manually
4. Check troubleshooting section above

**If everything works:**
Congrats! You're ready to deploy to production 🎉

---

## 📚 What We Automated

**Previously (manual):**
- [ ] Open Supabase SQL Editor
- [ ] Copy 265 lines of SQL
- [ ] Paste and run manually
- [ ] Verify tables created
- [ ] Check for errors

**Now (automated):**
```bash
source .env.test && ./run_tests.sh
```

**One command does everything!** ✨

---

**Estimated times:**
- Your setup work: **5 minutes**
- Automated tests: **30-40 minutes**
- **Total:** ~40 minutes, mostly hands-off

**Compare to manual setup:** 60+ minutes of active work

**Time saved:** 50% reduction + way less error-prone!
