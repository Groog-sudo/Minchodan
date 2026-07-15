import argparse
import shutil
import random
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Prepare YOLO Classification Dataset from Object Detection folders.")
    parser.add_argument("--indoor_dir", type=Path, default=Path("datasets/segmentation/indoor/images"), help="Path to indoor images")
    parser.add_argument("--outdoor_dir", type=Path, default=Path("datasets/object_detection/outdoor/images"), help="Path to outdoor images")
    parser.add_argument("--output_dir", type=Path, default=Path("datasets/classification"), help="Output classification dataset root")
    parser.add_argument("--split_ratio", type=float, default=0.8, help="Train ratio (default 0.8)")
    
    args = parser.parse_args()
    
    output_dir = args.output_dir
    train_dir = output_dir / "train"
    val_dir = output_dir / "val"
    
    # Create directory structure
    for env in ["indoor", "outdoor"]:
        (train_dir / env).mkdir(parents=True, exist_ok=True)
        (val_dir / env).mkdir(parents=True, exist_ok=True)

    def process_class(src_dir: Path, class_name: str):
        if not src_dir.exists():
            print(f"[WARN] Source directory not found: {src_dir}")
            return
            
        images = list(src_dir.glob("*.jpg"))
        if not images:
            print(f"[WARN] No images found in {src_dir}")
            return
            
        # Shuffle for random split
        random.seed(42)
        random.shuffle(images)
        
        split_idx = int(len(images) * args.split_ratio)
        train_imgs = images[:split_idx]
        val_imgs = images[split_idx:]
        
        # Copy files
        print(f"Copying {class_name} images... Train: {len(train_imgs)}, Val: {len(val_imgs)}")
        
        for img in train_imgs:
            shutil.copy(img, train_dir / class_name / img.name)
            
        for img in val_imgs:
            shutil.copy(img, val_dir / class_name / img.name)
            
    print("Preparing Indoor dataset...")
    process_class(args.indoor_dir, "indoor")
    
    print("Preparing Outdoor dataset...")
    process_class(args.outdoor_dir, "outdoor")
    
    print(f"Classification dataset successfully created at: {output_dir}")

if __name__ == "__main__":
    main()
