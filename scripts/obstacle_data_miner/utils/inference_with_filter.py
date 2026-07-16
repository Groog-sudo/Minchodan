import argparse

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(
        description="2-Stage Inference: Indoor/Outdoor Classifier -> Object Detector"
    )
    parser.add_argument("--img", type=str, required=True, help="Path to input image")
    parser.add_argument(
        "--cls_model",
        type=str,
        default="runs/classify/indoor_outdoor_cls/weights/best.pt",
        help="Path to classification model",
    )
    parser.add_argument(
        "--det_model", type=str, default="yolov8n.pt", help="Path to object detection model"
    )

    args = parser.parse_args()

    print(f"Loading Classifier: {args.cls_model}")
    try:
        cls_model = YOLO(args.cls_model)
    except Exception as e:
        print(f"[WARN] Could not load classifier: {e}")
        print("Please train the classifier first using train_classifier.py.")
        return

    print(f"Loading Object Detector: {args.det_model}")
    det_model = YOLO(args.det_model)

    # 1. Run Classification
    print("\n--- Step 1: Environment Classification ---")
    cls_results = cls_model(args.img, verbose=False)

    # YOLO classification output logic
    top1_idx = cls_results[0].probs.top1
    env_class = cls_results[0].names[top1_idx]
    confidence = float(cls_results[0].probs.top1conf)

    print(f"Environment Detected: {env_class.upper()} (Confidence: {confidence:.2f})")

    # 2. Run Object Detection
    print("\n--- Step 2: Object Detection with Filter ---")
    det_results = det_model(args.img, verbose=False)

    # Outdoor specific classes that should be ignored if environment is indoor
    # (These should match your config.py classes)
    outdoor_only_classes = [
        "traffic_light",
        "traffic_light_controller",
        "traffic_sign",
        "tree_trunk",
        "pole",
        "bollard",
        "parking_meter",
        "car",
        "bus",
        "truck",
        "motorcycle",
        "scooter",
        "bicycle",
        "barricade",
    ]

    boxes = det_results[0].boxes
    names = det_results[0].names

    filtered_detections = []
    dropped_detections = []

    for box in boxes:
        cls_id = int(box.cls[0])
        class_name = names[cls_id]
        conf = float(box.conf[0])

        # Filtering logic
        if env_class == "indoor" and class_name in outdoor_only_classes:
            dropped_detections.append((class_name, conf))
        else:
            filtered_detections.append((class_name, conf))

    print(f"Total Raw Detections: {len(boxes)}")
    print(f"Filtered Detections (Accepted): {len(filtered_detections)}")
    for obj, conf in filtered_detections:
        print(f"  [+] {obj} ({conf:.2f})")

    print(f"\nDropped Detections (False Positive Prevention): {len(dropped_detections)}")
    for obj, conf in dropped_detections:
        print(f"  [-] {obj} ({conf:.2f}) -> Dropped because environment is INDOOR")


if __name__ == "__main__":
    main()
