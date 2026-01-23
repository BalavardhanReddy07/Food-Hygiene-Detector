import os
import uuid
import base64
from datetime import datetime
import json
import time

import cv2
import numpy as np
from flask import Flask, jsonify, request, Response, send_from_directory
import google.generativeai as genai

from realtime_google_api import CONFIG, ThreatCategorizer, Visualizer, DetectionAnalyzer

# ========================
# SETUP
# ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- FIXED: Configure API Key directly from Environment Variables ---
# This replaces the need for 'setup_credentials.py'
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL: GEMINI_API_KEY not found in environment variables.")
    # On Render, this will cause the deployment to fail if the key isn't set
    exit(1)

try:
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    exit(1)
# ------------------------------------------------------------------

app = Flask(__name__, static_folder=BASE_DIR, template_folder=BASE_DIR)

# ========================
# GEMINI MODEL INITIALIZATION
# ========================
MODEL_NAME = "gemini-robotics-er-1.5-preview"

try:
    print(f"🔌 Connecting to model: {MODEL_NAME}...")
    gemini_model = genai.GenerativeModel(MODEL_NAME)
    print(f"✓ Gemini Model Initialized: {MODEL_NAME}")
except Exception as e:
    print(f"✗ Critical Error initializing {MODEL_NAME}: {e}")
    print("  -> Please verify your API Key has access to this specific preview model.")
    gemini_model = None

# Initialize Tools
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
categorizer = ThreatCategorizer()
visualizer = Visualizer()
analyzer = DetectionAnalyzer()

# ========================
# HELPER FUNCTIONS
# ========================

def blur_faces(image: np.ndarray) -> np.ndarray:
    """Detects and blurs human faces to protect privacy."""
    if image is None or image.size == 0: return image
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        for (x, y, w, h) in faces:
            if x >= 0 and y >= 0 and w > 0 and h > 0:
                roi = image[y:y+h, x:x+w]
                if roi.size > 0:
                    image[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (99, 99), 30)
        return image
    except Exception as e:
        return image

# ========================
# GEMINI LOGIC
# ========================

STRICT_PROMPT = """
You are a food safety AI. Analyze this image for these SPECIFIC categories ONLY:
1. Rodent
2. Insects
3. Hair Strands
4. Rotten Food
5. Mold / Fungal Growth
6. Burnt Food
7. Unhygienic Environment
8. Hygiene (Only use if image is clean/safe)
9. Dog
10. Cat

CRITICAL RULES FOR FALSE POSITIVES:
- Ignore walls, floor tiles, concrete, granite, and background textures. Do NOT identify them as Mold.
- Only identify Mold/Fungus if it is on FOOD or ORGANIC matter.
- Ignore reflections on stainless steel surfaces.
- Return valid JSON only.
- For every detection (except Hygiene), provide a "bounding_box" [ymin, xmin, ymax, xmax] (0-1000 scale).
- If multiple items exist, list them all.
- If the image is safe, return "name": "Hygiene".

JSON Format:
{
  "detections": [
    {"name": "Rodent", "score": 0.95, "box_2d": [100, 200, 300, 400]}
  ]
}
"""

def analyze_image_with_gemini(image_bytes):
    if not gemini_model: 
        print("Error: Model not initialized.")
        return {"detections": []}
    
    try:
        response = gemini_model.generate_content(
            [STRICT_PROMPT, {"mime_type": "image/jpeg", "data": image_bytes}],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini Analysis Error: {e}")
        return {"detections": []}

def process_gemini_result(result, w, h):
    processed = []
    raw_dets = result.get("detections", [])

    for det in raw_dets:
        name = det.get("name", "Unknown")
        score = det.get("score", 0.0)
        
        info = categorizer.categorize(name, score)
        if not info: 
            if "hygiene" in name.lower() or "clean" in name.lower(): continue 
            continue 

        # --- FALSE POSITIVE CHECK ---
        # If it detects Mold, enforce a stricter confidence threshold
        if info["category"] == "Mold / Fungal Growth" and score < CONFIG.MOLD_MIN_CONFIDENCE:
            print(f"Skipped low confidence Mold detection: {score}")
            continue
        # ----------------------------

        box = None
        if "box_2d" in det:
            ymin, xmin, ymax, xmax = det["box_2d"]
            x = int((xmin / 1000) * w)
            y = int((ymin / 1000) * h)
            bw = int(((xmax - xmin) / 1000) * w)
            bh = int(((ymax - ymin) / 1000) * h)
            box = (x, y, bw, bh)

        processed.append({
            "name": info["display_name"],
            "confidence": score,
            "box": box,
            "info": info
        })

    processed.sort(key=lambda x: x["confidence"], reverse=True)
    return processed[:5]

# ========================
# ROUTES
# ========================

@app.route("/")
def root(): return send_from_directory(BASE_DIR, "index.html")

@app.route("/styles.css")
def styles(): return send_from_directory(BASE_DIR, "styles.css")

@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "online",
        "model_status": MODEL_NAME,
        "server_time": datetime.now().isoformat()
    })

# ROUTE 1: File Upload (Standard)
@app.route("/api/predict_image", methods=["POST"])
def api_predict_image():
    file = request.files.get("image")
    if not file: return jsonify({"error": "No image"}), 400

    npimg = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    return process_and_respond(img)

# ROUTE 2: Webcam Capture (Receives Base64 from Client)
@app.route("/api/capture_frame", methods=["POST"])
def api_capture_frame():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"error": "No image data"}), 400

    try:
        # Decode Base64 string from JavaScript
        image_data = data['image'].split(',')[1] # Remove "data:image/jpeg;base64," header
        binary_data = base64.b64decode(image_data)
        np_arr = np.frombuffer(binary_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        return process_and_respond(img)
    except Exception as e:
        print(f"Capture Error: {e}")
        return jsonify({"error": "Failed to process capture"}), 500

def process_and_respond(img):
    """Shared logic for both upload and capture"""
    if img is None: return jsonify({"error": "Bad image"}), 400
    
    img = blur_faces(img)
    h, w = img.shape[:2]

    _, buf = cv2.imencode(".jpg", img)
    result_json = analyze_image_with_gemini(buf.tobytes())
    detections = process_gemini_result(result_json, w, h)

    annotated = img.copy()
    max_threat = 0
    predictions = []
    
    for d in detections:
        visualizer.draw_detection_box(annotated, d["box"], d["name"], d["confidence"], d["info"]["category"])
        predictions.append({
            "label": d["name"],
            "confidence": d["confidence"],
            "threat_level": d["info"]["threat_level"],
            "category": d["info"]["category"]
        })
        if d["info"]["threat_level"] > max_threat: max_threat = d["info"]["threat_level"]

    # NO FILE SAVING (cv2.imwrite Removed)
    # We strictly encode to Base64 to send back to the User.
    # Compression: Use 70% JPEG quality to save bandwidth and browser memory
    _, frame_buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    
    return jsonify({
        "predictions": predictions,
        "annotated_filename": None, 
        "frame_image": base64.b64encode(frame_buf).decode('utf-8'),
        "timestamp_iso": datetime.now().isoformat(),
        "total_detections": len(predictions)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
