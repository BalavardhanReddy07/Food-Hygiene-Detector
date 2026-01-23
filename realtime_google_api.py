import cv2
import numpy as np
from dataclasses import dataclass

@dataclass
class DetectionConfig:
    # Confidence Thresholds
    OBJECT_CONFIDENCE: float = 0.40
    LABEL_CONFIDENCE: float = 0.40
    
    # Visual Configuration
    HAIR_MIN_CONFIDENCE: float = 0.60
    # NEW: Higher threshold to prevent walls being detected as Mold
    MOLD_MIN_CONFIDENCE: float = 0.70
    
    # Color Analysis Thresholds (HSV)
    MOLD_HUE_RANGE: tuple = ((35, 30, 30), (95, 255, 255))
    DECAY_HUE_RANGE: tuple = ((8, 40, 15), (35, 255, 130))
    BURNT_RANGE: tuple = ((0, 0, 0), (30, 100, 80))
    
    ANOMALY_THRESHOLD: float = 0.08

CONFIG = DetectionConfig()

class ColorPalette:
    """Optimized color system"""
    CRITICAL = (0, 0, 255)      # Red
    HIGH = (0, 100, 255)        # Orange
    MEDIUM = (0, 200, 255)      # Yellow
    SAFE = (0, 255, 0)          # Green
    HAIR = (235, 206, 135)      # Sky Blue (BGR Format)
    
    @staticmethod
    def get_threat_color(category: str) -> tuple:
        cat = category.upper()
        if "HAIR" in cat: return ColorPalette.HAIR
        # Critical threats now include Rodents, Insects, Dog, and Cat
        if any(x in cat for x in ["RODENT", "INSECTS", "DOG", "CAT"]): return ColorPalette.CRITICAL
        if any(x in cat for x in ["ROTTEN", "MOLD", "BURNT"]): return ColorPalette.HIGH
        if "UNHYGIENIC" in cat: return ColorPalette.MEDIUM
        return ColorPalette.SAFE

class ThreatCategorizer:
    """
    STRICT CATEGORIZATION:
    1. Rodent, 2. Insects, 3. Hair Strands, 4. Rotten Food, 
    5. Mold / Fungal Growth, 6. Burnt Food, 7. Unhygienic, 8. Hygiene, 9.Dog, 10.Cat
    """
    
    @staticmethod
    def categorize(name: str, score: float) -> dict:
        name_lower = name.lower()
        
        # 1. Rodent
        if any(x in name_lower for x in ["rat", "mouse", "rodent", "mice", "droppings"]):
            return {"category": "Rodent", "threat_level": 5, "display_name": "Rodent"}
            
        # 2. Insects
        if any(x in name_lower for x in ["cockroach", "roach", "fly", "ant", "insect", "bug", "maggot", "worm", "pest"]):
            return {"category": "Insects", "threat_level": 5, "display_name": "Insects"}
            
        # 3. Hair Strands
        if any(x in name_lower for x in ["hair", "strand", "fiber", "fur"]):
            return {"category": "Hair Strands", "threat_level": 4, "display_name": "Hair Strands"}
            
        # 4. Rotten Food
        if any(x in name_lower for x in ["rotten", "spoiled", "decay", "decomposed", "putrid"]):
            return {"category": "Rotten Food", "threat_level": 4, "display_name": "Rotten Food"}
            
        # 5. Mold / Fungal
        if any(x in name_lower for x in ["mold", "fungus", "mildew", "spore", "growth"]):
            return {"category": "Mold / Fungal Growth", "threat_level": 4, "display_name": "Mold"}
            
        # 6. Burnt Food
        if any(x in name_lower for x in ["burnt", "charred", "blackened", "carbonized"]):
            return {"category": "Burnt Food", "threat_level": 4, "display_name": "Burnt Food"}
            
        # 7. Unhygienic
        if any(x in name_lower for x in ["dirty", "unclean", "grime", "messy", "stain", "spill", "trash", "garbage", "waste"]):
            return {"category": "Unhygienic", "threat_level": 3, "display_name": "Unhygienic"}
        # 9. Dog
        if any(x in name_lower for x in ["dog", "puppy", "canine"]):
            return {"category": "Dog", "threat_level": 2, "display_name": "Dog"}
        # 10. Cat
        if any(x in name_lower for x in ["cat", "kitten"]):
            return {"category": "Cat", "threat_level": 2, "display_name": "Cat"}

class Visualizer:
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    
    @staticmethod
    def draw_detection_box(img: np.ndarray, box: tuple, label: str, confidence: float, category: str):
        """Draws bounding box. SKIPS drawing if category is Hygiene/Clean"""
        if category.lower() in ["hygiene", "clean"] or box is None:
            return
            
        x, y, w, h = box
        color = ColorPalette.get_threat_color(category)
        
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        
        # Label background
        label_text = f"{category} ({int(confidence*100)}%)"
        (tw, th), _ = cv2.getTextSize(label_text, Visualizer.FONT, 0.6, 1)
        cv2.rectangle(img, (x, y - 25), (x + tw + 10, y), color, -1)
        cv2.putText(img, label_text, (x + 5, y - 5), Visualizer.FONT, 0.6, (255, 255, 255), 1)

    @staticmethod
    def draw_status_panel(img: np.ndarray, detections: list, analysis: dict):
        """Draws status on live feed"""
        if not detections:
            status, color = "HYGIENE", ColorPalette.SAFE
        else:
            max_threat = max(d["info"]["threat_level"] for d in detections)
            if max_threat >= 5: status, color = "CRITICAL", ColorPalette.CRITICAL
            elif max_threat >= 4: status, color = "HIGH RISK", ColorPalette.HIGH
            elif max_threat >= 3: status, color = "WARNING", ColorPalette.MEDIUM
            else: status, color = "NOTICE", ColorPalette.MEDIUM

        overlay = img.copy()
        cv2.rectangle(overlay, (10, 10), (220, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)
        cv2.putText(img, status, (20, 40), Visualizer.FONT, 1.0, color, 2)

class DetectionAnalyzer:
    @staticmethod
    def analyze_color_anomalies(roi: np.ndarray) -> dict:
        """Helper for color based anomalies (Mold/Burnt)"""
        if roi.size == 0: return {}
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        mold_mask = cv2.inRange(hsv, np.array(CONFIG.MOLD_HUE_RANGE[0]), np.array(CONFIG.MOLD_HUE_RANGE[1]))
        burnt_mask = cv2.inRange(hsv, np.array(CONFIG.BURNT_RANGE[0]), np.array(CONFIG.BURNT_RANGE[1]))
        
        total = roi.shape[0] * roi.shape[1]
        mold_ratio = np.count_nonzero(mold_mask) / total
        burnt_ratio = np.count_nonzero(burnt_mask) / total
        
        if mold_ratio > CONFIG.ANOMALY_THRESHOLD:
            return {"type": "Mold / Fungal Growth", "score": mold_ratio, "mask": mold_mask}
        if burnt_ratio > CONFIG.ANOMALY_THRESHOLD:
            return {"type": "Burnt Food", "score": burnt_ratio, "mask": burnt_mask}
            
        return {}

# Export components
__all__ = ['CONFIG', 'ThreatCategorizer', 'Visualizer', 'DetectionAnalyzer', 'ColorPalette']