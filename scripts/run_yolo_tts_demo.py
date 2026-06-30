# -*- coding: utf-8 -*-
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2

from server.detection.direction import (
    bbox_area_ratio,
    estimate_direction,
    estimate_distance,
)
from server.detection.risk_rules import build_message_hint, estimate_risk_level
from server.detection.yolo_detector import YoloDetector


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_INPUT = Path("data") / "raw" / "aihub_walk_sample"
DEFAULT_MODEL = Path("server") / "models" / "yolo26n" / "object_detection.pt"
DEFAULT_OUTPUT_DIR = Path("outputs") / "yolo_tts_demo"
RISK_ORDER = {"high": 3, "medium": 2, "low": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="샘플 이미지에 YOLO 추론을 실행하고 단말 TTS용 message_hint JSON을 생성합니다."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="이미지 파일 또는 이미지 폴더 경로입니다.",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
        help="YOLO Object Detection weight 경로입니다.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="결과 JSON 저장 폴더입니다.",
    )
    parser.add_argument("--conf", type=float, default=0.35, help="YOLO confidence threshold")
    parser.add_argument("--device", default="cpu", help="YOLO 실행 장치입니다. 예: cpu, cuda:0")
    return parser.parse_args()


def project_root() -> Path:
    return PROJECT_ROOT


def resolve_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute():
        return path
    return project_root() / path


def collect_images(input_path: Path) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() in IMAGE_EXTENSIONS:
        return [input_path]
    if not input_path.exists() or not input_path.is_dir():
        raise FileNotFoundError(f"입력 이미지 경로를 찾을 수 없습니다: {input_path}")
    return sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def bbox_xyxy(detection) -> list[float]:
    bbox = detection.bbox
    return [
        round(bbox.x, 2),
        round(bbox.y, 2),
        round(bbox.x + bbox.w, 2),
        round(bbox.y + bbox.h, 2),
    ]


def detection_to_record(detection, frame_width: int, frame_height: int) -> dict[str, Any]:
    distance = estimate_distance(detection.bbox, frame_width, frame_height, detection.class_name)
    direction = estimate_direction(detection.bbox, frame_width, distance)
    risk_level = estimate_risk_level(detection.class_name, direction, distance)
    message_hint = build_message_hint(detection, direction, distance, risk_level)
    return {
        "class_name": detection.class_name,
        "confidence": round(float(detection.confidence), 4),
        "bbox": bbox_xyxy(detection),
        "direction": direction,
        "distance": distance,
        "area_ratio": round(
            bbox_area_ratio(detection.bbox, frame_width, frame_height),
            5,
        ),
        "risk_level": risk_level,
        "message_hint": message_hint,
    }


def choose_tts_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return sorted(
        records,
        key=lambda item: (
            RISK_ORDER.get(item["risk_level"], 0),
            item["area_ratio"],
            item["confidence"],
        ),
        reverse=True,
    )[0]


def run_image(detector: YoloDetector, image_path: Path, frame_index: int) -> dict[str, Any]:
    frame = cv2.imread(str(image_path))
    if frame is None:
        return {
            "frame_id": f"frame_{frame_index:06d}",
            "source": image_path.name,
            "error": "이미지 디코딩 실패",
            "detections": [],
            "tts": {"enabled": False, "text": ""},
        }

    frame_height, frame_width = frame.shape[:2]
    started = time.perf_counter()
    detections = detector.predict(frame)
    inference_ms = (time.perf_counter() - started) * 1000
    records = [
        detection_to_record(detection, frame_width, frame_height)
        for detection in detections
    ]
    tts_record = choose_tts_record(records)
    message_hint = tts_record["message_hint"] if tts_record else None

    return {
        "frame_id": f"frame_{frame_index:06d}",
        "source": image_path.name,
        "width": frame_width,
        "height": frame_height,
        "inference_ms": round(inference_ms, 2),
        "detections": records,
        "tts": {
            "enabled": message_hint is not None,
            "text": message_hint["text"] if message_hint else "",
            "message_hint": message_hint,
        },
    }


def write_outputs(results: list[dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "yolo_tts_demo_results.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def main() -> None:
    args = parse_args()
    input_path = resolve_path(args.input)
    model_path = resolve_path(args.model)
    output_dir = resolve_path(args.output_dir)

    if not model_path.exists():
        raise FileNotFoundError(f"YOLO weight 파일을 찾을 수 없습니다: {model_path}")

    image_paths = collect_images(input_path)
    if not image_paths:
        raise FileNotFoundError(f"입력 이미지가 없습니다: {input_path}")

    detector = YoloDetector(
        str(model_path),
        conf=args.conf,
        device=args.device,
        enable_tracking=False,
    )
    if not detector.load():
        raise RuntimeError(f"YOLO 모델 로드 실패: {model_path}")

    results = [
        run_image(detector, image_path, index + 1)
        for index, image_path in enumerate(image_paths)
    ]
    output_path = write_outputs(results, output_dir)

    print(f"입력 이미지 수: {len(image_paths)}")
    print(f"결과 JSON: {output_path}")
    for result in results:
        print(
            f"{result['source']} | detections={len(result['detections'])} | "
            f"tts={result['tts']['text']}"
        )


if __name__ == "__main__":
    main()
