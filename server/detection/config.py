import logging
import os
import sys

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

YOLO_CONF = float(os.getenv("YOLO_CONF", "0.35"))
FRAME_SIZE = int(os.getenv("FRAME_SIZE", "640"))
REFLEX_FPS = int(os.getenv("REFLEX_FPS", "10"))
COGNITIVE_FPS = int(os.getenv("COGNITIVE_FPS", "2"))
DETECTOR_TYPE = os.getenv("DETECTOR_TYPE", "mock").strip().lower()
YOLO26N_OBJECT_DET = os.getenv(
    "YOLO26N_OBJECT_DET", os.path.join("server", "models", "yolo26n", "object_detection260714.pt")
)
YOLO26N_SEG = os.getenv("YOLO26N_SEG", os.path.join("server", "models", "yolo26n", "segmentation260714.pt"))


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(project_root, path)


def _resolve_existing_path(primary_path: str, fallback_paths: list[str]) -> str | None:
    candidates = [primary_path, *fallback_paths]
    for candidate in candidates:
        resolved = resolve_path(candidate)
        if os.path.exists(resolved):
            return resolved
    return None


def get_yolo_device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _should_use_mock() -> bool:
    """환경 변수 기준으로 Mock 모드 사용 여부를 결정한다."""
    if DETECTOR_TYPE == "mock":
        logger.info("[config] DETECTOR_TYPE=mock - MockDetector/MockSegmentor를 사용합니다.")
        return True
    if DETECTOR_TYPE != "yolo":
        logger.warning(
            f"[config] 알 수 없는 DETECTOR_TYPE='{DETECTOR_TYPE}'. 안전 폴백으로 mock을 사용합니다."
        )
        return True
    return False


def get_detector():
    from server.detection.detector_interface import DetectorInterface
    from server.detection.mock_detector import MockDetector
    from server.detection.yolo_detector import YoloDetector

    if _should_use_mock():
        return MockDetector()

    weights_path = _resolve_existing_path(
        YOLO26N_OBJECT_DET,
        [
            os.path.join("server", "models", "yolo26n", "object_detection.pt"),
        ],
    )
    if weights_path is None:
        logger.warning(
            "[config] Detector 가중치 없음: YOLO26N_OBJECT_DET 및 fallback 경로를 모두 확인했으나 "
            "실파일을 찾지 못했습니다. 폴백으로 MockDetector를 로드합니다."
        )
        return MockDetector()
    detector: DetectorInterface = YoloDetector(
        weights_path=weights_path,
        conf=float(os.getenv("YOLO_DET_CONF", "0.50")),
        device=get_yolo_device(),
    )
    if not detector.load():
        logger.warning(
            f"[config] YoloDetector 로드 실패: {weights_path}. 폴백으로 MockDetector를 로드합니다."
        )
        return MockDetector()
    logger.info(f"[config] YoloDetector 로드 성공: {weights_path}")
    return detector


def get_segmentor():
    from server.detection.detector_interface import SegmentorInterface
    from server.detection.mock_detector import MockSegmentor
    from server.detection.yolo_segmentor import YoloSegmentor

    if _should_use_mock():
        return MockSegmentor()

    weights_path = _resolve_existing_path(
        YOLO26N_SEG,
        [
            os.path.join("server", "models", "yolo26n", "segmentation.pt"),
        ],
    )
    if weights_path is None:
        logger.warning(
            "[config] Segmentor 가중치 없음: YOLO26N_SEG 및 fallback 경로를 모두 확인했으나 "
            "실파일을 찾지 못했습니다. 폴백으로 MockSegmentor를 로드합니다."
        )
        return MockSegmentor()
    segmentor: SegmentorInterface = YoloSegmentor(
        weights_path=weights_path,
        conf=YOLO_CONF,
        device=get_yolo_device(),
    )
    if not segmentor.load():
        logger.warning(
            f"[config] YoloSegmentor 로드 실패: {weights_path}. 폴백으로 MockSegmentor를 로드합니다."
        )
        return MockSegmentor()
    logger.info(f"[config] YoloSegmentor 로드 성공: {weights_path}")
    return segmentor
