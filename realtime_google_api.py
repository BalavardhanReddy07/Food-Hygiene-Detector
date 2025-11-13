# realtime_api_v3_focused.py
import cv2
import io
import time
import threading
from queue import Queue, Empty
from typing import Tuple

from google.cloud import vision

# ------------------ CONFIG (LOGIC FOCUSED) ------------------

# 1. CONTAMINANTS: We ONLY care about these objects.
UNHYGIENIC_KEYWORDS = {
    "Rat", "Ratlike", "Rodent", "Mouse", "Cockroach", "Fly", "Insect",
    "Garbage", "Trash", "Litter", "Waste", "Rubbish",
    "Spoiled food", "Expired food", # Specific "bad food"
    "Hair", "Hair strand",
    "Spill", "Stain"
}

# 2. CONTEXT: We can check if these are present (optional logic)
FOOD_KEYWORDS = {
    "Food", "Meal", "Dish", "Plate", "Bowl", "Kitchen"
}

# NOTE: "Human", "Chair", "Table", etc. are NOT in either list
# and will be 100% IGNORED.

# Confidence thresholds
OBJ_CONF_THRESHOLD = 0.45      # Only check objects above this confidence

# Rate limiting
API_CALL_INTERVAL_SECONDS = 1.5  # seconds between API calls

# Frame preprocessing
SEND_WIDTH = 640   # width to resize prior to sending to API
MAX_QUEUE_SIZE = 2

# ------------------ VISUALS ------------------
FONT = cv2.FONT_HERSHEY_SIMPLEX
STATUS_POS = (10, 30)
STATUS_SCALE = 0.9
STATUS_THICKNESS = 2

# ------------------ UTILS ------------------
def scale_box_from_normalized(norm_vertices, img_w, img_h) -> Tuple[int,int,int,int]:
    """Convert normalized API vertices to an (x, y, w, h) bounding box."""
    xs = [v.x for v in norm_vertices]
    ys = [v.y for v in norm_vertices]
    min_x = max(int(min(xs) * img_w), 0)
    min_y = max(int(min(ys) * img_h), 0)
    max_x = min(int(max(xs) * img_w), img_w - 1)
    max_y = min(int(max(ys) * img_h), img_h - 1)
    return (min_x, min_y, max_x - min_x, max_y - min_y)

def draw_labelled_box(img, box, label, prob=None, color=(0,0,255)):
    """Draws a labeled box on the image."""
    x, y, w, h = box
    cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
    text = f"{label}"
    if prob is not None:
        text += f" {prob*100:.1f}%"
    (tw, th), baseline = cv2.getTextSize(text, FONT, 0.6, 1)
    cv2.rectangle(img, (x, y - th - baseline - 6), (x + tw + 6, y), color, -1)
    cv2.putText(img, text, (x + 3, y - 6), FONT, 0.6, (0,0,0), 1, cv2.LINE_AA)

# ------------------ WORKER THREAD ------------------
class VisionWorker(threading.Thread):
    """
    Sends API requests in a separate thread to keep the webcam feed smooth.
    This version ONLY calls object_localization.
    """
    def __init__(self, client: vision.ImageAnnotatorClient, request_queue: Queue, result_queue: Queue):
        super().__init__(daemon=True)
        self.client = client
        self.req_q = request_queue
        self.res_q = result_queue
        self.running = True

    def run(self):
        while self.running:
            try:
                payload = self.req_q.get(timeout=0.5)
            except Empty:
                continue
            if payload is None:
                break # Shutdown signal
            
            frame_bytes, meta = payload
            try:
                image = vision.Image(content=frame_bytes)
                
                # We ONLY call object_localization. No more "Label" detection.
                response_objects = self.client.object_localization(image=image)
                
                if getattr(response_objects, "error", None) and response_objects.error.message:
                    print(f"[VisionWorker] Object localization error: {response_objects.error.message}")
                    localized_annotations = []
                else:
                    localized_annotations = response_objects.localized_object_annotations

                out = {
                    "timestamp": meta.get("timestamp"),
                    "objects": localized_annotations,
                }
            except Exception as e:
                print(f"[VisionWorker] Exception calling Vision API: {e}")
                out = {"timestamp": meta.get("timestamp"), "objects": []}

            try:
                self.res_q.put_nowait(out)
            except:
                pass # Queue full, drop old result

    def stop(self):
        self.running = False
        try:
            self.req_q.put_nowait(None)
        except:
            pass

# ------------------ MAIN ------------------
def main():
    print("Starting Focused Hygiene Detector (Google Vision API)...")
    try:
        client = vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"Failed to create Vision client. Ensure GOOGLE_APPLICATION_CREDENTIALS is set.\nError: {e}")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open camera index 0.")
        return

    req_q = Queue(maxsize=MAX_QUEUE_SIZE)
    res_q = Queue(maxsize=MAX_QUEUE_SIZE)
    worker = VisionWorker(client, req_q, res_q)
    worker.start()

    last_api_time = 0.0
    last_result = {"timestamp": 0, "objects": []}

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Frame capture failed; exiting.")
                break

            display = frame.copy()
            h, w = display.shape[:2]
            now = time.time()

            # --- Send frame to worker (rate-limited) ---
            if (now - last_api_time) >= API_CALL_INTERVAL_SECONDS:
                scale = SEND_WIDTH / float(w)
                if scale < 1.0:
                    small = cv2.resize(frame, (SEND_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
                else:
                    small = frame.copy()
                is_success, buf = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if is_success:
                    try:
                        req_q.put_nowait((buf.tobytes(), {"timestamp": now}))
                        last_api_time = now
                    except:
                        pass # Queue full

            # --- Get latest result ---
            try:
                candidate = res_q.get_nowait()
                last_result = candidate
            except Empty:
                pass # No new result, just re-use the last one

            # ---------- NEW FOCUSED LOGIC ----------
            
            # 1. Assume hygienic until a CONTAMINANT is found
            scene_is_hygienic = True
            
            objects_to_draw = [] # Store contaminants here
            
            objects = last_result.get("objects", []) if last_result else []
            for obj in objects:
                try:
                    obj_name = getattr(obj, "name", "")
                    obj_score = getattr(obj, "score", 0.0)
                    if obj_score < OBJ_CONF_THRESHOLD:
                        continue # Ignore low-confidence detections

                    # 2. Check if the object is a known contaminant
                    if obj_name in UNHYGIENIC_KEYWORDS:
                        scene_is_hygienic = False # We found a pest!
                        
                        # Save the box details to draw later
                        verts = obj.bounding_poly.normalized_vertices
                        box = scale_box_from_normalized(verts, w, h)
                        objects_to_draw.append((box, obj_name, obj_score))
                    
                    # 3. IF obj_name is "Human", "Chair", "Food", etc.,
                    # it is NOT in UNHYGIENIC_KEYWORDS, so we do nothing.
                    # It is completely and safely ignored.

                except Exception as ex:
                    print("Error processing object:", ex)
                    continue
            
            # --- Draw Results ---
            
            # 4. Draw all the contaminant boxes we found
            for box, name, score in objects_to_draw:
                draw_labelled_box(display, box, f"UNHYGIENIC: {name}", prob=score, color=(0,0,255))

            # 5. Draw overall status
            if scene_is_hygienic:
                status_text = "Status: Hygienic"
                status_color = (0, 255, 0) # Green
            else:
                status_text = "Status: UNHYGIENIC DETECTED"
                status_color = (0, 0, 255) # Red

            cv2.putText(display, status_text, STATUS_POS, FONT, STATUS_SCALE, status_color, STATUS_THICKNESS, cv2.LINE_AA)

            cv2.imshow("Hygiene Detector (Focused API)", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        # shutdown
        print("Shutting down worker...")
        worker.stop()
        worker.join(timeout=2.0)
        cap.release()
        cv2.destroyAllWindows()
        print("Exit.")

if __name__ == "__main__":
    main()