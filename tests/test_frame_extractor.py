import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os

import cv2
import numpy as np
import pytest
from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.build.frame_extractor import extract_frames

load_dotenv()


def test_extract_frames_success(tmp_path):
    # 테스트용 임시 비디오 및 출력 디렉토리 경로 지정
    video_path = str(tmp_path / "test_video.mp4")
    output_dir = str(tmp_path / "output_frames")

    # 1. 2초짜리 (60프레임) 더미 비디오 동적 생성
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (100, 100))
    for _ in range(60):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    # 2. 1fps 속도로 프레임 추출 실행 (총 2개 프레임 예상)
    paths = extract_frames(video_path, output_dir, fps=1)

    assert len(paths) == 2
    for p in paths:
        assert os.path.exists(p)
        assert p.endswith(".jpg")


def test_extract_frames_file_not_found():
    # 존재하지 않는 비디오 경로 전달 시 FileNotFoundError 테스트
    with pytest.raises(FileNotFoundError):
        extract_frames("non_existent_video.mp4", "output_frames", fps=1)


def test_extract_frames_invalid_video(tmp_path):
    # 손상된 비디오 파일 전달 시 ValueError 테스트
    invalid_video_path = str(tmp_path / "broken_video.mp4")
    with open(invalid_video_path, "w") as f:
        f.write("This is not a video file.")

    with pytest.raises(ValueError):
        extract_frames(invalid_video_path, str(tmp_path / "output"), fps=1)
