# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
from dotenv import load_dotenv
load_dotenv()


# 3단계 Yolo 26N - Object Detection & Segmentation 탐지 클래스명 단일 표준화 정의 (SSOT)
KICKBOARD = "kickboard"
BOLLARD = "bollard"
BRAILLE_DAMAGED = "braille_damaged"
STAIRS = "stairs"
CROSSWALK = "crosswalk"
MANHOLE = "manhole"
GRATING = "grating"

# 전체 표준 클래스 리스트 정의
ALL_CLASSES = [
    KICKBOARD,
    BOLLARD,
    BRAILLE_DAMAGED,
    STAIRS,
    CROSSWALK,
    MANHOLE,
    GRATING
]

if __name__ == "__main__":
    print("Minchodan RAG 라벨 SSOT 로딩 테스트 완료")
    print(f"등록된 전체 클래스 목록: {ALL_CLASSES}")
