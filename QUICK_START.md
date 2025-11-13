# Quick Deployment Checklist

## Files Created for Deployment:
✓ `Procfile` - Railway/Heroku config
✓ `Dockerfile` - Docker support
✓ `runtime.txt` - Python version
✓ `.gitignore` - Exclude large files
✓ `docs/index.html` - GitHub Pages frontend
✓ `DEPLOY_GUIDE.md` - Full instructions
✓ `app.py` - Flask backend with CORS

## The 3-Step Process:

### 1. BACKEND (Railway) - 5 minutes
```
1. Go to railway.app
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Select your repo
5. Wait for deployment
6. Copy your live URL
```

### 2. FRONTEND (GitHub Pages) - 2 minutes
```
1. Go to Repo Settings → Pages
2. Source: Deploy from a branch → main
3. Folder: /docs
4. Click Save
5. Wait 1-2 min for build
```

### 3. CONNECT - 1 minute
```
1. Open your GitHub Pages URL
2. Click on the backend URL (top alert)
3. Paste your Railway URL
4. Click predict button to test
```

## Your Live URLs:

- **Frontend:** `https://yourusername.github.io/Hygein-Detector`
- **Backend:** `https://your-project.railway.app`

## Testing Endpoints:

```bash
# Check backend is alive
curl https://your-railway-url.railway.app/api/status

# Upload image (from frontend UI)
# Frontend handles all requests automatically
```

## Troubleshooting One-Liner:

```bash
# See what's wrong on Railway
railway logs

# Test from command line
curl -X GET https://your-railway-url.railway.app/api/status
```

---

**That's it! Your app is now live and globally accessible!** 🎉
