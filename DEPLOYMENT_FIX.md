# Deployment Fixes for CulinaraAI

## Issues Fixed

### 1. Frontend "localhost:8000" Error on Vercel
### 2. Railway Running Ingestion on Every Deployment

---

## Issue 1: Frontend Connection Error

### Problem
When clicking "Discover Recipes" from the onboarding page, the frontend shows:
```
⚠️ Something went wrong. Make sure the backend is running on http://localhost:8000
```

### Root Cause
The Vercel frontend deployment is missing the `VITE_API_URL` environment variable, so it defaults to `http://localhost:8000` instead of your Railway backend URL.

In `frontend/src/services/api.ts`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### Solution

**Step 1: Get Your Railway Backend URL**
1. Go to your Railway dashboard
2. Click on your backend service
3. Go to "Settings" tab
4. Copy the public URL (e.g., `https://your-app.up.railway.app`)

**Step 2: Set Environment Variable in Vercel**
1. Go to your Vercel dashboard
2. Select your CulinaraAI project
3. Go to "Settings" → "Environment Variables"
4. Add a new variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://your-railway-backend-url.up.railway.app` (from Step 1)
   - **Environments**: Select all (Production, Preview, Development)
5. Click "Save"

**Step 3: Redeploy Frontend**
1. Go to "Deployments" tab in Vercel
2. Click on the latest deployment
3. Click "Redeploy" button
4. Or push a new commit to trigger automatic deployment

**Step 4: Verify**
1. Visit your Vercel app
2. Complete the onboarding
3. Click "Discover Recipes"
4. Should now connect to Railway backend successfully!

---

## Issue 2: Railway Running Ingestion Every Deployment

### Problem
Every time you deploy to Railway, the app runs the full ingestion process, which:
- Takes time on startup
- Uses API credits unnecessarily
- Defeats the purpose of having ChromaDB

### Root Cause
1. `chroma_db/` folder is in `.gitignore`, so it's never committed to git
2. Railway builds from git, so `chroma_db/` doesn't exist in the build
3. Docker containers are ephemeral - data created at runtime is lost on redeployment
4. The startup script detects empty ChromaDB and runs ingestion again

### Solutions (Choose ONE)

#### Option A: Use Railway Volumes (Recommended - Persistent Storage)

Railway offers persistent volumes that survive across deployments.

**Setup Steps:**

1. **Create a Volume in Railway**
   - Go to your Railway project
   - Click on your backend service
   - Go to "Variables" tab
   - Add a new volume:
     - **Mount Path**: `/data`
     - Click "Add Volume"

2. **Set Environment Variable**
   - Still in "Variables" tab
   - Add:
     - **Name**: `RUN_INGESTION`
     - **Value**: `true`

3. **First Deployment**
   - Push your updated code (with the new `startup.sh`)
   - Railway will detect the volume and set `RAILWAY_VOLUME_MOUNT_PATH=/data`
   - The startup script will:
     - Create symlink: `chroma_db` → `/data/chroma_db`
     - Run ingestion (since it's empty)
     - Store data in `/data/chroma_db` (persisted!)

4. **Subsequent Deployments**
   - Volume data persists
   - Startup script finds existing ChromaDB
   - Skips ingestion
   - App starts immediately!

5. **Optional: Disable Ingestion After First Run**
   - Once you verify ChromaDB is populated
   - Set `RUN_INGESTION=false` or remove the variable
   - This prevents accidental ingestion runs

**Verification:**
Check Railway logs for:
```bash
📦 Railway volume detected at: /data
✅ Linked chroma_db to persistent volume
✅ ChromaDB exists with data (XXX files)
🎯 Starting FastAPI server...
```

---

#### Option B: Commit ChromaDB to Git (Simple but Not Recommended)

**Pros:**
- Simple setup
- No Railway volume needed
- ChromaDB included in every build

**Cons:**
- Git repo becomes very large (ChromaDB can be hundreds of MB)
- Slow git operations
- Against best practices (don't commit generated data)
- Updates require new commits

**Setup Steps:**

1. **Remove `chroma_db/` from `.gitignore`**
   ```bash
   # Edit .gitignore and remove line 49:
   # chroma_db/
   ```

2. **Run Ingestion Locally**
   ```bash
   cd backend
   python data/run_ingestion.py
   ```

3. **Commit ChromaDB**
   ```bash
   git add backend/chroma_db/
   git commit -m "Add pre-populated ChromaDB"
   git push
   ```

4. **Update Railway Environment**
   - Remove or set `RUN_INGESTION=false`

5. **Deploy**
   - Railway will now include `chroma_db/` in the Docker image
   - No ingestion will run on startup

**Warning:** This is not recommended for production. Use Option A instead.

---

#### Option C: Pre-build ChromaDB in Docker (Alternative)

Build ChromaDB during Docker image build instead of runtime.

**Setup Steps:**

1. **Update Dockerfile**
   Add before the CMD line:
   ```dockerfile
   # Run ingestion during build (requires API keys as build args)
   ARG GEMINI_API_KEY
   ENV GEMINI_API_KEY=$GEMINI_API_KEY
   RUN python data/run_ingestion.py || echo "Skipping ingestion"
   ```

2. **Update Railway Build Settings**
   - Go to Railway service settings
   - Add build-time environment variables (if supported)
   - Or use Railway's secret management

**Cons:**
- Rebuilds ChromaDB on every deployment
- Longer build times
- Still uses API credits on each build
- Not truly persistent

**Not Recommended** - Option A (Volumes) is better.

---

## Recommended Setup Summary

### For Vercel Frontend:
1. Set environment variable: `VITE_API_URL` = `https://your-railway-app.up.railway.app`
2. Redeploy

### For Railway Backend:
1. Create a volume with mount path `/data`
2. Set `RUN_INGESTION=true`
3. Deploy and verify ingestion runs successfully
4. Optionally set `RUN_INGESTION=false` after first successful run
5. Future deployments will use persisted ChromaDB

---

## Verification Checklist

### Frontend (Vercel)
- [ ] `VITE_API_URL` environment variable is set
- [ ] Frontend can connect to Railway backend
- [ ] No "localhost:8000" errors
- [ ] Onboarding → Discover works correctly

### Backend (Railway)
- [ ] Volume is created and mounted at `/data`
- [ ] Initial deployment runs ingestion successfully
- [ ] Subsequent deployments skip ingestion
- [ ] ChromaDB data persists across deployments
- [ ] Startup logs show: "✅ ChromaDB exists with data"

---

## Troubleshooting

### Frontend Still Shows localhost:8000 Error
1. Verify `VITE_API_URL` is set in Vercel
2. Check it's set for the right environment (Production/Preview)
3. Redeploy to pick up new environment variable
4. Clear browser cache and reload
5. Check browser console for actual error message

### Backend Still Runs Ingestion Every Time
1. Verify volume is created in Railway dashboard
2. Check Railway logs for "📦 Railway volume detected"
3. Verify `RAILWAY_VOLUME_MOUNT_PATH` env var is set automatically
4. Check if chroma_db symlink was created successfully
5. Verify ChromaDB actually has data files in the volume

### ChromaDB Data Lost After Deployment
1. Ensure you're using Railway volumes (Option A)
2. Verify volume mount path is correct
3. Check startup.sh is creating symlink properly
4. Don't use Option B or C - they don't persist data correctly

---

## Additional Notes

### Why This Happens
- **Docker containers are ephemeral**: Any data created at runtime is lost when container restarts
- **Railway rebuilds on each deploy**: Fresh container = fresh filesystem
- **Git doesn't track chroma_db**: Excluded by .gitignore
- **Solution**: Use persistent volumes to store data outside the container

### Cost Optimization
- First ingestion: ~300 recipes, uses Gemini API credits
- With persistence: Ingestion runs only once
- Without persistence: Ingestion runs on every deployment
- **Savings**: Significant API credits and deployment time

### When to Re-run Ingestion
You might want to re-run ingestion when:
- Adding new recipes or data sources
- Updating embeddings model
- Fixing data quality issues

To re-run:
1. Set `RUN_INGESTION=true` in Railway
2. Manually delete contents of volume (or clear chroma_db folder)
3. Redeploy
4. After completion, set `RUN_INGESTION=false`

---

## Questions?

If you encounter issues not covered here, check:
1. Railway deployment logs
2. Vercel deployment logs
3. Browser developer console
4. Network tab for API calls

Happy cooking with CulinaraAI! 🍳🌿
