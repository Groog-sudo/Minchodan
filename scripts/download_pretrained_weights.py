# -*- coding: utf-8 -*-
import os
import sys
import urllib.request
import logging

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def download_file(url: str, dest_path: str):
    logger.info(f"다운로드 중: {url} -> {dest_path}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        logger.info(f"다운로드 완료: {dest_path}")
    except Exception as e:
        logger.error(f"다운로드 실패: {e}")
        raise

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # 저장 경로 설정
    models_dir = os.path.join(project_root, "server", "models", "yolo26n")
    os.makedirs(models_dir, exist_ok=True)
    
    det_weights_url = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
    seg_weights_url = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-seg.pt"
    
    det_dest = os.path.join(models_dir, "object_detection.pt")
    seg_dest = os.path.join(models_dir, "segmentation.pt")
    
    logger.info("사전 학습된 YOLOv8 모델 가중치 다운로드를 시작합니다.")
    
    try:
        download_file(det_weights_url, det_dest)
        download_file(seg_weights_url, seg_dest)
        logger.info("모든 가중치 파일이 성공적으로 준비되었습니다.")
    except Exception as e:
        logger.error(f"가중치 준비 중 오류가 발생했습니다: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
