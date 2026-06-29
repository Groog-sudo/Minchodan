import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os

import imagehash
from dotenv import load_dotenv
from PIL import Image

load_dotenv()


def filter_duplicates(image_paths: list, threshold: int = 5) -> list:
    """
    pHash (Perceptual Hash) 값을 비교하여 유사도가 해밍 거리 임계값(threshold) 이하인
    중복되거나 매우 유사한 프레임을 필터링합니다.

    Args:
        image_paths: 입력 이미지 파일 경로 리스트
        threshold: 중복 여부를 결정할 해밍 거리 임계값

    Returns:
        중복이 제거된 고유 이미지 파일 경로 리스트
    """
    if not image_paths:
        return []

    unique_paths = []
    hashes = []

    for path in image_paths:
        if not os.path.exists(path):
            continue

        try:
            # PIL Image로 로드하여 방어적으로 가드 처리
            with Image.open(path) as img:
                img_hash = imagehash.phash(img)
        except Exception as e:
            # 디코딩 불량 프레임 등은 예외 처리하고 무시
            print(f"[Dedup] 이미지 로드 또는 해시 계산 오류 ({path}): {e}")
            continue

        # 기존 고유 이미지들의 해시값과 비교
        is_duplicate = False
        for h in hashes:
            if (img_hash - h) <= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_paths.append(path)
            hashes.append(img_hash)

    return unique_paths


if __name__ == "__main__":
    print("dedup_phash.py 스모크 테스트 실행")

    # [DUMMY DATA] 설명: 테스트용 임시 이미지 경로 / 주의: PIL을 사용하여 중복 이미지와 고유 이미지를 테스트용으로 생성합니다.
    import numpy as np

    img1_path = "smoke_img1.jpg"
    img2_path = "smoke_img2.jpg"
    img3_path = "smoke_img3.jpg"

    # 완전히 동일한 이미지 2개, 다른 이미지 1개 생성
    data1 = np.zeros((100, 100, 3), dtype=np.uint8)
    data1[:, :] = [0, 255, 0]  # 초록색

    data3 = np.zeros((100, 100, 3), dtype=np.uint8)
    data3[:, :] = [0, 0, 255]  # 빨간색

    Image.fromarray(data1).save(img1_path)
    Image.fromarray(data1).save(img2_path)  # img1의 완전 복사본
    Image.fromarray(data3).save(img3_path)  # 완전히 다른 이미지

    test_paths = [img1_path, img2_path, img3_path]

    try:
        filtered = filter_duplicates(test_paths, threshold=5)
        print(f"중복 제거 결과: {len(test_paths)}개 중 {len(filtered)}개 남음.")
        for f in filtered:
            print(f"- {f}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        for p in test_paths:
            if os.path.exists(p):
                os.remove(p)
