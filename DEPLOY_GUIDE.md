# 🚀 Complete Deployment Guide for Hygein Detector

## Architecture
```
GitHub Pages (Frontend)
        ↓ (API calls)
    Railway.app (Backend Flask)
        ↓ (Model inference)
    TensorFlow/YOLO Models
```

---

## Step 1: Deploy Backend to Railway (5 minutes)

### 1a. Create Railway Account
- Go to **railway.app**
- Sign up with GitHub
- Authorize Railway

### 1b. Deploy
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find your repo and connect
4. Railway auto-detects `Procfile` and `requirements.txt`
5. Wait for deployment (5-10 min)
6. Copy your **live URL** (e.g., `https://hygein-detector-prod-abc123.railway.app`)

### 1c. Test Backend
```bash
curl https://your-railway-url.railway.app/api/status
```

You should get:
```json
{
  "model_loaded": true,
  "model_type": "Keras",
  "status": "Keras Ready ✓",
  "classes": ["hygienic", "insects", "ratimages"]
}
```

---

## Step 2: Enable GitHub Pages for Frontend

1. Go to your **GitHub repo Settings** → **Pages**
2. Under "Build and deployment"
   - Source: **Deploy from a branch**
   - Branch: **main** (or your branch)
   - Folder: **`/docs`**
3. Click **Save**
4. Wait 1-2 minutes for GitHub Pages to build
5. Your site will be at: `https://yourusername.github.io/repo-name`

---

## Step 3: Connect Frontend to Backend

Open `docs/index.html` and update the backend URL:

**Option A: Hard-code (Simple)**
```javascript
// Line ~180 in docs/index.html
const BACKEND_URL = 'https://your-railway-url.railway.app';
```

**Option B: localStorage (Recommended - User can change it)**
- Already implemented! Just click the URL in the UI to change it.

---

## Step 4: Test Everything

1. Open your GitHub Pages URL: `https://yourusername.github.io/repo-name`
2. Check **Status** panel - should show "✓ Connected"
3. Try uploading an image → should see predictions
4. Live feed should stream (if webcam available on backend)

---

## Troubleshooting

### Backend shows "✗ Offline"
- Check your Railway URL is correct
- Verify Railway deployment is running (check logs)
- Make sure CORS is enabled (✓ already in app.py)

### Image upload fails
- Check browser console for CORS errors
- Verify backend URL is correct
- Railway logs: `Railway dashboard → Logs tab`

### Live video doesn't show
- Railway's free tier might timeout long connections
- This is normal - image upload will still work

### Check Backend Logs
```bash
# Via Railway CLI
railway logs

# Or via GitHub Actions
```

---

## Production Checklist

- [x] Flask app with CORS enabled
- [x] Procfile for Railway
- [x] requirements.txt with gunicorn
- [x] GitHub Pages frontend
- [x] Environment-agnostic API endpoints
- [x] Error handling

---

## Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Railway | FREE (500 hours/month) | Plenty for hobby use |
| GitHub Pages | FREE | Static hosting only |
| Total | $0 | ✓ Completely free! |

---

## Advanced: Custom Domain

### On Railway:
1. Dashboard → your project → **Settings**
2. Add custom domain (e.g., `api.yourdomain.com`)

### On GitHub Pages:
1. Repo Settings → Pages
2. Add custom domain (e.g., `detector.yourdomain.com`)

---

## Next Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add deployment files for Railway + GitHub Pages"
   git push
   ```

2. **Deploy to Railway** (link repo)

3. **Enable GitHub Pages** (Settings → Pages)

4. **Update backend URL** in `docs/index.html`

5. **Test live at GitHub Pages URL**

---

## Need Help?

- **Railway Docs**: https://docs.railway.app
- **GitHub Pages Docs**: https://pages.github.com
- **Flask CORS**: https://flask-cors.readthedocs.io

---

Happy deploying! 🚀
