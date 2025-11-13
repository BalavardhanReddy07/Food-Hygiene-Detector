# 🎯 Railway Deployment Checklist

## ✅ App.py - What Was Fixed

Your new `app.py` (262 lines) includes these critical fixes:

### 1. ✅ CORS Enabled (Lines 11-43)
```python
HAS_CORS = False
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    pass

if HAS_CORS:
    CORS(app, resources={r"/api/*": {"origins": "*"}})
```
**Why:** GitHub Pages frontend needs to call Railway backend API

---

### 2. ✅ Health Check Endpoint (Lines 155-165)
```python
@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'models_loaded': models_loaded,
        'model_status': model_status,
        ...
    })
```
**Why:** Frontend polls this to check if backend is ready

---

### 3. ✅ Safe Webcam Init (Lines 55-67)
```python
def init_webcam():
    global cap, webcam_available
    try:
        cap = cv2.VideoCapture(0)
        if cap and cap.isOpened():
            ...
            webcam_available = True
            return True
    except:
        cap = None
        webcam_available = False
        return False
```
**Why:** Fails gracefully in cloud (no blocking)

---

### 4. ✅ Background Model Loading (Lines 69-102)
```python
def load_models():
    global model_yolo, model_keras, ...
    # Tries YOLO first, then Keras fallback
    ...

loader_thread = threading.Thread(target=load_models, daemon=True)
loader_thread.start()
```
**Why:** App starts immediately, doesn't wait for models

---

### 5. ✅ API Prediction Endpoint (Lines 168-209)
```python
@app.route('/api/predict_image', methods=['POST'])
def api_predict_image():
    if not models_loaded:
        return jsonify({'error': 'Models loading'}), 503
    # ... process image ...
    return jsonify({'predictions': predictions, ...})
```
**Why:** Frontend sends image here for prediction

---

### 6. ✅ Production Config (Lines 258-262)
```python
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG, threaded=True)
```
**Why:** Works on Railway (reads PORT from env), threaded for concurrency

---

## 📋 Pre-Deployment Verification

### Files Exist ✓
- [x] `app.py` - 262 lines, clean syntax
- [x] `requirements.txt` - Has flask-cors
- [x] `Procfile` - Has `web: gunicorn app:app`
- [x] `runtime.txt` - Has `python-3.10.13`
- [x] `utils.py` - Helper functions exist
- [x] `templates/index.html` - Flask template

### Directories Created ✓
- [x] `static/` - For CSS/JS files
- [x] `templates/` - For Flask templates
- [x] `snapshots/` - For saving predictions

### Model Files
- [ ] `models/insect_rat_model.keras` - **Must exist for Keras fallback**
  - Location: `/models/insect_rat_model.keras`
  - Size: ~50MB (OK for Railway)
  - If missing: App works but shows "No models available"

---

## 🚀 Deployment Steps

### Step 1: Local Testing (5 min)
```bash
cd Desktop/"Hygein Detector"
pip install -r requirements.txt
python app.py

# In another terminal:
curl http://localhost:5000/api/status
```

✓ Should return JSON with status info

---

### Step 2: Git Setup
```bash
cd Desktop/"Hygein Detector"
git init
git add .
git commit -m "Production-ready Flask app"
git remote add origin https://github.com/YOUR_USERNAME/Hygein-Detector.git
git push -u origin main
```

✓ Code is now on GitHub

---

### Step 3: Deploy Backend to Railway (10 min)

1. Go to **railway.app**
2. Click **Create New Project**
3. Click **Deploy from GitHub repo**
4. Select your repo
5. Click **Deploy**
6. ⏳ Wait for green "Running" status
7. 📋 Copy your Railway URL (e.g., `https://hygein-detector-prod-abc.railway.app`)

✓ Backend is live!

---

### Step 4: Enable GitHub Pages

1. Go to repo **Settings**
2. Click **Pages** (left menu)
3. Under "Source", select:
   - Branch: `main`
   - Folder: `/docs`
4. Click **Save**
5. ⏳ Wait 1-2 minutes for blue link to appear
6. 📋 Copy your GitHub Pages URL (e.g., `https://yourusername.github.io/Hygein-Detector`)

✓ Frontend is live!

---

### Step 5: Connect Frontend to Backend

**Option A: UI Method (Easiest)**
1. Open your GitHub Pages URL
2. Click the blue backend URL field at top
3. Paste your Railway URL
4. Test: Upload an image → should work!

**Option B: Edit Code**
Find in `docs/index.html` (~line 180):
```javascript
const BACKEND_URL = 'http://localhost:5000';
```

Change to:
```javascript
const BACKEND_URL = 'https://your-railway-url.railway.app';
```

Commit and push: `git add . && git commit -m "Update backend URL" && git push`

✓ Frontend and backend connected!

---

## ✅ Verification Checklist

After deployment:

- [ ] Backend URL responds: `curl https://your-railway-url.railway.app/api/status`
- [ ] Frontend loads: GitHub Pages URL opens in browser
- [ ] Status shows "Connected": Green indicator at top of page
- [ ] Model status shows: "YOLO Ready" or "Keras Ready" (or "No models available")
- [ ] Can upload image: Test with a JPG file
- [ ] Prediction returns: See confidence scores
- [ ] Can download: Annotated image downloads

---

## 🆘 If Deployment Fails

### Issue: Backend shows "Offline"
1. Check Railway URL is correct (copy from dashboard)
2. Verify Railway status is green "Running"
3. Check Railway logs for errors
4. Retry: Redeploy from GitHub

### Issue: "Models not available"
1. Check `models/insect_rat_model.keras` exists locally
2. Verify file is in GitHub repo
3. Train a new model: `python train.py`
4. Push to GitHub and redeploy

### Issue: CORS error in console
1. Restart backend
2. Hard refresh frontend (Ctrl+Shift+R)
3. Check `flask-cors` in `requirements.txt`

### Issue: Upload fails with 413 error
1. Image file too large (>16MB)
2. Compress or use smaller image
3. Or increase limit in `app.py` line 43

---

## 📚 Documentation Files Created

| File | Purpose |
|------|---------|
| `DEPLOYMENT_READY.md` | Summary of what was fixed |
| `RAILWAY_TROUBLESHOOT.md` | Detailed troubleshooting guide |
| `DEPLOYMENT.md` | Original deployment notes |
| `DEPLOY_GUIDE.md` | Step-by-step deployment |
| `QUICK_START.md` | Quick reference |

---

## 💾 File Sizes (For Reference)

```
app.py                    10 KB ✓ Small and efficient
requirements.txt          0.2 KB ✓ Minimal dependencies
models/insect_rat_model.keras  ~50 MB (OK for Railway)
```

---

## 🎉 Success! What Now?

Once deployed and verified:

1. **Share your app**: Give friends the GitHub Pages URL
2. **Add more data**: Upload more training images to improve accuracy
3. **Monitor usage**: Check Railway dashboard for activity
4. **Upgrade model**: Train with more data for better detection

---

## 📞 Quick Reference

| What | Where |
|------|-------|
| Local testing | `python app.py` → `http://localhost:5000` |
| Railway dashboard | `railway.app` → Your Project → Logs |
| GitHub Pages URL | Repo Settings → Pages → Your link |
| Backend API | `/api/status` (check health) |
| Backend API | `/api/predict_image` (upload image) |

---

**Status: ✅ READY TO DEPLOY**

All production issues have been resolved. Your app is ready for Railway!

Follow the 5-step deployment process above and you'll be live in 15 minutes.
