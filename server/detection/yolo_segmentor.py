import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

    def predict(self, frame: np.ndarray) -> list[SurfaceResult]:
        # =========================================================================
        # 🤖 VIBE CODE 영역 (세그멘테이션 추론 및 예외 처리) 🤖
        # 💡 [설계 의도] Segmentation은 Object Detection보다 연산량이 크므로 CUDA OOM 발생 확률이 높습니다.
        # 에러 발생 시 예외를 먹고 빈 결과를 반환하거나, CPU로 안전하게 폴백하여 파이프라인 영속성을 보장합니다.
        # =========================================================================
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
        surfaces: list[SurfaceResult] = []
        if result.masks is None or len(result.masks) == 0:
            return surfaces

        names = result.names
        for idx, mask in enumerate(result.masks):
            cls_id = int(result.boxes.cls[idx]) if result.boxes is not None else idx
            class_name = names.get(cls_id, str(cls_id))
            centroid = self._compute_centroid(mask.xy)
            polygon = self._extract_polygon(mask.xy)
            surfaces.append(
                SurfaceResult(
                    class_name=class_name,
                    mask=None,
                    centroid=centroid,
                    polygon=polygon,
                )
            )
        return surfaces

    @staticmethod
    def _extract_polygon(mask_xy) -> list[list[float]]:
        # =========================================================================
        # 🤖 VIBE CODE 영역 (폴리곤 좌표 변환) 🤖
        # 💡 [설계 의도] ultralytics mask.xy는 인스턴스당 폴리곤 1개를 numpy ndarray로 준다.
        # SurfaceResult.polygon(exclude=True, 서버 내부 전용)에 담기 위해 JSON 직렬화 가능한
        # list[list[float]]로만 변환한다. 이 필드는 어디로도 전송되지 않으므로 좌표를 압축하지
        # 않고 그대로 보존해 point-in-polygon 판정(surface_departure.py)의 정확도를 지킨다.
        # =========================================================================
        try:
            pts = np.concatenate(mask_xy, axis=0)
            return pts.tolist()
        except Exception:
            return []

    @staticmethod
    def _compute_centroid(mask_xy) -> list[float]:
        # =========================================================================
        # 👨‍💻 HARD CODE 영역 시작 (마스크 무게중심 계산 로직) 👨‍💻
        # 💡 [면접 대비 주석]
        # 질문: Segmentation 결과인 폴리곤 면적(Mask)을 SurfaceResult(점 데이터)로 단순화한 이유는?
        # 답변: 보도블럭이나 계단 등 노면 상태의 전체 폴리곤 좌표를 하위 시스템으로 넘기면 통신/직렬화 오버헤드가 큽니다.
        # 따라서 Numpy의 mean() 연산을 통해 다각형의 무게중심(Centroid) '단일 점 좌표(cx, cy)'로 압축 치환했습니다.
        # 이를 통해 2단계 게이트(Surface Gate)에서 점이 안전선(Threshold) 아래에 있는지만
        # O(1)에 가깝게 비교할 수 있어 극단적인 Low Latency를 달성했습니다.
        # =========================================================================
        try:
            pts = np.concatenate(mask_xy, axis=0)
            cx = float(np.mean(pts[:, 0]))
            cy = float(np.mean(pts[:, 1]))
            return [cx, cy]
        except Exception:
            return [0.0, 0.0]
