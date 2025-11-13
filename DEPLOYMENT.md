# Deployment Guide for Hygein Detector

## Quick Start

### Option 1: Deploy to Railway (Easiest - FREE)

1. **Sign up at railway.app**
2. **Connect GitHub repo**
3. **Railway auto-detects Python + Procfile**
4. **Get your live URL**

### Option 2: Deploy to Render (FREE Tier)

1. Go to render.com
2. Click "New +" → "Web Service"
3. Connect GitHub
4. Set Build Command: `pip install -r requirements.txt`
5. Set Start Command: `gunicorn app:app`
6. Deploy

### Option 3: Deploy Frontend to GitHub Pages

After backend is live on Railway/Render:

1. Create `docs/index.html` with API pointing to your backend
2. Go to Settings → Pages → Choose `docs/` folder
3. Enable GitHub Pages

---

## Environment Variables

Add to your hosting platform:
```
FLASK_ENV=production
FLASK_DEBUG=0
PORT=5000
```

---

## Local Testing

```bash
# Install
pip install -r requirements.txt

# Run
python app.py
```

Open http://localhost:5000

---

## Production Checklist

- [ ] Add CORS headers (✓ already in app.py)
- [ ] Use gunicorn (✓ in Procfile)
- [ ] Set debug=False (✓ in app.py)
- [ ] Add requirements.txt with gunicorn (✓)
- [ ] Test with production flag
