# Supabase Setup Checklist - CulinaraAI

Follow these exact steps to set up your Supabase database.

---

## ✅ Step 1: Create Supabase Project (5 min)

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in:
   - **Name:** `culinara-ai-test`
   - **Database Password:** Choose strong password (SAVE IT!)
   - **Region:** Select closest to you (e.g., US East)
4. Click **"Create new project"**
5. Wait ~2 minutes for initialization
6. You'll see ✅ when ready

**Status:** [ ] Project created

---

## ✅ Step 2: Get Your Credentials (3 min)

### 2.1 Get Project URL

1. In Supabase Dashboard, click **"Settings"** (gear icon, bottom left)
2. Click **"API"**
3. Find **"Project URL"**
4. Copy: `https://xxxxxxxxxxxxx.supabase.co`
5. Save as: `SUPABASE_URL`

**Status:** [ ] Project URL copied

### 2.2 Get Anon/Public Key

1. Still in Settings → API
2. Find **"Project API keys"**
3. Copy the **"anon public"** key (starts with `eyJhbGc...`)
4. Save as: `SUPABASE_KEY`

**Status:** [ ] Anon key copied

### 2.3 Get Database Connection String

1. In Settings, click **"Database"**
2. Scroll to **"Connection string"**
3. Select **"URI"** tab
4. Copy the string (starts with `postgresql://postgres:...`)
5. **IMPORTANT:** Replace `[YOUR-PASSWORD]` with your actual database password
6. Save as: `SUPABASE_DATABASE_URL`

**Example:**
```
Before: postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
After:  postgresql://postgres:MyStr0ngP@ssw0rd@db.xxx.supabase.co:5432/postgres
```

**Status:** [ ] Database URL copied and password replaced

---

## ✅ Step 3: Fill in .env.test (2 min)

1. Open the file:
   ```bash
   nano .env.test
   # or use your preferred editor
   ```

2. Fill in these values:
   ```env
   SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx
   SUPABASE_DATABASE_URL=postgresql://postgres:YourPassword@db.xxx.supabase.co:5432/postgres
   GEMINI_API_KEY=your-gemini-api-key
   SPOONACULAR_API_KEY=your-spoonacular-key  # Optional
   ```

3. Save and exit (Ctrl+X, Y, Enter in nano)

**Status:** [ ] .env.test filled in

---

## ✅ Step 4: Run Migration SQL (3 min)

### 4.1 Open SQL Editor

1. In Supabase Dashboard, click **"SQL Editor"** (left sidebar)
2. Click **"New Query"** button (top right)

**Status:** [ ] SQL Editor opened

### 4.2 Copy the Migration SQL

1. Display the SQL:
   ```bash
   cat supabase/migrations/001_initial_schema.sql
   ```

2. Select all and copy (Ctrl+A, Ctrl+C)

**Status:** [ ] SQL copied

### 4.3 Run the Migration

1. Paste into SQL Editor (Ctrl+V)
2. Click **"Run"** button (or press Ctrl+Enter)
3. Wait 2-3 seconds

**Expected Result:**
```
Success. Rows returned: 2

table_name
recipes
recipe_embeddings
```

**Status:** [ ] Migration ran successfully

---

## ✅ Step 5: Verify Setup (2 min)

Run this query in SQL Editor:

```sql
SELECT * FROM get_database_stats();
```

**Expected Result:**
```
total_recipes: 0
total_embeddings: 0
recipes_pending_embedding: 0
unique_sources: 0
unique_cuisines: 0
```

If you see this, **everything is set up correctly!** ✅

**Status:** [ ] Verification query successful

---

## ✅ Step 6: Check Table Editor (1 min)

1. Click **"Table Editor"** (left sidebar)
2. You should see:
   - ✅ `recipes` table
   - ✅ `recipe_embeddings` table

3. Click on `recipes` table
4. Should show columns: id, title, ingredients, instructions, etc.

**Status:** [ ] Tables visible in Table Editor

---

## ✅ Complete Setup Checklist

- [ ] Supabase project created and initialized
- [ ] Project URL copied
- [ ] Anon key copied
- [ ] Database connection string copied (with password replaced)
- [ ] .env.test filled in with all credentials
- [ ] Migration SQL run successfully
- [ ] Verification query shows correct structure
- [ ] Tables visible in Table Editor

---

## 🎉 Setup Complete!

If all checkboxes are ticked, you're ready to:

```bash
# Load environment
source .env.test

# Run automated tests
./run_tests.sh
```

The test script will:
1. ✅ Test Supabase connection
2. ✅ Scrape ~50 recipes
3. ✅ Generate embeddings
4. ✅ Test backend startup
5. ✅ Test recipe search
6. ✅ Full integration test

**Estimated time:** 20-30 minutes

---

## 🐛 Common Issues

### Issue: "relation 'recipes' does not exist"

**Cause:** Migration SQL not run or failed

**Fix:**
1. Go to SQL Editor
2. Re-run the migration SQL
3. Check for error messages in red

---

### Issue: "type 'vector' does not exist"

**Cause:** pgvector extension not enabled

**Fix:**
```sql
-- Run this in SQL Editor:
CREATE EXTENSION IF NOT EXISTS vector;

-- Then re-run the full migration
```

---

### Issue: "invalid input for query argument"

**Cause:** Wrong credentials format

**Fix:**
- SUPABASE_URL must start with `https://`
- SUPABASE_KEY should start with `eyJhbGc`
- SUPABASE_DATABASE_URL must have actual password (not `[YOUR-PASSWORD]`)

---

### Issue: "permission denied for relation recipes"

**Cause:** Using service role key instead of anon key

**Fix:**
- Make sure SUPABASE_KEY is the **"anon public"** key
- NOT the "service role" key

---

## 💡 Pro Tips

1. **Save your credentials securely:**
   ```bash
   # Good: In .env.test (gitignored)
   # Bad: In your code or public files
   ```

2. **Test connection before running full tests:**
   ```bash
   source .env.test
   python3 -c "from supabase import create_client; import os; print(create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')).table('recipes').select('count', count='exact').execute())"
   ```

3. **Use Supabase Table Editor for debugging:**
   - Visual interface to see your data
   - Can manually add/edit/delete rows
   - Good for testing before automation

---

## 📞 Ready for Tests?

Once all checkboxes are complete:

```bash
source .env.test
./run_tests.sh
```

I'll help you debug any issues that come up! 🚀
