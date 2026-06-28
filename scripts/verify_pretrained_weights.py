import logging
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# PYTHONPATH 설정을 대신하여 프로젝트 루트를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.detection.config import get_detector, get_segmentor
from server.detection.yolo_detector import YoloDetector
from server.detection.yolo_segmentor import YoloSegmentor


def main():
    logger.info(
        "사전 학습된 Yolo 26N 가중치(Object Detection / Segmentation) 로드 및 추론 테스트를 시작합니다."
    )

    # 팩토리에서 가져오기
    detector = get_detector()
    segmentor = get_segmentor()

    logger.info(f"획득한 Detector 타입: {type(detector)}")
    logger.info(f"획득한 Segmentor 타입: {type(segmentor)}")

    # 타입 검증 (Mock이 아니라 실제 YoloDetector/YoloSegmentor 인지 확인)
    if not isinstance(detector, YoloDetector):
        logger.error("오류: 팩토리가 YoloDetector를 리턴하지 않았습니다.")
        sys.exit(1)
    if not isinstance(segmentor, YoloSegmentor):
        logger.error("오류: 팩토리가 YoloSegmentor를 리턴하지 않았습니다.")
        sys.exit(1)

    logger.info("팩토리로부터 실제 YOLO 모델 인스턴스 로딩 성공.")

    # 더미 프레임 생성 (640x640x3 BGR)
    frame = np.zeros((640, 640, 3), dtype=np.uint8)

    # 추론 테스트
    try:
        logger.info("Object Detection 추론을 실행합니다...")
        det_results = detector.predict(frame)
        logger.info(f"Detection 성공. 탐지 개수: {len(det_results)}")

        logger.info("Segmentation 추론을 실행합니다...")
        seg_results = segmentor.predict(frame)
        logger.info(f"Segmentation 성공. 분할 노면 개수: {len(seg_results)}")

        logger.info(
            "축하합니다! 사전 학습된 가중치를 이용한 실제 YOLO 모델 연산 환경 구축이 검증되었습니다."
        )
    except Exception as e:
        logger.error(f"추론 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
