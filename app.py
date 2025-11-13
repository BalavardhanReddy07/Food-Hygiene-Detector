import os
import cv2
import time
import threading
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import numpy as np
import tensorflow as tf
from utils import preprocess_roi, ensure_dir

HAS_CORS = False
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    pass

USE_YOLO = True
try:
    from ultralytics import YOLO
except ImportError:
    USE_YOLO = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_KERAS = os.path.join(BASE_DIR, 'models', 'insect_rat_model.keras')
MODEL_YOLO = os.path.join(BASE_DIR, 'runs', 'train', 'pest_detector_v1', 'weights', 'best.pt')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
SNAPSHOT_DIR = os.path.join(BASE_DIR, 'snapshots')

ensure_dir(SNAPSHOT_DIR)
ensure_dir(STATIC_DIR)
ensure_dir(TEMPLATES_DIR)

CONFIDENCE_THRESHOLD = 0.6
INPUT_SIZE = (224, 224)

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if HAS_CORS:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

model_yolo = None
model_keras = None
model_names = ['hygienic', 'insects', 'ratimages']
model_status = "Initializing..."
models_loaded = False
webcam_available = False
cap = None

def init_webcam():
    global cap, webcam_available
    try:
        cap = cv2.VideoCapture(0)
        if cap and cap.isOpened():
            ret, _ = cap.read()
            if ret:
                webcam_available = True
                return True
        cap = None
        webcam_available = False
        return False
    except:
        cap = None
        webcam_available = False
        return False

def load_models():
    global model_yolo, model_keras, model_names, model_status, models_loaded
    if USE_YOLO:
        try:
            if os.path.exists(MODEL_YOLO):
                model_yolo = YOLO(MODEL_YOLO)
                try:
                    model_names = list(model_yolo.names.values()) if hasattr(model_yolo.names, 'values') else model_yolo.names
                except:
                    pass
                model_status = "YOLO Ready"
                models_loaded = True
                return
        except:
            pass
    
    if os.path.exists(MODEL_KERAS):
        try:
            model_keras = tf.keras.models.load_model(MODEL_KERAS, safe_mode=False)
            class_file = os.path.join(os.path.dirname(MODEL_KERAS), 'class_names.txt')
            if os.path.exists(class_file):
                with open(class_file, 'r', encoding='utf-8') as f:
                    model_names = [line.strip() for line in f.readlines() if line.strip()]
            model_status = "Keras Ready"
            models_loaded = True
            return
        except:
            pass
    
    model_status = "No models available"
    models_loaded = False

loader_thread = threading.Thread(target=load_models, daemon=True)
loader_thread.start()
init_webcam()

def gen_frames():
    while True:
        if not webcam_available or cap is None or not cap.isOpened():
            time.sleep(0.5)
            continue
        try:
            success, frame = cap.read()
            if not success:
                continue
            annotated = frame.copy()
            if model_yolo is not None:
                try:
                    results = model_yolo(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                                conf = float(box.conf[0].cpu().numpy())
                                cls_id = int(box.cls[0].cpu().numpy())
                                label = model_yolo.names[cls_id]
                                color = (0, 255, 0) if 'hygi' in label.lower() else (0, 0, 255)
                                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                                cv2.putText(annotated, f"{label} {conf*100:.1f}%", (x1, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                except:
                    pass
            elif model_keras is not None:
                try:
                    h, w = frame.shape[:2]
                    resized = cv2.resize(frame, INPUT_SIZE)
                    inp = preprocess_roi(resized, target_size=INPUT_SIZE)
                    preds = model_keras.predict(inp, verbose=0)
                    if preds.shape[-1] > 1:
                        idx = int(np.argmax(preds.ravel()))
                        conf = float(preds.ravel()[idx])
                        label = model_names[idx] if idx < len(model_names) else str(idx)
                    else:
                        prob = float(preds.ravel()[0])
                        label = model_names[1] if prob >= 0.5 else model_names[0]
                        conf = prob if label == model_names[1] else (1.0 - prob)
                    color = (0, 255, 0) if 'hygi' in label.lower() else (0, 0, 255)
                    cv2.putText(annotated, f"{label} {conf*100:.1f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                except:
                    pass
            ret, buffer = cv2.imencode('.jpg', annotated)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except:
            time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'models_loaded': models_loaded,
        'model_status': model_status,
        'model_type': 'YOLO' if model_yolo else ('Keras' if model_keras else 'None'),
        'classes': model_names,
        'webcam_available': webcam_available,
        'confidence_threshold': CONFIDENCE_THRESHOLD
    })

@app.route('/video_feed')
def video_feed():
    if not webcam_available:
        return jsonify({'error': 'Webcam not available'}), 503
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/predict_image', methods=['POST'])
def api_predict_image():
    if not models_loaded:
        return jsonify({'error': 'Models loading'}), 503
    file = request.files.get('image')
    if not file:
        return jsonify({'error': 'No image'}), 400
    try:
        data = file.read()
        npimg = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'Invalid image'}), 400
        annotated = img.copy()
        predictions = []
        if model_yolo is not None:
            try:
                results = model_yolo(img, conf=CONFIDENCE_THRESHOLD, verbose=False)
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                            conf = float(box.conf[0].cpu().numpy())
                            cls_id = int(box.cls[0].cpu().numpy())
                            label = model_yolo.names[cls_id]
                            color = (0, 255, 0) if 'hygi' in label.lower() else (0, 0, 255)
                            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(annotated, f"{label} {conf*100:.1f}%", (x1, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            predictions.append({'label': label, 'confidence': float(conf), 'box': [int(x1), int(y1), int(x2-x1), int(y2-y1)]})
            except:
                pass
        elif model_keras is not None:
            try:
                h, w = img.shape[:2]
                resized = cv2.resize(img, INPUT_SIZE)
                inp = preprocess_roi(resized, target_size=INPUT_SIZE)
                preds = model_keras.predict(inp, verbose=0)
                if preds.shape[-1] > 1:
                    idx = int(np.argmax(preds.ravel()))
                    conf = float(preds.ravel()[idx])
                    label = model_names[idx] if idx < len(model_names) else str(idx)
                else:
                    prob = float(preds.ravel()[0])
                    label = model_names[1] if prob >= 0.5 else model_names[0]
                    conf = prob if label == model_names[1] else (1.0 - prob)
                color = (0, 255, 0) if 'hygi' in label.lower() else (0, 0, 255)
                cv2.putText(annotated, f"{label} {conf*100:.1f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                predictions.append({'label': label, 'confidence': float(conf), 'box': [0, 0, int(w), int(h)]})
            except:
                pass
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(SNAPSHOT_DIR, f"pred_{timestamp}.jpg")
        cv2.imwrite(output_path, annotated)
        return jsonify({'predictions': predictions, 'annotated_filename': os.path.basename(output_path), 'image_size': [int(img.shape[1]), int(img.shape[0])]})
    except Exception as e:
        return jsonify({'error': str(e)[:100]}), 500

@app.route('/snapshots/<path:filename>')
def get_snapshot(filename):
    try:
        return send_from_directory(SNAPSHOT_DIR, filename)
    except:
        return jsonify({'error': 'Not found'}), 404

@app.route('/static/<path:filename>')
def get_static(filename):
    try:
        return send_from_directory(STATIC_DIR, filename)
    except:
        return jsonify({'error': 'Not found'}), 404

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG, threaded=True)
