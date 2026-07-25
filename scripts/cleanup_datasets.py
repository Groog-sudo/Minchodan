import os
import glob
import shutil

def keep_samples(directory, extensions, num_samples=10):
    if not os.path.exists(directory):
        return
    
    for ext in extensions:
        files = sorted(glob.glob(os.path.join(directory, f"**/*{ext}"), recursive=True))
        if len(files) > num_samples:
            files_to_delete = files[num_samples:]
            for f in files_to_delete:
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Error removing {f}: {e}")
            print(f"Deleted {len(files_to_delete)} {ext} files in {directory}")

def main():
    print("Starting dataset cleanup...")

    # Data directories
    data_dirs = [
        "data/raw",
        "data/frames",
        "data/test_100_samples/results"
    ]
    for d in data_dirs:
        keep_samples(d, ['.jpg', '.png', '.jpeg', '.json'], 10)

    # Training directories
    training_dirs = [
        "training/datasets/detection/aihub_0820_26",
        "training/datasets/detection/aihub_finetune",
        "training/datasets/detection/aihub_full",
        "training/datasets/segmentation/aihub_0820_26",
        "training/datasets/segmentation/aihub_finetune"
    ]
    
    for d in training_dirs:
        keep_samples(os.path.join(d, "images"), ['.jpg', '.png', '.jpeg'], 10)
        keep_samples(os.path.join(d, "labels"), ['.txt'], 10)
        keep_samples(os.path.join(d, "masks"), ['.png', '.jpg'], 10)
        keep_samples(os.path.join(d, "raw"), ['.jpg', '.png'], 10)
        
    # Runs directories
    last_pts = glob.glob("training/runs/**/weights/last*.pt", recursive=True)
    for pt in last_pts:
        try:
            os.remove(pt)
            print(f"Deleted {pt}")
        except Exception as e:
            print(f"Error removing {pt}: {e}")
            
    print("Cleanup completed.")

if __name__ == "__main__":
    main()
