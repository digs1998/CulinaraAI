# Railway Deployment Guide - Fully Automated Setup

This guide shows you how to deploy CulinaraAI to Railway with **zero local setup**. Everything runs automatically in the cloud!

## 🎯 Architecture Overview

1. **Railway**: Hosts your backend, auto-creates database tables on first deployment
2. **Supabase**: Cloud PostgreSQL with pgvector for persistent recipe storage
3. **GitHub Actions**: Automatically scrapes recipes daily at 2 AM UTC

## ✅ One-Time Setup (5 minutes)

### Step 1: Set Railway Environment Variables

In your Railway project dashboard, add these environment variables:

```bash
# Supabase credentials (from your Supabase dashboard)
SUPABASE_URL=https://wcgobskmkjbclhkiqsyt.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_DATABASE_URL=postgresql://postgres:your_password@db.wcgobskmkjbclhkiqsyt.supabase.co:5432/postgres

# API keys
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 2: Set GitHub Secrets

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions**, and add:

```bash
SUPABASE_DATABASE_URL=postgresql://postgres:your_password@db.wcgobskmkjbclhkiqsyt.supabase.co:5432/postgres
GEMINI_API_KEY=your_gemini_api_key_here
SPOONACULAR_API_KEY=your_spoonacular_key_here  # Optional
```

### Step 3: Deploy to Railway

```bash
git push origin main  # or your branch name
```

Railway will automatically:
1. ✅ Detect Supabase credentials
2. ✅ Create database tables (if they don't exist)
3. ✅ Start the FastAPI server
4. ✅ Skip ChromaDB entirely

**Expected Railway logs:**
```
🚀 Starting CulinaraAI...
📊 Supabase detected - using cloud PostgreSQL + pgvector
🔄 Checking if database tables exist...
📋 Running database migration (first deployment)...
✅ Database tables created successfully
💡 No ingestion needed on deployment - GitHub Actions handles daily scraping!
🎯 Starting FastAPI server...
INFO:CulinaraAI:📊 Using Supabase PostgreSQL + pgvector
INFO:CulinaraAI:📊 Supabase has 0 recipes, 0 embeddings
INFO:CulinaraAI:✅ RAG Engine ready with Supabase
```

### Step 4: Trigger Initial Recipe Scraping

Go to **GitHub Actions** → **Daily Recipe Scraper** → **Run workflow**

This will:
1. Scrape 50 recipes from TheMealDB (free, unlimited)
2. Scrape 40 recipes from Spoonacular (free tier)
3. Generate embeddings with Gemini
4. Store everything in Supabase

**After ~5 minutes**, your database will have ~90 recipes ready!

## 🔄 Daily Automated Scraping

GitHub Actions runs automatically every day at **2 AM UTC**:
- Scrapes fresh recipes
- Deduplicates automatically (skips existing recipes)
- Generates embeddings
- Updates Supabase

No manual work required!

## 📊 Monitoring

### Check Railway Deployment Status
```bash
# Railway logs should show:
INFO:CulinaraAI:📊 Supabase has X recipes, Y embeddings
```

### Check GitHub Actions Status
Go to **Actions** tab in GitHub → **Daily Recipe Scraper**

Latest run should show:
```
✅ Scraping completed! Database now has 90 recipes, 90 embeddings
```

### Check Supabase Directly
In Supabase SQL Editor:
```sql
-- Check recipe count
SELECT COUNT(*) FROM recipes;

-- Check embedding count
SELECT COUNT(*) FROM recipe_embeddings;

-- View recent recipes
SELECT title, source_name, created_at
FROM recipes
ORDER BY created_at DESC
LIMIT 10;
```

## 🚀 Deployment Time Comparison

| Before (ChromaDB) | After (Supabase) |
|-------------------|------------------|
| 20 minutes (300 recipes) | < 1 minute |
| Re-ingests on every deploy | Zero ingestion |
| Data lost on redeploy | Persistent storage |
| Will scale poorly | Scales indefinitely |

## 🔧 Troubleshooting

### "Supabase has 0 recipes"
- Run GitHub Actions workflow manually (first time only)
- Check that SUPABASE_DATABASE_URL secret is set correctly
- Verify GitHub Actions completed successfully

### "Using ChromaDB (legacy mode)"
- Check Railway environment variables are set
- Redeploy Railway after setting variables
- Verify SUPABASE_URL and SUPABASE_KEY exist

### "Migration failed"
- Tables may already exist (safe to ignore)
- Check SUPABASE_DATABASE_URL format is correct
- Verify database password doesn't have special characters that need escaping

## 📝 Next Steps

1. **Wait for GitHub Actions** to populate recipes (runs daily)
2. **Monitor Railway logs** to confirm Supabase mode
3. **Scale up scraping** by increasing --count in the workflow (optional)
4. **Add more sources** by editing scripts/scrape_recipes.py (optional)

## 🎉 Benefits of This Setup

✅ No local setup required
✅ Automated daily recipe updates
✅ Fast deployments (< 1 minute)
✅ Persistent data storage
✅ Scales to thousands of recipes
✅ Free tier friendly (Supabase + GitHub Actions)
✅ Zero maintenance required

Your SaaS is now fully automated! 🚀
