# utils.py
import os
import cv2
import numpy as np
from datetime import datetime

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def draw_labelled_box(frame, box, label, prob=None, color=(0,255,0), thickness=2):
    """
    Draw rectangle and label on frame.
    box = (x, y, w, h)
    """
    x, y, w, h = box
    cv2.rectangle(frame, (x,y), (x+w, y+h), color, thickness)
    text = f"{label}"
    if prob is not None:
        text += f" {prob*100:.1f}%"
    # put background for text
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    cv2.rectangle(frame, (x, y-20), (x+tw+6, y), color, -1)
    cv2.putText(frame, text, (x+3, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 1, cv2.LINE_AA)

def save_snapshot(frame, label, out_dir="snapshots"):
    """
    Save snapshot to out_dir with timestamp and label in filename.
    """
    ensure_dir(out_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{ts}_{label}.jpg"
    path = os.path.join(out_dir, filename)
    # write with reasonable JPEG quality
    cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return path

def preprocess_roi(roi, target_size=(224,224)):
    """
    Convert BGR ROI (OpenCV) to RGB float32 image scaled to [0,255]
    Returns numpy array shape (1, H, W, 3).
    """
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    roi_resized = cv2.resize(roi_rgb, target_size, interpolation=cv2.INTER_AREA)
    arr = np.asarray(roi_resized).astype('float32')
    return np.expand_dims(arr, axis=0)