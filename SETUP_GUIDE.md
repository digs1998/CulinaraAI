# CulinaraAI Setup Guide - FREE Tier Implementation

## 🎯 What This Solves

1. ✅ **No more 20-minute deployments** - Recipes stored in Supabase (persists across deployments)
2. ✅ **No paywall issues** - Uses completely FREE recipe APIs
3. ✅ **$0 infrastructure cost** - Everything runs on free tiers
4. ✅ **Automatic daily updates** - GitHub Actions scrapes new recipes every day

---

## 📋 Prerequisites

1. GitHub account (you have this ✅)
2. Supabase account (free) - https://supabase.com
3. API keys (all free):
   - Gemini API key (you have this ✅)
   - Spoonacular API key (optional) - https://spoonacular.com/food-api

---

## 🚀 Step-by-Step Setup (30 minutes)

### Step 1: Set Up Supabase (10 minutes)

1. **Create Supabase project:**
   - Go to https://supabase.com/dashboard
   - Click "New Project"
   - Name: `culinara-ai`
   - Password: (choose a strong password)
   - Region: Choose closest to your users
   - Wait ~2 minutes for project to initialize

2. **Run database migration:**
   - In your Supabase dashboard, go to "SQL Editor"
   - Click "New Query"
   - Copy/paste the entire contents of `supabase/migrations/001_initial_schema.sql`
   - Click "Run" or press Ctrl+Enter
   - You should see: "Success. No rows returned"

3. **Get your database credentials:**
   - Go to "Project Settings" (gear icon) → "Database"
   - Scroll to "Connection string" section
   - Copy the **"URI"** connection string (starts with `postgresql://postgres:...`)
   - Save this as `SUPABASE_DATABASE_URL`

4. **Get your Supabase API credentials** (for backend):
   - Go to "Project Settings" → "API"
   - Copy **"Project URL"** → save as `SUPABASE_URL`
   - Copy **"anon public"** key → save as `SUPABASE_KEY`

### Step 2: Get Free API Keys (5 minutes)

1. **Spoonacular API** (optional but recommended):
   - Go to https://spoonacular.com/food-api
   - Click "Get Access"
   - Create free account
   - Copy your API key
   - Free tier: 150 requests/day

2. **Gemini API** (you already have this):
   - Confirm it's working at https://aistudio.google.com/app/apikey

### Step 3: Configure GitHub Secrets (5 minutes)

1. **Go to your GitHub repository:**
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"

2. **Add these secrets one by one:**

   | Secret Name | Value | Where to Get |
   |------------|-------|--------------|
   | `SUPABASE_DATABASE_URL` | `postgresql://postgres:...` | Supabase → Settings → Database → URI |
   | `SUPABASE_URL` | `https://xxx.supabase.co` | Supabase → Settings → API → Project URL |
   | `SUPABASE_KEY` | `eyJhbGc...` | Supabase → Settings → API → anon public key |
   | `GEMINI_API_KEY` | Your Gemini key | https://aistudio.google.com/app/apikey |
   | `SPOONACULAR_API_KEY` | Your Spoonacular key | https://spoonacular.com/food-api/console#Dashboard |

### Step 4: Test the Scraper Locally (10 minutes)

```bash
# 1. Install dependencies
pip install requests psycopg2-binary google-generativeai python-dotenv

# 2. Create .env file for local testing
cat > .env.local << 'EOF'
SUPABASE_DATABASE_URL=postgresql://postgres:your-password@db.xxx.supabase.co:5432/postgres
GEMINI_API_KEY=your-gemini-key
SPOONACULAR_API_KEY=your-spoonacular-key
EOF

# 3. Load environment variables
export $(cat .env.local | xargs)

# 4. Test scraper (scrapes ~90 recipes)
python scripts/scrape_recipes.py

# Expected output:
# ✅ Scraped 50 recipes from TheMealDB
# ✅ Scraped 40 recipes from Spoonacular
# ✅ Newly inserted: 90 recipes

# 5. Test embedding generator
python scripts/generate_embeddings.py

# Expected output:
# ✅ Successfully generated: 90 embeddings
```

### Step 5: Update Backend to Use Supabase (done automatically)

The backend code has been updated to use Supabase instead of ChromaDB. No action needed!

### Step 6: Deploy to Railway

1. **Update environment variables in Railway:**
   - Go to your Railway project
   - Click on your backend service
   - Go to "Variables" tab
   - Add:
     ```
     SUPABASE_URL=https://xxx.supabase.co
     SUPABASE_KEY=eyJhbGc...
     GEMINI_API_KEY=your-key
     ```

2. **Deploy:**
   ```bash
   git add .
   git commit -m "Migrate to Supabase with automated scraping"
   git push -u origin claude/recipe-saas-enhancement-nwlUI
   ```

3. **Verify deployment:**
   - Railway will auto-deploy
   - This time it should take **< 1 minute** (no ingestion!)
   - Check logs to confirm it connects to Supabase

---

## ⚙️ How the Automation Works

### Daily Scraping (GitHub Actions)

**Schedule:** Every day at 2 AM UTC

**What it does:**
1. Scrapes ~50 recipes from TheMealDB (free, unlimited)
2. Scrapes ~40 recipes from Spoonacular (if API key provided)
3. Inserts new recipes into Supabase (skips duplicates)
4. Generates embeddings for new recipes
5. Total time: ~5-10 minutes

**To manually trigger:**
1. Go to your GitHub repo
2. Click "Actions" tab
3. Click "Daily Recipe Scraper"
4. Click "Run workflow" → "Run workflow"

### Cost Breakdown (Free Tier)

| Service | Free Tier | Monthly Cost |
|---------|-----------|--------------|
| Supabase | 500MB DB, 2GB bandwidth | $0 |
| GitHub Actions | 2,000 minutes/month | $0 |
| Gemini API | 1,500 calls/day | $0 |
| TheMealDB | Unlimited | $0 |
| Spoonacular | 150 calls/day | $0 |
| Railway | $5 credit | $0-5 |
| Vercel | 100GB bandwidth | $0 |
| **TOTAL** | | **$0-5/month** |

---

## 📊 Expected Results

### After 1 Day
- 90-100 recipes in database
- All have embeddings
- Deployment time: < 1 minute ✅

### After 1 Week
- 600-700 recipes
- Diverse cuisines
- Still $0 cost

### After 1 Month
- 2,500-3,000 recipes
- Production-ready scale
- Still within free tiers

---

## 🧪 Testing the System

### Test 1: Verify Database

```bash
# Connect to Supabase and check
python3 << 'EOF'
import os
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DATABASE_URL'))
cursor = conn.cursor()

cursor.execute("SELECT * FROM get_database_stats()")
stats = cursor.fetchone()

print("📊 Database Statistics:")
print(f"   Total recipes: {stats[0]}")
print(f"   Total embeddings: {stats[1]}")
print(f"   Pending embeddings: {stats[2]}")
print(f"   Unique sources: {stats[3]}")
print(f"   Unique cuisines: {stats[4]}")

cursor.close()
conn.close()
EOF
```

### Test 2: Test Semantic Search

```bash
python3 << 'EOF'
import os
import psycopg2
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Generate query embedding
result = genai.embed_content(
    model="models/text-embedding-004",
    content="healthy pasta recipes",
    task_type="retrieval_query"
)
query_embedding = result["embedding"]

# Search
conn = psycopg2.connect(os.getenv('SUPABASE_DATABASE_URL'))
cursor = conn.cursor()

embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
cursor.execute("""
    SELECT title, similarity
    FROM search_recipes(%s::vector, 0.3, 5)
""", (embedding_str,))

print("🔍 Search results for 'healthy pasta recipes':")
for title, similarity in cursor.fetchall():
    print(f"   {similarity:.2%} - {title}")

cursor.close()
conn.close()
EOF
```

---

## 🐛 Troubleshooting

### Issue: "relation 'recipes' does not exist"
**Solution:** Run the migration SQL in Supabase SQL Editor

### Issue: "API quota exceeded" (Gemini)
**Solution:** Free tier is 1,500 calls/day. Wait 24 hours or upgrade.

### Issue: "connection refused" (Supabase)
**Solution:** Check your `SUPABASE_DATABASE_URL` is correct. It should start with `postgresql://postgres:`

### Issue: "No recipes scraped"
**Solution:**
- Check internet connection
- Verify API keys are set correctly
- TheMealDB might be down (rare) - wait 1 hour and retry

### Issue: GitHub Actions failing
**Solution:**
1. Go to Actions tab → Click failed run → View logs
2. Common issues:
   - Missing secrets (add them in Settings → Secrets)
   - API rate limits (reduce `num_recipes` in scraper)

---

## 📈 Monitoring & Maintenance

### Daily Checks (automated)
- GitHub Actions runs automatically
- Check Actions tab for green checkmarks
- If red, check logs and fix

### Weekly Checks
- Log into Supabase dashboard
- Check table sizes (Settings → Database)
- Verify recipe count is growing

### Monthly Maintenance
- Review Supabase usage (should be <500MB)
- Check Railway costs (should be ~$5)
- Consider upgrading if approaching limits

---

## 🎓 Next Steps

Once this is running smoothly:

1. **Improve User Acquisition** (see `SAAS_ENHANCEMENT_PLAN.md`)
   - Add landing page
   - SEO optimization
   - Product Hunt launch

2. **Add Features**
   - User accounts (Supabase Auth)
   - Save favorites
   - Meal planning

3. **Scale Infrastructure**
   - Migrate to Pinecone when you hit 5K recipes
   - Add Redis caching for API responses
   - Set up monitoring (Sentry)

---

## 💡 Pro Tips

1. **Monitor GitHub Actions quota:**
   - Settings → Billing → Plans and usage
   - You get 2,000 minutes/month free
   - Daily scraping uses ~10 min/day = 300 min/month

2. **Optimize scraping:**
   - Run less frequently (every 2-3 days instead of daily)
   - Or reduce `num_recipes` per run

3. **Backup your data:**
   - Supabase has automatic backups
   - Also export to JSON weekly:
     ```sql
     COPY (SELECT * FROM recipes) TO STDOUT WITH CSV HEADER;
     ```

---

## ✅ Success Checklist

- [ ] Supabase project created
- [ ] Database migration run successfully
- [ ] GitHub secrets configured
- [ ] Scraped first batch of recipes locally
- [ ] Generated embeddings successfully
- [ ] Backend deployed to Railway with Supabase
- [ ] Frontend deployed to Vercel
- [ ] GitHub Actions running automatically
- [ ] Deployment time < 1 minute ✅
- [ ] Recipes persist across deployments ✅

---

**Questions?** Check the troubleshooting section or create an issue in the repo.

**Ready to launch?** See `SAAS_ENHANCEMENT_PLAN.md` for marketing strategy.
