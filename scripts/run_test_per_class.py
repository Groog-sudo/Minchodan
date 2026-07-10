import os
import glob
import shutil
import random
from collections import defaultdict
from ultralytics import YOLO

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    val_images_dir = os.path.join(base_dir, "training", "datasets", "detection", "aihub_full", "images", "val")
    val_labels_dir = os.path.join(base_dir, "training", "datasets", "detection", "aihub_full", "labels", "val")
    
    out_dir = os.path.join(base_dir, "data", "test_100_samples")
    model_path = os.path.join(base_dir, "server", "models", "yolo26n", "object_detection.pt")
    
    AIHUB_CLASS_NAMES = [
        "barricade", "bench", "bicycle", "bollard", "bus", "car", "carrier", "cat",
        "chair", "dog", "fire_hydrant", "kiosk", "motorcycle", "movable_signage",
        "parking_meter", "person", "pole", "potted_plant", "power_controller",
        "scooter", "stop", "stroller", "table", "traffic_light", "traffic_light_controller",
        "traffic_sign", "tree_trunk", "truck", "wheelchair"
    ]
    
    print("라벨 파일을 스캔하여 클래스별 이미지를 분류합니다...")
    class_to_images = defaultdict(list)
    label_files = glob.glob(os.path.join(val_labels_dir, "*.txt"))
    
    for label_file in label_files:
        basename = os.path.splitext(os.path.basename(label_file))[0]
        img_path = os.path.join(val_images_dir, basename + ".jpg")
        if not os.path.exists(img_path):
            continue
            
        with open(label_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            classes_in_img = set()
            for line in lines:
                parts = line.strip().split()
                if parts:
                    cls_id = int(parts[0])
                    classes_in_img.add(cls_id)
            for cls_id in classes_in_img:
                class_to_images[cls_id].append(img_path)
                
    # 클래스별로 100개씩 추출하여 복사
    print("클래스당 최대 100개의 샘플 이미지를 추출합니다...")
    sampled_dict = {}
    for cls_id, img_list in class_to_images.items():
        if cls_id >= len(AIHUB_CLASS_NAMES):
            continue
        cls_name = AIHUB_CLASS_NAMES[cls_id]
        target_count = min(100, len(img_list))
        sampled = random.sample(img_list, target_count)
        sampled_dict[cls_name] = sampled
        
        cls_in_dir = os.path.join(out_dir, "input_images", f"{cls_id:02d}_{cls_name}")
        os.makedirs(cls_in_dir, exist_ok=True)
        
        for img in sampled:
            shutil.copy2(img, cls_in_dir)
            
    print(f"\n[{model_path}] 모델을 로드하여 각 클래스별 추론을 시작합니다...")
    model = YOLO(model_path)
    
    for cls_name in AIHUB_CLASS_NAMES:
        if cls_name not in sampled_dict:
            continue
        cls_id = AIHUB_CLASS_NAMES.index(cls_name)
        cls_in_dir = os.path.join(out_dir, "input_images", f"{cls_id:02d}_{cls_name}")
        cls_out_dir = os.path.join(out_dir, "results", f"{cls_id:02d}_{cls_name}")
        
        print(f"[{cls_name}] 클래스 추론 중... ({len(sampled_dict[cls_name])}장)")
        model.predict(
            source=cls_in_dir,
            save=True,
            save_txt=True,
            project=cls_out_dir,
            name="predict",
            exist_ok=True,
            conf=0.25,
            verbose=False
        )
    
    print("\n[성공] 29개 전체 클래스에 대한 테스트 셋 추출 및 추론 결과 저장이 완료되었습니다.")
    print(f"👉 확인 경로: {out_dir}")

if __name__ == "__main__":
    main()
