"""Visualize YOLO Object Detection and Segmentation labels overlaid on images."""

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import TARGET_CLASSES, SETTINGS
from seg_config import SEG_TARGET_CLASSES

def draw_yolo_bbox(image, label_path, class_names):
    h, w = image.shape[:2]
    if not label_path.exists():
        return image
        
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5: continue
            
            cls_id = int(parts[0])
            cx, cy, bw, bh = map(float, parts[1:5])
            
            x1 = int((cx - bw/2) * w)
            y1 = int((cy - bh/2) * h)
            x2 = int((cx + bw/2) * w)
            y2 = int((cy + bh/2) * h)
            
            name = class_names.get(cls_id, f"Class {cls_id}")
            
            # Draw bbox
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            # Text parameters
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.2
            thickness = 3
            
            # Get text size for background box
            (text_width, text_height), baseline = cv2.getTextSize(name, font, font_scale, thickness)
            
            # Draw solid background for text
            text_y = max(y1, text_height + 5)
            cv2.rectangle(image, (x1, text_y - text_height - 5), (x1 + text_width + 5, text_y + baseline), (0, 255, 0), -1)
            
            # Draw text in black over the green background
            cv2.putText(image, name, (x1 + 2, text_y), font, font_scale, (0, 0, 0), thickness)
            
    return image

def draw_yolo_seg(image, label_path, class_names):
    h, w = image.shape[:2]
    if not label_path.exists():
        return image
        
    overlay = image.copy()
    colors = {
        0: (255, 0, 0),    # sidewalk (blue)
        1: (0, 0, 255),    # caution (red)
        2: (128, 128, 128),# roadway (gray)
        3: (0, 255, 255),  # braille (yellow)
    }
    
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7: continue
            
            cls_id = int(parts[0])
            coords = list(map(float, parts[1:]))
            
            pts = []
            for i in range(0, len(coords), 2):
                pts.append([int(coords[i] * w), int(coords[i+1] * h)])
                
            pts = np.array(pts, np.int32)
            pts = pts.reshape((-1, 1, 2))
            
            color = colors.get(cls_id, (0, 255, 0))
            
            # Fill polygon
            cv2.fillPoly(overlay, [pts], color)
            # Draw outline
            cv2.polylines(image, [pts], True, color, 2)
            
            # Put label at first point
            name = class_names.get(cls_id, f"Class {cls_id}")
            cv2.putText(image, name, (pts[0][0][0], pts[0][0][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
    # Alpha blend
    return cv2.addWeighted(overlay, 0.4, image, 0.6, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["obj", "seg"], required=True)
    parser.add_argument("--count", type=int, default=5, help="Number of random samples to visualize")
    args = parser.parse_args()
    
    if args.mode == "obj":
        img_dir = SETTINGS.object_detection_root / "images"
        lbl_dir = SETTINGS.object_detection_root / "labels"
        classes = TARGET_CLASSES
        draw_fn = draw_yolo_bbox
    else:
        from seg_config import SEG_DATASET_ROOT
        img_dir = SEG_DATASET_ROOT / "images"
        lbl_dir = SEG_DATASET_ROOT / "labels"
        classes = SEG_TARGET_CLASSES
        draw_fn = draw_yolo_seg
        
    out_dir = Path("visualizations")
    out_dir.mkdir(exist_ok=True)
    
    images = list(img_dir.glob("aihub_*.jpg"))
    if not images:
        print(f"No AI Hub images found in {img_dir}")
        return
        
    random.shuffle(images)
    samples = images[:args.count]
    
    for img_path in samples:
        lbl_path = lbl_dir / f"{img_path.stem}.txt"
        img = cv2.imread(str(img_path))
        if img is None: continue
        
        drawn = draw_fn(img, lbl_path, classes)
        out_path = out_dir / f"viz_{img_path.name}"
        cv2.imwrite(str(out_path), drawn)
        print(f"Saved visualization: {out_path}")

if __name__ == "__main__":
    main()
