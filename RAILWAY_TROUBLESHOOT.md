# 🚀 Railway Deployment Troubleshooting & Quick Start

## ✅ Changes Made to `app.py`

Your updated `app.py` is now **production-ready** with:

1. **CORS Enabled** - Allows GitHub Pages frontend to communicate with Railway backend
2. **Safe Webcam Init** - Gracefully handles cloud environments (no webcam)
3. **Better Error Handling** - Catches and logs errors properly
4. **API Status Endpoint** - Frontend can check if backend is alive (`/api/status`)
5. **Production Config** - Uses PORT from environment, safe defaults
6. **Background Model Loading** - Non-blocking startup
7. **Comprehensive Logging** - Shows what's happening at startup

---

## 🎯 Quick Deployment Steps

### Step 1: Push Code to GitHub
```bash
git add .
git commit -m "Production-ready Flask app for Railway"
git push origin main
```

### Step 2: Deploy to Railway (5 minutes)

1. **Go to railway.app**
2. Click **New Project**
3. **Deploy from GitHub repo**
4. Select your repo
5. **Wait for deployment** (Railway auto-detects Procfile)
6. **Copy your live URL** (shown in Dashboard)

Example: `https://hygein-detector-prod-abc123.railway.app`

### Step 3: Enable GitHub Pages

1. **Repo Settings → Pages**
2. Source: **Deploy from branch** → `main` → `/docs` folder
3. Save → Wait 1-2 min
4. Your URL: `https://yourusername.github.io/Hygein-Detector`

### Step 4: Connect Frontend to Backend

**Option A: Click the URL in the UI**
- Open your GitHub Pages URL
- Click the backend URL at the top (blue alert)
- Paste your Railway URL
- Done!

**Option B: Edit `docs/index.html` directly**
Find this line (~line 180):
```javascript
const BACKEND_URL = localStorage.getItem('backendUrl') || 'http://localhost:5000';
```

Change to:
```javascript
const BACKEND_URL = 'https://your-railway-url.railway.app';
```

---

## 🔍 Common Issues & Fixes

### Issue 1: "Models not loading"
**Symptoms:** Status shows "No models loaded"

**Fixes:**
1. Make sure `models/insect_rat_model.keras` exists
2. Check file size: Should be 20-100 MB
3. Check Railway logs for loading errors:
   ```
   Railway Dashboard → Logs tab → Look for [ERROR]
   ```

**Solution:**
- Upload model file to Railway via Git
- Or train a new model: `python train.py`

---

### Issue 2: "Backend unreachable"  
**Symptoms:** Frontend shows "✗ Offline"

**Fixes:**

1. **Verify Railroad URL is correct**
   - Copy exact URL from Railway dashboard (including `https://`)
   - No trailing slash!

2. **Check if Railway is running**
   - Railway Dashboard → Your project → Status should be green "Running"

3. **Check Railway logs**
   ```
   Railway Dashboard → Logs → If you see errors, fix them
   ```

4. **Test from command line**
   ```bash
   curl https://your-railway-url.railway.app/api/status
   ```
   Should return JSON with model info.

---

### Issue 3: "CORS errors"
**Symptoms:** Browser console shows CORS error

**This is FIXED in new app.py** - CORS is enabled.

If still having issues:
- Check that `flask-cors` is in `requirements.txt` ✓
- Railway should have auto-installed it

---

### Issue 4: "Image upload fails"
**Symptoms:** Upload button doesn't work

**Fixes:**
1. Check browser console for errors (F12 → Console tab)
2. Check backend URL is correct
3. If error says "413 Payload Too Large":
   - Railway has 16MB upload limit (should be fine for images)
   - Compress your image

---

### Issue 5: "Webcam not showing"
**Symptoms:** Live feed shows "No webcam available"

**This is NORMAL on Railway** - cloud servers don't have cameras.

Image upload will still work perfectly. If you need live feed:
- Run locally: `python app.py`
- Or use `realtime.py` script locally

---

## ✅ Verification Checklist

- [ ] `app.py` has CORS enabled
- [ ] `requirements.txt` has flask-cors & gunicorn
- [ ] `Procfile` exists with correct syntax
- [ ] Model files (`models/insect_rat_model.keras`) exist
- [ ] `docs/index.html` has correct backend URL
- [ ] Railway deployment is green/running
- [ ] GitHub Pages is enabled in `/docs`
- [ ] Can access GitHub Pages URL in browser
- [ ] `/api/status` endpoint returns JSON

---

## 🧪 Local Testing Before Deployment

```bash
# Install requirements
pip install -r requirements.txt

# Test locally
python app.py

# Open browser
http://localhost:5000

# Try predictions
# Upload an image → should work
```

---

## 📊 Production Monitoring

Once deployed to Railway:

1. **Check Logs**
   - Railway Dashboard → Your project → Logs
   - Look for `[INFO]` and `[ERROR]` messages

2. **Monitor Status**
   - Open `/api/status` endpoint to check models
   - Frontend shows model status in top-right

3. **Common Log Messages**
   ```
   [INFO] Loading models...
   [SUCCESS] YOLO loaded           ← Good
   [INFO] Webcam not available     ← Normal in cloud
   [WARN] Models not available     ← Bad - check models folder
   [ERROR] YOLO failed: ...        ← Problem loading model
   ```

---

## 🚨 If Deployment Still Fails

1. **Check Railway error logs** (most common)
2. **Verify all files exist:**
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `models/insect_rat_model.keras`
   - `templates/index.html`

3. **Re-run locally:**
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

4. **If model fails locally:**
   - Train new model: `python train.py`
   - Or download pre-trained model

---

## 💡 Pro Tips

- **Faster deploys:** Commit only necessary files (use `.gitignore`)
- **Smaller model:** Use quantized or compressed model
- **Better performance:** Use Railway's GPU tier (paid)
- **Custom domain:** Add to Railway settings

---

## 📞 Support

- **Railway docs:** https://docs.railway.app
- **Flask-CORS:** https://flask-cors.readthedocs.io
- **GitHub Pages:** https://pages.github.com

---

## Success! 🎉

If everything works:
1. Frontend (GitHub Pages) shows "✓ Connected"
2. You can upload images and get predictions
3. Download annotated images
4. Status shows model type (YOLO or Keras)

**You're live and globally accessible!**
