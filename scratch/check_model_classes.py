import sys
from ultralytics import YOLO

def main():
    print("Checking object_detection.pt classes...")
    try:
        det_model = YOLO("server/models/yolo26n/object_detection.pt")
        print(f"Loaded successfully. Classes count: {len(det_model.names)}")
        print("Classes list:")
        print(det_model.names)
    except Exception as e:
        print(f"Failed to load det model: {e}")

    print("\nChecking segmentation.pt classes...")
    try:
        seg_model = YOLO("server/models/yolo26n/segmentation.pt")
        print(f"Loaded successfully. Classes count: {len(seg_model.names)}")
        print("Classes list:")
        print(seg_model.names)
    except Exception as e:
        print(f"Failed to load seg model: {e}")

if __name__ == "__main__":
    main()
