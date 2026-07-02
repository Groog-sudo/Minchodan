"""
segbest.pt 세그멘테이션 모델을 모바일 온디바이스용 TFLite 포맷으로 변환하는 스크립트.
"""

import os
import sys

# stdout UTF-8 인코딩 강제 설정 (AGENTS.md 규칙 5.1 준수)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from ultralytics import YOLO
except ImportError:
    print(
        "Error: ultralytics 라이브러리가 설치되어 있지 않습니다. requirements.txt를 확인해 주십시오."
    )
    sys.exit(1)


def main():
    # 실행 파일 경로 기준 상위 프로젝트 루트 탐색
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))

    model_path = os.path.join(project_root, "server", "models", "yolo26n", "segbest.pt")

    if not os.path.exists(model_path):
        print(f"Error: 모델 파일이 존재하지 않습니다: {model_path}")
        sys.exit(1)

    print(f"변환 대상 모델 경로: {model_path}")
    print(
        "TFLite 포맷으로 모델 변환(Export)을 시작합니다. 이 작업은 다소 시간이 소요될 수 있습니다..."
    )

    try:
        model = YOLO(model_path)
        # TFLite로 export (imgsz=640)
        exported_path = model.export(format="tflite", imgsz=640, int8=False)
        print(f"변환 완료! 생성된 모델 경로: {exported_path}")

    except Exception as e:
        print(f"모델 변환 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
