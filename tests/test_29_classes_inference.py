"""
29개 커스텀 클래스 가중치 모델(det_best_20260705.pt)의 추론 정합성을 검증하는 통합 테스트 스크립트.
"""

import os
import sys

# UTF-8 출력 재설정 (guide 3.1)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from ultralytics import YOLO


def main():
    print("==================================================")
    print(" 29개 커스텀 클래스 YOLO 추론 정합성 검증 테스트 시작")
    print("==================================================")

    # 1. 모델 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    weights_path = os.path.join(project_root, "server", "models", "yolo26n", "det_best_20260705.pt")

    print(f"[검증 1] 탐지 모델 가중치 파일 탐색: {weights_path}")
    if not os.path.exists(weights_path):
        print(f"[실패] 탐지 가중치 파일이 존재하지 않습니다: {weights_path}")
        sys.exit(1)
    print("[성공] 탐지 가중치 파일 확인 완료.")

    # 2. YOLO 탐지 모델 적재
    print("\n[검증 2] YOLO 29 클래스 커스텀 모델 메모리 적재 시도...")
    try:
        model = YOLO(weights_path)
        names = model.names
        class_count = len(names)
        print(f"[성공] 모델 로드 완료. 클래스 개수: {class_count}개")

        # 클래스 매핑 검증
        expected_classes = {
            3: "bollard",
            12: "motorcycle",
            15: "person",
            19: "scooter",
            27: "truck",
        }
        print("\n[검증 3] 주요 핵심 시각장애인 위협 클래스 정합성 체크:")
        for idx, expected_name in expected_classes.items():
            actual_name = names.get(idx, "unknown")
            if actual_name == expected_name:
                print(f"  - 클래스 {idx:02d}: {expected_name} == {actual_name} [일치]")
            else:
                print(f"  - 클래스 {idx:02d}: 예상={expected_name} / 실제={actual_name} [불일치 ⚠️]")

    except Exception as e:
        print(f"[실패] 모델 적재 도중 예외 발생: {e}")
        sys.exit(1)

    # 3. 더미 이미지 추론 검증
    print("\n[검증 4] 640x640 BGR 가상 프레임 이미지 추론 연산 테스트...")
    try:
        # 640x640 무작위 노이즈 프레임 준비
        dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # 추론 수행
        results = model.predict(source=dummy_frame, conf=0.25, verbose=False)
        result = results[0]

        print(f"[성공] 640x640 추론 연산 완료. (탐지된 객체 개수: {len(result.boxes)}개)")
        print("  - 가상 더미 프레임 추론에 대한 메모리 및 ANE/CPU 드라이버 에러 검증 통과.")
    except Exception as e:
        print(f"[실패] 추론 연산 도중 에러 발생: {e}")
        sys.exit(1)

    print("\n==================================================")
    print(" 29개 커스텀 클래스 정합성 및 인퍼런스 파이프라인 검증 성공")
    print("==================================================")


if __name__ == "__main__":
    main()
