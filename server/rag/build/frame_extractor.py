import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os

import cv2
from dotenv import load_dotenv

load_dotenv()


def extract_frames(video_path: str, output_dir: str, fps: int = 1) -> list:
    """
    비디오 파일에서 지정된 fps 간격으로 프레임을 추출하여 디스크에 JPEG 파일로 저장합니다.

    Args:
        video_path: 입력 비디오 파일 경로
        output_dir: 프레임 저장 디렉토리 경로
        fps: 초당 프레임 수

    Returns:
        추출된 프레임 이미지 파일 경로 리스트

    Raises:
        FileNotFoundError: 비디오 파일이 없을 경우 발생
        ValueError: 비디오 디코딩 실패 시 발생 (비협상 가드)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"입력 비디오 파일이 존재하지 않습니다: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"비디오 파일을 열거나 디코딩할 수 없습니다: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        video_fps = 30.0  # 기본값 백업

    frame_interval = round(video_fps / fps)
    if frame_interval <= 0:
        frame_interval = 1

    extracted_paths = []
    frame_count = 0
    saved_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                out_path = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
                # 프레임 버퍼가 None인지 방어적 가드 처리
                if frame is not None:
                    cv2.imwrite(out_path, frame)
                    extracted_paths.append(out_path)
                    saved_count += 1

            frame_count += 1
    finally:
        cap.release()

    if not extracted_paths:
        raise ValueError("추출된 프레임이 없습니다. 비디오 디코딩 문제를 확인하세요.")

    return extracted_paths


if __name__ == "__main__":
    print("frame_extractor.py 스모크 테스트 실행")

    # [DUMMY DATA] 설명: 테스트용 임시 비디오 경로 / 주의: OpenCV를 이용해 1초짜리 가짜 동영상을 동적으로 생성합니다.
    test_video = "temp_smoke_video.mp4"
    test_output = "temp_smoke_frames"

    # 1초짜리 더미 비디오 파일 생성
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(test_video, fourcc, 30.0, (640, 640))
    import numpy as np

    for _ in range(30):
        # 파란색 빈 화면 30프레임 (1초) 작성
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        frame[:, :] = [255, 0, 0]
        out.write(frame)
    out.release()

    try:
        paths = extract_frames(test_video, test_output, fps=1)
        print(f"추출 성공: {len(paths)}개 프레임 저장 완료.")
        for p in paths:
            print(f"- {p}")
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(test_output):
            os.rmdir(test_output)
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if os.path.exists(test_video):
            os.remove(test_video)
