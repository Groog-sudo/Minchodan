# -*- coding: utf-8 -*-
import argparse
import os
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LABEL_MAP = {
    "sidewalk": 0,               # sidewalk_normal
    "caution_zone": 1,           # caution (횡단보도 포함)
    "roadway": 2,                # roadway
    "alley": 2,                  # roadway
    "bike_lane": 2,              # roadway
    "braille_guide_blocks": 3    # braille_normal
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Hub 서피스마스킹 XML을 YOLO Segmentation 포맷으로 변환합니다.")
    parser.add_argument("--input-dir", required=True, help="서피스마스킹 최상위 폴더 경로 (예: C:\\...\\서피스마스킹)")
    parser.add_argument("--output-dir", required=True, help="결과 저장 폴더 (예: training/datasets/segmentation/aihub_0820_26)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation 셋 비율 (기본: 0.1)")
    parser.add_argument("--max-images", type=int, default=0, help="변환할 최대 이미지 수 (0: 전체)")
    return parser.parse_args()


def process_xml(xml_path: Path) -> list[tuple[str, int, int, list[dict]]]:
    """XML을 파싱하여 (이미지 파일명, width, height, [폴리곤들...]) 리스트 반환"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML {xml_path}: {e}")
        return []

    data = []
    for image in root.findall("image"):
        img_name = image.get("name")
        width = int(image.get("width"))
        height = int(image.get("height"))
        
        polygons = []
        for poly in image.findall("polygon"):
            label = poly.get("label")
            points_str = poly.get("points")
            if not label or not points_str:
                continue
            
            if label not in LABEL_MAP:
                continue
                
            class_id = LABEL_MAP[label]
            
            # points_str: "x1,y1;x2,y2;..."
            points = []
            for pt in points_str.split(";"):
                if not pt.strip():
                    continue
                x, y = map(float, pt.split(","))
                # YOLO 포맷을 위한 정규화 (0~1)
                norm_x = max(0.0, min(1.0, x / width))
                norm_y = max(0.0, min(1.0, y / height))
                points.extend([norm_x, norm_y])
                
            if points:
                polygons.append({"class_id": class_id, "points": points})
                
        # 폴리곤이 하나라도 있으면 추가
        if polygons:
            data.append((img_name, width, height, polygons))
            
    return data

def main():
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    
    # 작업 경로는 프로젝트 루트 기준
    project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
    output_dir = project_root / args.output_dir
    
    # 출력 폴더 생성
    img_train_dir = output_dir / "images" / "train"
    img_val_dir = output_dir / "images" / "val"
    lbl_train_dir = output_dir / "labels" / "train"
    lbl_val_dir = output_dir / "labels" / "val"
    
    for d in [img_train_dir, img_val_dir, lbl_train_dir, lbl_val_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    xml_files = list(input_dir.rglob("*.xml"))
    print(f"Found {len(xml_files)} XML files.")
    
    all_image_data = []
    for xml_path in xml_files:
        parsed_data = process_xml(xml_path)
        # 이미지 파일이 XML과 같은 폴더에 있다고 가정
        xml_parent = xml_path.parent
        for img_name, w, h, polygons in parsed_data:
            img_src = xml_parent / img_name
            if img_src.exists():
                all_image_data.append((img_src, polygons))
                
    print(f"Found {len(all_image_data)} valid images with annotations.")
    
    if args.max_images > 0:
        all_image_data = all_image_data[:args.max_images]
        print(f"Limiting to {args.max_images} images as requested.")
        
    # 셔플 및 분할
    random.seed(42)
    random.shuffle(all_image_data)
    
    val_count = int(len(all_image_data) * args.val_ratio)
    train_count = len(all_image_data) - val_count
    
    train_data = all_image_data[:train_count]
    val_data = all_image_data[train_count:]
    
    def copy_and_convert(data, split_name, img_dir, lbl_dir):
        print(f"Processing {split_name} set ({len(data)} images)...")
        for idx, (img_src, polygons) in enumerate(data):
            # 복사 (Hard Link 선호, 실패 시 Copy)
            img_dst = img_dir / img_src.name
            if not img_dst.exists():
                try:
                    os.link(img_src, img_dst)
                except OSError:
                    shutil.copy2(img_src, img_dst)
            
            # 라벨 작성
            lbl_dst = lbl_dir / f"{img_src.stem}.txt"
            with open(lbl_dst, "w", encoding="utf-8") as f:
                for poly in polygons:
                    points_str = " ".join(f"{v:.6f}" for v in poly["points"])
                    f.write(f"{poly['class_id']} {points_str}\n")
                    
            if (idx + 1) % 100 == 0:
                print(f"  [{idx + 1}/{len(data)}] processed.")

    copy_and_convert(train_data, "train", img_train_dir, lbl_train_dir)
    copy_and_convert(val_data, "val", img_val_dir, lbl_val_dir)
    
    print("Dataset conversion completed.")
    print(f"Train images: {len(train_data)}")
    print(f"Val images: {len(val_data)}")

if __name__ == "__main__":
    main()
