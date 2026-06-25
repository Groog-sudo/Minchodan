# -*- coding: utf-8 -*-
import logging
import sys
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import numpy as np
from ultralytics import YOLO

from server.detection.detector_interface import SegmentorInterface
from server.detection.schemas import SurfaceResult

logger = logging.getLogger(__name__)


class YoloSegmentor(SegmentorInterface):
    """Yolo 26N - Segmentation 래퍼."""

    def __init__(self, weights_path: str, conf: float = 0.35, device: str = "cpu"):
        self.weights_path = weights_path
        self.conf = conf
        self.device = device
        self.model: YOLO | None = None

    def load(self) -> bool:
        try:
            self.model = YOLO(self.weights_path)
            logger.info(f"[YoloSegmentor] 모델 로드 성공: {self.weights_path}")
            return True
        except Exception as e:
            logger.error(f"[YoloSegmentor] 모델 로드 실패: {e}")
            self.model = None
            return False

    def predict(self, frame: np.ndarray) -> List[SurfaceResult]:
        if self.model is None:
            logger.warning("[YoloSegmentor] 모델이 로드되지 않았습니다.")
            return []

        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf,
                device=self.device,
                verbose=False,
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and self.device != "cpu":
                logger.warning("[YoloSegmentor] CUDA OOM, CPU로 평백")
                self.device = "cpu"
                return self.predict(frame)
            logger.error(f"[YoloSegmentor] 추론 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"[YoloSegmentor] 추론 오류: {e}")
            return []

        result = results[0]
        surfaces: List[SurfaceResult] = []
        if result.masks is None or len(result.masks) == 0:
            return surfaces

        names = result.names
        for idx, mask in enumerate(result.masks):
            cls_id = int(result.boxes.cls[idx]) if result.boxes is not None else idx
            class_name = names.get(cls_id, str(cls_id))
            centroid = self._compute_centroid(mask.xy)
            surfaces.append(
                SurfaceResult(
                    class_name=class_name,
                    mask=None,
                    centroid=centroid,
                )
            )
        return surfaces

    @staticmethod
    def _compute_centroid(mask_xy) -> List[float]:
        try:
            pts = np.concatenate(mask_xy, axis=0)
            cx = float(np.mean(pts[:, 0]))
            cy = float(np.mean(pts[:, 1]))
            return [cx, cy]
        except Exception:
            return [0.0, 0.0]
