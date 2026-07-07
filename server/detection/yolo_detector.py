import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from ultralytics import YOLO

from server.detection.detector_interface import DetectorInterface
from server.detection.schemas import BBox, Detection

logger = logging.getLogger(__name__)


class YoloDetector(DetectorInterface):
    """Yolo 26N - Object Detection 래퍼."""

    def __init__(
        self,
        weights_path: str,
        conf: float = 0.35,
        device: str = "cpu",
        enable_tracking: bool = True,
    ):
        self.weights_path = weights_path
        self.conf = conf
        self.device = device
        self.enable_tracking = enable_tracking
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

    def predict(self, frame: np.ndarray) -> list[Detection]:
        # =========================================================================
        # 🤖 VIBE CODE 영역 (안전 폴백 및 예외 처리) 🤖
        # 💡 [설계 의도] GPU OOM(Out of Memory)이나 ByteTrack 의존성 에러 시
        # 서버가 죽지 않고 CPU나 기본 predict 모드로 폴백하도록 방어적 코딩을 적용했습니다.
        # =========================================================================
        if self.model is None:
            logger.warning("[YoloDetector] 모델이 로드되지 않았습니다.")
            return []

        if not self.enable_tracking:
            return self._predict_without_tracking(frame)

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
                logger.warning("[YoloDetector] CUDA OOM, CPU로 폴백")
                self.device = "cpu"
                return self.predict(frame)
            logger.error(f"[YoloDetector] 추론 오류: {e}")
            return []
        except Exception as e:
            if "lap" in str(e).lower():
                logger.warning("[YoloDetector] ByteTrack 의존성 없음, predict()로 폴백")
                results = self.model.predict(
                    source=frame,
                    conf=self.conf,
                    device=self.device,
                    verbose=False,
                )
            else:
                logger.error(f"[YoloDetector] 추론 오류: {e}")
                return []

        result = results[0]
        return self._parse_result(result)

    def _predict_without_tracking(self, frame: np.ndarray) -> list[Detection]:
        if self.model is None:
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
                logger.warning("[YoloDetector] CUDA OOM, CPU로 폴백")
                self.device = "cpu"
                return self._predict_without_tracking(frame)
            logger.error(f"[YoloDetector] 추론 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"[YoloDetector] 추론 오류: {e}")
            return []
        return self._parse_result(results[0])

    @staticmethod
    def _parse_result(result) -> list[Detection]:
        # =========================================================================
        # 👨‍💻 HARD CODE 영역 시작 (핵심 파싱 및 BBox 매핑) 👨‍💻
        # 💡 [면접 대비 주석]
        # 질문: YOLO 모델의 텐서 출력을 시스템 내부 포맷(Detection)으로 직접 파싱한 이유는?
        # 답변: 1. 텐서 값을 Python 기본 타입(float, int)으로 완전 캐스팅하여 JSON 직렬화 에러를 방지했습니다.
        #       2. ByteTrack이 반환하는 식별자를 'T-0001' 포맷으로 통일하여, 하위 파이프라인(위험도 게이트)에서
        #          동일 객체를 끊김 없이 추적하고 중복 알림을 억제할 수 있도록 식별 체계를 구축했습니다.
        # =========================================================================
        detections: list[Detection] = []
        if result.boxes is None or len(result.boxes) == 0:
            return detections

        names = result.names

        for box in result.boxes:
            # 1. 클래스 ID 와 이름 파싱 (Tensor -> int)
            cls_id = int(box.cls[0])
            class_name = names.get(cls_id, str(cls_id))

            # 2. 신뢰도(Confidence) 파싱
            confidence = float(box.conf[0])

            # 3. Bounding Box 좌표 파싱 (x1, y1, x2, y2)
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())

            # 4. ByteTrack 추적 ID mapping (T-0001 포맷)
            track_id = None
            if box.id is not None:
                track_id = f"T-{int(box.id[0]):04d}"

            # 5. DTO(Detection Objects)로 변환하여 리스트에 추가
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
