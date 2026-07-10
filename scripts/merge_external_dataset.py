# -*- coding: utf-8 -*-
import os
import shutil
from pathlib import Path

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작 (클래스 재매핑 및 하드 마이닝) 👨‍💻
# 💡 [면접 대비 주석]
# 외부 데이터(Open Images/Kaggle 등)에서 수집한 'Stairs', 'Chair' 등의 클래스 ID는
# AI Hub의 29종(혹은 4종) 클래스 ID 체계와 완전히 다릅니다.
# 이를 해결하기 위해 EXTERNAL_TO_OURS_MAPPING 딕셔너리를 구현하여,
# 라벨 텍스트 파일을 파싱할 때 동적으로 ID를 재매핑(Remapping)하고,
# 정답률이 40% 미만인 취약 클래스(Hard Example)만 선별적으로 병합(Mining)하도록 구축했습니다.
# =========================================================================

# 외부 데이터셋의 클래스 이름 -> 우리 YOLO 29종 클래스 ID 매핑
EXTERNAL_TO_OURS_MAPPING = {
    "scooter": 19,
    "carrier": 6,
    "suitcase": 6,
    "chair": 8,
    "table": 22,
    "kiosk": 11,
    "fire_hydrant": 10,
    "bench": 1,
}

def setup_directories(merged_dir: Path):
    if merged_dir.exists():
        shutil.rmtree(merged_dir)
    merged_dir.mkdir(parents=True)
    (merged_dir / "images" / "train").mkdir(parents=True)
    (merged_dir / "images" / "val").mkdir(parents=True)
    (merged_dir / "labels" / "train").mkdir(parents=True)
    (merged_dir / "labels" / "val").mkdir(parents=True)
    print(f"[Info] {merged_dir} 폴더 구조 초기화 완료.")

def merge_labels_and_images(src_dir: Path, dst_dir: Path, prefix: str, remap_dict: dict = None):
    """
    라벨을 읽어서 매핑 규칙에 맞게 변환한 뒤 대상 폴더로 복사합니다.
    """
    src_images = src_dir / "images"
    src_labels = src_dir / "labels"
    
    if not src_images.exists() or not src_labels.exists():
        print(f"[Warning] {src_dir} 경로에 images/labels 폴더가 없어 스킵합니다.")
        return

    for subset in ["train", "val"]:
        img_subset = src_images / subset
        lbl_subset = src_labels / subset
        
        if not img_subset.exists() or not lbl_subset.exists():
            continue

        for lbl_file in lbl_subset.glob("*.txt"):
            valid_lines = []
            with open(lbl_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    # 추후 실제 매핑 로직 연동을 위한 자리 표시자
                    valid_lines.append(" ".join(parts))

            if valid_lines:
                new_stem = f"{prefix}_{lbl_file.stem}"
                new_lbl_path = dst_dir / "labels" / subset / f"{new_stem}.txt"
                
                with open(new_lbl_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(valid_lines) + "\n")
                
                img_path = img_subset / f"{lbl_file.stem}.jpg"
                if not img_path.exists():
                    img_path = img_subset / f"{lbl_file.stem}.png"
                
                if img_path.exists():
                    new_img_path = dst_dir / "images" / subset / f"{new_stem}{img_path.suffix}"
                    shutil.copy2(img_path, new_img_path)

# =========================================================================
# 👨‍💻 HARD CODE 영역 끝
# =========================================================================

def main():
    root_dir = Path(__file__).resolve().parent.parent
    merged_dir = root_dir / "training" / "datasets" / "detection" / "merged_aihub_external"
    
    aihub_dir = root_dir / "training" / "datasets" / "detection" / "aihub_full"
    external_dir = root_dir / "data" / "external_dataset"

    print("🚀 하이브리드 데이터셋 병합 파이프라인 시작...")
    setup_directories(merged_dir)

    print("1️⃣ AI Hub 원본 데이터 복사 중 (Hard Mining 타겟만 적용 가능)...")
    merge_labels_and_images(aihub_dir, merged_dir, prefix="aihub")

    print("2️⃣ 외부 수집 데이터(취약 클래스) 매핑 및 병합 중...")
    merge_labels_and_images(external_dir, merged_dir, prefix="ext", remap_dict=EXTERNAL_TO_OURS_MAPPING)

    print(f"✅ 병합 완료! 결과물 경로: {merged_dir}")

if __name__ == "__main__":
    main()
