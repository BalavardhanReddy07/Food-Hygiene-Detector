# Hygein Detector 🐭🦟

Real-time pest detection system using deep learning. Detects insects and rats with high accuracy.

## Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py

# Open browser
# http://localhost:5000
```

## Deploy (Global)

See `DEPLOY_GUIDE.md` for complete instructions.

**TL;DR:**
1. Deploy backend to Railway (free)
2. Enable GitHub Pages frontend
3. Update backend URL in `docs/index.html`
4. Done! Access at `https://yourusername.github.io/Hygein-Detector`

## Features

✅ Real-time video detection  
✅ Image upload & prediction  
✅ Live confidence scores  
✅ Snapshot downloads  
✅ Multi-model support (YOLO & Keras)  
✅ CORS-enabled API  
✅ Production-ready  

## Architecture

```
Frontend (GitHub Pages)
    ↓
    ↓ HTTP API calls
    ↓
Backend (Railway/Heroku)
    ↓
    ↓ TensorFlow inference
    ↓
Models (Keras/YOLO)
```

## Files

- `app.py` - Flask backend
- `docs/index.html` - Frontend UI
- `models/` - Trained models
- `dataset/` - Training data
- `Procfile` - Railway config
- `requirements.txt` - Python deps

## Model Training

```bash
python train.py --data_dir dataset --epochs 30
```

See `train.py` for options.

## Support

- Issues? Check `DEPLOY_GUIDE.md`
- Local problems? Check `QUICK_START.md`
- Model questions? See `train.py` comments

---

Made with ❤️ for pest detection.
