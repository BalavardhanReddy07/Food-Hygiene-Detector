# realtime.py
import cv2
import numpy as np
import tensorflow as tf
import os
from utils import preprocess_roi, draw_labelled_box, save_snapshot, ensure_dir
from datetime import datetime # Import for saving snapshots

# Config
MODEL_PATH = "models/insect_rat_model.keras"
INPUT_SIZE = (224, 224)

# --- YOUR REQUESTED CHANGES ---
CONFIDENCE_THRESHOLD = 0.60  # 60% - Only show a box if model is 60% confident
SNAPSHOT_CONFIDENCE = 0.80   # 80% - Only save snapshots if 80% confident
# --- END OF CHANGES ---

MIN_CONTOUR_AREA = 5000 
SNAPSHOT_DIR = "snapshots"
CLASS_FILE = os.path.join(os.path.dirname(MODEL_PATH) or '.', 'class_names.txt')

def load_model(path=MODEL_PATH):
    print(f"Loading model from {path} ...")
    try:
        model = tf.keras.models.load_model(path, safe_mode=False)
        print("Model loaded successfully.")
        return model
    except Exception as e:
        print(f"---!!! ERROR LOADING MODEL !!!---")
        print(f"Error: {e}")
        print(f"Please ensure '{MODEL_PATH}' exists.")
        print("Have you run 'python train.py' successfully?")
        print("-----------------------------------")
        return None

def load_class_names(path=CLASS_FILE, default=None):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            # Read names and convert to lowercase for robust matching
            names = [line.strip().lower() for line in f.readlines() if line.strip()]
            print(f"Loaded class names: {names}")
            return names
    print(f"Warning: Class names file not found at {path}")
    return default

def main():
    model = load_model()
    if model is None:
        return

    class_names = load_class_names(default=['hygienic', 'insects', 'rats'])
    if class_names is None:
        print("Error: class_names are not loaded. Exiting.")
        return
        
    # Find the 'hygienic' class name, default to 'hygienic' if not found
    # This is to make the logic robust
    hygienic_class_name = 'hygienic'
    for name in class_names:
        if 'hygi' in name:
            hygienic_class_name = name
            break
    print(f"Using '{hygienic_class_name}' as the non-pest class.")

    ensure_dir(SNAPSHOT_DIR)
    ensure_dir(os.path.join("dataset", "hygienic")) # For the 's' key

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check camera index.")

    backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)

    print("\n--- Starting webcam ---")
    print(f"Detecting classes: {class_names}")
    print(f"Confidence to show box: {CONFIDENCE_THRESHOLD*100}%")
    print(f"Confidence to save snapshot: {SNAPSHOT_CONFIDENCE*100}%")
    print("\n--- CONTROLS ---")
    print("Press 's' to save a 'hygienic' snapshot for re-training.")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        original = frame.copy()
        frame_small = frame.copy()
        fgmask = backSub.apply(frame_small)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=1)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_DILATE, kernel, iterations=2)

        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < MIN_CONTOUR_AREA:
                continue

            x,y,w,h = cv2.boundingRect(cnt)
            pad = 8
            x1 = max(0, x-pad); y1 = max(0, y-pad)
            x2 = min(frame_small.shape[1], x+w+pad); y2 = min(frame_small.shape[0], y+h+pad)

            roi = frame_small[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            # --- PREDICTION ---
            pred_label = None
            confidence = 0.0

            inp = preprocess_roi(roi, target_size=INPUT_SIZE)
            preds = model.predict(inp, verbose=0)
            
            # This logic handles your 3-class model
            if preds.shape[-1] > 1: 
                probs = preds.ravel()
                idx = int(np.argmax(probs))
                pred_label = class_names[idx] if idx < len(class_names) else 'Unknown'
                confidence = float(probs[idx])
            else:
                # Fallback for binary models
                prob = float(preds.ravel()[0])
                if prob >= 0.5:
                    pred_label = class_names[1]
                    confidence = prob
                else:
                    pred_label = class_names[0]
                    confidence = 1.0 - prob

            # --- LOGIC FOR BOXES AND SNAPSHOTS ---
            
            # Only proceed if confidence is above the *minimum* threshold (60%)
            if confidence >= CONFIDENCE_THRESHOLD:
                
                # --- THIS IS THE BUG FIX ---
                # We check if the label is NOT the hygienic class.
                # This is robust and future-proof.
                is_pest = (pred_label.lower() != hygienic_class_name)
                # --- END OF BUG FIX ---

                # 1. Determine Color
                if is_pest:
                    if 'rat' in pred_label.lower():
                        color = (0, 165, 255) # Orange (BGR)
                    else: # 'insect' or any other pest
                        color = (0, 0, 255) # Red (BGR)
                else:
                    color = (0, 255, 0) # Green (BGR)
                
                # 2. Check for Snapshot
                # Save snapshot only if it's a PEST and confidence is >= 80%
                if is_pest and confidence >= SNAPSHOT_CONFIDENCE:
                    snapshot = original.copy()
                    # Draw the box on the snapshot before saving
                    draw_labelled_box(snapshot, (x1, y1, x2-x1, y2-y1), pred_label.capitalize(), confidence, color=color)
                    saved_path = save_snapshot(snapshot, pred_label, out_dir=SNAPSHOT_DIR)
                    print(f"PEST DETECTED: Saved snapshot: {saved_path} (label={pred_label}, conf={confidence:.3f})")

                # 3. Draw Box on Live Video
                # Always draw if confidence is >= 60%
                draw_labelled_box(original, (x1, y1, x2-x1, y2-y1), pred_label.capitalize(), confidence, color=color)

        cv2.imshow("Mask", fgmask)
        cv2.imshow("Detections", original)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        
        # Press 's' to save a 'hygienic' snapshot for re-training
        if key == ord('s'):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"manual_save_{ts}.jpg"
            save_path = os.path.join("dataset", "hygienic", filename)
            cv2.imwrite(save_path, frame) # Save the *original* frame
            print(f"SAVED: Manual snapshot to {save_path}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()