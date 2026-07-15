import glob
import os
import random
import shutil

from ultralytics import YOLO


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    val_dir = os.path.join(
        base_dir, "training", "datasets", "detection", "aihub_full", "images", "val"
    )
    out_dir = os.path.join(base_dir, "data", "test_100_samples")
    model_path = os.path.join(base_dir, "server", "models", "yolo26n", "object_detection.pt")

    # 1. Collect all images in val_dir
    all_images = glob.glob(os.path.join(val_dir, "*.jpg"))
    if len(all_images) == 0:
        print(f"No images found in {val_dir}")
        return

    # 2. Select 100 random images
    num_samples = min(100, len(all_images))
    sampled_images = random.sample(all_images, num_samples)

    # 3. Create input dir and copy sampled images
    temp_in_dir = os.path.join(out_dir, "input_images")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(temp_in_dir, exist_ok=True)

    print(f"Copying {num_samples} random images to {temp_in_dir}...")
    for img_path in sampled_images:
        shutil.copy2(img_path, temp_in_dir)

    # 4. Run YOLO prediction
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)

    print("Running inference and drawing bounding boxes...")
    # This will save annotated images to out_dir/results
    model.predict(
        source=temp_in_dir,
        save=True,
        save_txt=True,
        save_conf=True,
        project=out_dir,
        name="results",
        exist_ok=True,
        conf=0.25,  # 기본 임계치 설정
    )

    print("\n[성공] 100개 샘플 테스트 완료!")
    print(f"👉 원본 이미지: {temp_in_dir}")
    print(f"👉 예측 완료된 이미지(박스 쳐진 사진): {os.path.join(out_dir, 'results')}")


if __name__ == "__main__":
    main()
