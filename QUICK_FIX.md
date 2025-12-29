# Quick Fix Guide

## Problem 1: "localhost:8000" Error

### Fix in 3 Steps:

1. **Get Railway URL**
   - Railway Dashboard → Your Service → Settings
   - Copy the public URL

2. **Set Vercel Environment Variable**
   - Vercel Dashboard → Settings → Environment Variables
   - Add: `VITE_API_URL` = `https://your-railway-url.up.railway.app`

3. **Redeploy**
   - Vercel → Deployments → Redeploy latest

✅ **Done!** Frontend will now connect to Railway backend.

---

## Problem 2: Ingestion Runs Every Deployment

### Fix with Railway Volumes:

1. **Create Volume**
   - Railway → Your Service → Variables
   - Add Volume with mount path: `/data`

2. **Set Environment Variable**
   - Add: `RUN_INGESTION=true`

3. **Deploy**
   - Push your code
   - First deployment will run ingestion
   - ChromaDB saved to `/data` volume

4. **Disable Ingestion** (Optional)
   - Set: `RUN_INGESTION=false`
   - Future deployments skip ingestion

✅ **Done!** ChromaDB persists across deployments.

---

## Verification

### Frontend
Open browser console and check:
- No "localhost:8000" errors
- Network tab shows requests to Railway URL

### Backend
Check Railway logs for:
```
📦 Railway volume detected at: /data
✅ ChromaDB exists with data
```

---

📖 Full details: [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md)
