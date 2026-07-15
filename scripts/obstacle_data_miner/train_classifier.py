import argparse

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(
        description="Train YOLO Image Classification Model (Indoor vs Outdoor)"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="datasets/classification",
        help="Path to classification dataset root",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolo11n-cls.pt",
        help="Base model to use (e.g., yolo11n-cls.pt, yolov8n-cls.pt, yolo26n-cls.pt)",
    )
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=224, help="Image size for classification")

    args = parser.parse_args()

    print(f"Starting classification training using base model: {args.model}")
    print(f"Dataset path: {args.data}")

    # Load a model
    model = YOLO(args.model)  # load a pretrained model

    # Train the model
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        project="runs/classify",
        name="indoor_outdoor_cls",
    )

    print("Training complete. Results saved to runs/classify/indoor_outdoor_cls")


if __name__ == "__main__":
    main()
