import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from dotenv import load_dotenv
from PIL import Image

# 로컬 모듈 임포트
from server.rag.build.dedup_phash import filter_duplicates

load_dotenv()


def test_filter_duplicates(tmp_path):
    img1_path = str(tmp_path / "img1.jpg")
    img2_path = str(tmp_path / "img2.jpg")
    img3_path = str(tmp_path / "img3.jpg")

    # 1. 초록색 이미지 2개 생성 (서로 동일한 pHash)
    data_green = np.zeros((100, 100, 3), dtype=np.uint8)
    data_green[:, :] = [0, 255, 0]
    Image.fromarray(data_green).save(img1_path)
    Image.fromarray(data_green).save(img2_path)

    # 2. 대각선 줄무늬가 있는 파란색 이미지 1개 생성 (다른 pHash)
    data_blue = np.zeros((100, 100, 3), dtype=np.uint8)
    data_blue[:, :] = [255, 0, 0]
    for idx in range(100):
        data_blue[idx, idx] = [0, 0, 255]  # 노이즈 추가하여 해시 확실하게 다르게 함
    Image.fromarray(data_blue).save(img3_path)

    test_paths = [img1_path, img2_path, img3_path]

    # 중복 제거 수행 (임계값 5)
    filtered = filter_duplicates(test_paths, threshold=5)

    # 3. 2개의 고유 이미지만 반환되어야 함
    assert len(filtered) == 2
    assert img1_path in filtered
    assert img3_path in filtered
    assert img2_path not in filtered


def test_filter_duplicates_empty():
    # 빈 리스트 주입 시 에러 없이 빈 리스트 반환 검증
    assert filter_duplicates([]) == []


def test_filter_duplicates_missing_files():
    # 존재하지 않는 파일 패스 전달 시 제외 처리 검증
    assert filter_duplicates(["non_existent.jpg"]) == []
