"""Import AI Hub Object Detection data (JSON Bbox & CVAT XML) into local YOLO format."""

import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import CLASS_TO_ID, CLASS_ALIASES, SETTINGS
from utils.format_converter import HashIndex, xyxy_to_yolo, safe_image_open

def extract_label(raw_label: str) -> str | None:
    """Extract English label from AI Hub mixed Korean/English format or aliases."""
    raw_label = raw_label.lower().strip()
    
    # Direct match
    if raw_label in CLASS_TO_ID:
        return raw_label
    if raw_label in CLASS_ALIASES:
        return CLASS_ALIASES[raw_label]
        
    # Regex extract (e.g., "자동차 진입 억제용 말뚝 (bollard)_정상" -> "bollard")
    match = re.search(r'\(([a-z_]+)\)', raw_label)
    if match:
        extracted = match.group(1)
        if extracted in CLASS_TO_ID:
            return extracted
        if extracted in CLASS_ALIASES:
            return CLASS_ALIASES[extracted]
            
    # Hardcoded specific Korean mappings just in case
    ko_mappings = {
        "키오스크": "kiosk",
        "볼라드": "bollard",
        "입간판": "movable_signage",
        "신호등제어기": "traffic_light_controller",
        "전력제어기": "power_controller",
        "바리케이드": "barricade",
        "유모차": "stroller",
        "가로수": "tree_trunk",
        "오토바이": "motorcycle",
        "자전거": "bicycle",
        "신호등": "traffic_light",
        "표지판": "traffic_sign",
        "휠체어": "wheelchair",
        "트럭": "truck",
        "자동차": "car",
        "보행자": "person",
        "사람": "person"
    }
    
    for ko, en in ko_mappings.items():
        if ko in raw_label:
            return en
            
    return None

def process_aihub_json(json_path: Path, image_dir: Path, label_dir: Path, hash_index: HashIndex) -> int:
    """Process Type A JSON (dataSetSn=513 format)."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON {json_path.name}: {e}")
        return 0

    info = data.get("info", {})
    filename = info.get("filename") or data.get("images", {}).get("file_name")
    
    # Try different width/height locations
    width = info.get("width") or data.get("images", {}).get("width")
    height = info.get("height") or data.get("images", {}).get("height")
    
    if not filename or not width or not height:
        return 0

    annotations = data.get("annotations", [])
    yolo_lines = []

    for ann in annotations:
        if ann.get("annotation_type") != "bbox":
            continue
            
        raw_label = str(ann.get("label_name", ""))
        label = extract_label(raw_label)
        if not label:
            continue
            
        class_id = CLASS_TO_ID[label]
        ann_info = ann.get("annotation_info", [])
        if not ann_info or len(ann_info) == 0:
            continue
            
        bbox = ann_info[0] # [x, y, w, h]
        if len(bbox) != 4:
            continue
            
        x_min, y_min, w, h = bbox
        x_max = x_min + w
        y_max = y_min + h
        
        yolo_vals = xyxy_to_yolo(float(x_min), float(y_min), float(x_max), float(y_max), int(width), int(height))
        yolo_lines.append(f"{class_id} " + " ".join(f"{v:.6f}" for v in yolo_vals))

    if not yolo_lines:
        return 0

    # Locate image
    # AI Hub typically puts images in the same or adjacent directory
    img_candidates = [
        json_path.parent / filename,
        json_path.parent.parent / "images" / filename,
        json_path.parent.parent / "원천데이터" / filename,
    ]
    
    img_path = None
    for cand in img_candidates:
        if cand.exists():
            img_path = cand
            break
            
    # Also recursive search nearby if exact sibling isn't found
    if not img_path:
        found = list(json_path.parent.rglob(filename))
        if found:
            img_path = found[0]

    if not img_path or not img_path.exists():
        print(f"[WARN] Image {filename} not found for {json_path.name}")
        return 0

    output_stem = f"aihub_obj_{json_path.stem}"
    out_img = image_dir / f"{output_stem}.jpg"
    out_lbl = label_dir / f"{output_stem}.txt"

    with safe_image_open(img_path) as img:
        if img is None:
            return 0
        if hash_index.duplicate_source(img):
            return 0
        hash_index.add(img, str(out_img))
        shutil.copy(img_path, out_img)

    out_lbl.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
    return 1

def process_aihub_cvat_xml(xml_path: Path, image_dir: Path, label_dir: Path, hash_index: HashIndex) -> int:
    """Process Type B CVAT XML (dataSetSn=189 format)."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"[ERROR] Failed to read XML {xml_path.name}: {e}")
        return 0

    exported = 0
    for image_tag in root.findall(".//image"):
        filename = image_tag.get("name")
        width = int(image_tag.get("width", 0))
        height = int(image_tag.get("height", 0))
        
        if not filename or width == 0 or height == 0:
            continue

        yolo_lines = []
        for box in image_tag.findall("box"):
            raw_label = box.get("label", "")
            label = extract_label(raw_label)
            if not label:
                continue
                
            class_id = CLASS_TO_ID[label]
            xtl = float(box.get("xtl", 0))
            ytl = float(box.get("ytl", 0))
            xbr = float(box.get("xbr", 0))
            ybr = float(box.get("ybr", 0))
            
            yolo_vals = xyxy_to_yolo(xtl, ytl, xbr, ybr, width, height)
            yolo_lines.append(f"{class_id} " + " ".join(f"{v:.6f}" for v in yolo_vals))

        if not yolo_lines:
            continue

        # Locate image (CVAT XMLs usually reference images in a sibling folder)
        img_candidates = list(xml_path.parent.parent.rglob(filename))
        if not img_candidates:
            print(f"[WARN] Image {filename} not found for CVAT XML {xml_path.name}")
            continue
            
        img_path = img_candidates[0]
        
        output_stem = f"aihub_cvat_{Path(filename).stem}"
        out_img = image_dir / f"{output_stem}.jpg"
        out_lbl = label_dir / f"{output_stem}.txt"

        with safe_image_open(img_path) as img:
            if img is None:
                continue
            if hash_index.duplicate_source(img):
                continue
            hash_index.add(img, str(out_img))
            shutil.copy(img_path, out_img)

        out_lbl.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
        exported += 1

    return exported

def main() -> None:
    parser = argparse.ArgumentParser(description="Import AI Hub Object Detection Annotations.")
    parser.add_argument("input_dir", type=Path, help="Directory containing raw AI Hub JSON/XML and images")
    parser.add_argument("--output", type=Path, default=SETTINGS.object_detection_root, help="Output dataset root")
    parser.add_argument("--env", type=str, choices=["indoor", "outdoor", "mixed"], default="mixed", help="Environment tag to split the dataset folder")
    args = parser.parse_args()

    # Append environment to output path (e.g. datasets/object_detection/outdoor)
    env_output = args.output / args.env
    image_dir = env_output / "images"
    label_dir = env_output / "labels"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    hash_index = HashIndex(env_output / f"hash_index_aihub_objdet_{args.env}.json")
    exported = 0

    print(f"Scanning {args.input_dir} for Object Detection labels...")
    
    # Process CVAT XMLs first
    for xml_path in args.input_dir.rglob("*.xml"):
        print(f"Processing XML: {xml_path.name}")
        exported += process_aihub_cvat_xml(xml_path, image_dir, label_dir, hash_index)
        
    # Process AI Hub JSONs
    for json_path in args.input_dir.rglob("*.json"):
        print(f"Processing JSON: {json_path.name}")
        exported += process_aihub_json(json_path, image_dir, label_dir, hash_index)

    hash_index.save()
    print(f"Exported {exported} new images to {env_output}")

if __name__ == "__main__":
    main()
