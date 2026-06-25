# -*- coding: utf-8 -*-
import logging
import sys
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import numpy as np
from ultralytics import YOLO

from server.detection.detector_interface import DetectorInterface
from server.detection.schemas import BBox, Detection

logger = logging.getLogger(__name__)


class YoloDetector(DetectorInterface):
    """Yolo 26N - Object Detection 래퍼."""

    def __init__(self, weights_path: str, conf: float = 0.35, device: str = "cpu"):
        self.weights_path = weights_path
        self.conf = conf
        self.device = device
        self.model: YOLO | None = None

    def load(self) -> bool:
        try:
            self.model = YOLO(self.weights_path)
            logger.info(f"[YoloDetector] 모델 로드 성공: {self.weights_path}")
            return True
        except Exception as e:
            logger.error(f"[YoloDetector] 모델 로드 실패: {e}")
            self.model = None
            return False

    def predict(self, frame: np.ndarray) -> List[Detection]:
        if self.model is None:
            logger.warning("[YoloDetector] 모델이 로드되지 않았습니다.")
            return []

        try:
            results = self.model.track(
                source=frame,
                conf=self.conf,
                device=self.device,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False,
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and self.device != "cpu":
                logger.warning("[YoloDetector] CUDA OOM, CPU로 평백")
                self.device = "cpu"
                return self.predict(frame)
            logger.error(f"[YoloDetector] 추론 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"[YoloDetector] 추론 오류: {e}")
            return []

        result = results[0]
        detections: List[Detection] = []
        if result.boxes is None or len(result.boxes) == 0:
            return detections

        names = result.names
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = names.get(cls_id, str(cls_id))
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            track_id = None
            if box.id is not None:
                track_id = f"T-{int(box.id[0]):04d}"
            detections.append(
                Detection(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=BBox(x=x1, y=y1, w=x2 - x1, h=y2 - y1),
                    track_id=track_id,
                    speed=None,
                    direction=None,
                    risk=None,
                )
            )
        return detections
