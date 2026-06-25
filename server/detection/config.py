# -*- coding: utf-8 -*-
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

YOLO_CONF = float(os.getenv("YOLO_CONF", "0.35"))
FRAME_SIZE = int(os.getenv("FRAME_SIZE", "640"))
REFLEX_FPS = int(os.getenv("REFLEX_FPS", "10"))
COGNITIVE_FPS = int(os.getenv("COGNITIVE_FPS", "2"))
YOLO26N_OBJECT_DET = os.getenv(
    "YOLO26N_OBJECT_DET", os.path.join("server", "models", "yolo26n", "object_detection.pt")
)
YOLO26N_SEG = os.getenv(
    "YOLO26N_SEG", os.path.join("server", "models", "yolo26n", "segmentation.pt")
)


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(project_root, path)


def get_yolo_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_detector():
    from server.detection.detector_interface import DetectorInterface
    from server.detection.mock_detector import MockDetector
    from server.detection.yolo_detector import YoloDetector

    weights_path = resolve_path(YOLO26N_OBJECT_DET)
    if os.path.exists(weights_path):
        detector: DetectorInterface = YoloDetector(
            weights_path=weights_path,
            conf=YOLO_CONF,
            device=get_yolo_device(),
        )
        if detector.load():
            logger.info(f"[config] YoloDetector 로드 성공: {weights_path}")
            return detector
        logger.warning("[config] YoloDetector 로드 실패, MockDetector로 평백")
    else:
        logger.warning(f"[config] 가중치 없음: {weights_path}, MockDetector 사용")
    return MockDetector()


def get_segmentor():
    from server.detection.detector_interface import SegmentorInterface
    from server.detection.mock_detector import MockSegmentor
    from server.detection.yolo_segmentor import YoloSegmentor

    weights_path = resolve_path(YOLO26N_SEG)
    if os.path.exists(weights_path):
        segmentor: SegmentorInterface = YoloSegmentor(
            weights_path=weights_path,
            conf=YOLO_CONF,
            device=get_yolo_device(),
        )
        if segmentor.load():
            logger.info(f"[config] YoloSegmentor 로드 성공: {weights_path}")
            return segmentor
        logger.warning("[config] YoloSegmentor 로드 실패, MockSegmentor로 평백")
    else:
        logger.warning(f"[config] 가중치 없음: {weights_path}, MockSegmentor 사용")
    return MockSegmentor()
