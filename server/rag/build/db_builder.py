import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import contextlib
import json
import os
import shutil

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from server.rag.build.dedup_phash import filter_duplicates
from server.rag.build.frame_extractor import extract_frames
from server.rag.build.gemini_captioner import generate_caption

# 로컬 모듈 임포트
from server.rag.shared.labels import (
    BOLLARD,
    BRAILLE_DAMAGED,
    KICKBOARD,
)

load_dotenv()


def build_database(
    video_path: str,
    output_dir: str,
    db_persist_dir: str,
    embeddings: Embeddings,
    force_mock_captioner: bool = False,
) -> Chroma:
    """
    비디오에서 프레임을 추출하고 중복을 제거한 후 VLM 캡셔닝을 통해
    행동 수칙과 매핑하여 ChromaDB 로컬 벡터 DB를 인덱싱하고 빌드합니다.

    Args:
        video_path: 입력 비디오 파일 경로
        output_dir: 임시 프레임 저장 경로
        db_persist_dir: ChromaDB 영구 저장 디렉토리 경로
        embeddings: 인덱싱에 사용할 랭체인 Embeddings 구현 객체
        force_mock_captioner: True인 경우 VLM API 대신 테스트용 더미 캡션을 강제 반환

    Returns:
        생성된 Chroma 인스턴스

    Raises:
        PermissionError: 저장 디렉토리에 쓰기 권한이 없을 경우 발생 (비협상 가드)
        ValueError: 비디오 혹은 프레임 처리 오류 시 발생
    """
    # 디바이스 권한 및 쓰기 에러 사전 검사
    parent_dir = os.path.dirname(os.path.abspath(db_persist_dir))
    if not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception as e:
            raise PermissionError(
                f"디스크 쓰기 권한이 없거나 경로가 잘못되었습니다: {parent_dir}. 에러: {e}"
            ) from e

    if os.path.exists(db_persist_dir) and not os.access(db_persist_dir, os.W_OK):
        raise PermissionError(f"ChromaDB 경로에 쓰기 권한이 없습니다: {db_persist_dir}")

    # 1. 프레임 추출
    print("[DB Builder] 1. 프레임 추출을 시작합니다.")
    extracted_frames = extract_frames(video_path, output_dir, fps=1)
    print(f"[DB Builder] 추출된 총 프레임 개수: {len(extracted_frames)}")

    # 2. 중복 프레임 제거
    print("[DB Builder] 2. pHash 중복 제거를 적용합니다.")
    unique_frames = filter_duplicates(extracted_frames, threshold=5)
    print(f"[DB Builder] 중복 제거 후 고유 프레임 개수: {len(unique_frames)}")

    # 3. 캡션 생성 및 안전 지침 문서 빌딩
    documents = []

    # [DUMMY DATA] 설명: 전문가 검수를 거친 실제 안전 대처 수칙 텍스트 / 주의: objects/scene_type 값은 labels.py의 상수와 일치해야 함
    dummy_guidance_templates = {
        KICKBOARD: "전방에 킥보드가 무단 방치되어 있습니다. 킥보드 충돌 방지를 위해 보행 속도를 줄이고, 좌측 혹은 우측으로 한 보 이상 비껴 안전거리를 확보하며 서행하세요.",
        BOLLARD: "시각장애인 보행로 상에 차량 진입 방지용 볼라드가 감지되었습니다. 무릎 충돌 위험이 있으므로 즉시 보폭을 좁히고 지팡이 촉으로 위치를 탐색하며 안전하게 우회하세요.",
        BRAILLE_DAMAGED: "바닥 점자블록이 파손되거나 유실된 구간이 존재합니다. 발밑 유실로 인한 낙상 위험이 있으니, 지팡이 중심의 지지면에 힘을 싣고 느린 보조로 조심스럽게 전진하십시오.",
    }

    print("[DB Builder] 3. VLM 상황 캡셔닝 및 문서 인덱싱 목록을 만듭니다.")
    for i, frame_path in enumerate(unique_frames):
        # 캡션 생성
        if force_mock_captioner:
            # 캡션 Mocking
            if i % 3 == 0:
                caption = "길가 한가운데 전동 킥보드가 쓰러져 있고 통행을 방해하는 화면입니다."
                scene_type = KICKBOARD
                risk_level = "mid"
                objects = [KICKBOARD]
            elif i % 3 == 1:
                caption = "화강암 재질의 볼라드가 인도 보도블록 위에 불쑥 솟아 있는 모습입니다."
                scene_type = BOLLARD
                risk_level = "mid"
                objects = [BOLLARD]
            else:
                caption = "파편이 깨지고 마모되어 형태가 어지러운 노란색 파손 점자블록이 보입니다."
                scene_type = BRAILLE_DAMAGED
                risk_level = "high"
                objects = [BRAILLE_DAMAGED]
        else:
            try:
                caption = generate_caption(frame_path)
                # 캡션 내용에서 매칭되는 클래스 탐색하여 메타데이터 설정
                scene_type = "unknown"
                risk_level = "low"
                objects = []
                for cls in [KICKBOARD, BOLLARD, BRAILLE_DAMAGED]:
                    if cls in caption or (cls == BRAILLE_DAMAGED and "점자" in caption):
                        scene_type = cls
                        risk_level = "high" if cls == BRAILLE_DAMAGED else "mid"
                        objects.append(cls)
                        break
            except Exception as e:
                print(f"[DB Builder] {frame_path} 캡셔닝 실패: {e}. 기본 킥보드로 폴백합니다.")
                caption = "킥보드가 방치된 화면입니다."
                scene_type = KICKBOARD
                risk_level = "mid"
                objects = [KICKBOARD]

        # 문서 조립
        guidance = dummy_guidance_templates.get(scene_type, "주의하여 서행해 주세요.")
        page_content = f"장면 설명: {caption}\n행동 수칙: {guidance}"

        # 메타데이터 스키마 규격 정의
        metadata = {
            "scene_type": scene_type,
            "risk_level": risk_level,
            "objects": json.dumps(
                objects
            ),  # ChromaDB 메타데이터는 단순 기본 타입 또는 문자열이어야 함
            "guidance_template": guidance,
        }

        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    if not documents:
        raise ValueError("빌드할 문서 리스트가 비어 있습니다.")

    # 4. Vector DB 적재
    print(f"[DB Builder] 4. ChromaDB 적재를 완료합니다. (저장 경로: {db_persist_dir})")
    db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=db_persist_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
    db.persist()
    print("[DB Builder] DB 빌드 성공 및 디스크 저장 완료.")
    return db


if __name__ == "__main__":
    print("db_builder.py 스모크 테스트 실행")

    test_video = "temp_smoke_builder_video.mp4"
    test_frames = "temp_smoke_builder_frames"
    test_db_dir = "temp_smoke_chromadb"

    # 1. OpenCV를 통해 더미 비디오 파일 생성
    import cv2
    import numpy as np

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(test_video, fourcc, 30.0, (640, 640))
    for i in range(90):  # 3초 분량 비디오
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        # 프레임에 변화를 주어 pHash 필터링 테스트
        cv2.putText(frame, f"Frame {i}", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    out.release()

    try:
        from server.rag.embedding_engine_factory import MockEmbeddingEngine

        mock_embeds = MockEmbeddingEngine()
        db = build_database(
            video_path=test_video,
            output_dir=test_frames,
            db_persist_dir=test_db_dir,
            embeddings=mock_embeds,
            force_mock_captioner=True,
        )
        print(f"빌드 성공 여부 확인: {db is not None}")

        # 검색 동작 테스트
        results = db.similarity_search("킥보드 수칙", k=1)
        if results:
            print("성공적인 조회 결과:")
            print(f"- 내용: {results[0].page_content}")
            print(f"- 메타데이터: {results[0].metadata}")

    except Exception as e:
        print(f"테스트 실패: {e}")
    finally:
        # 정리
        if os.path.exists(test_frames):
            with contextlib.suppress(Exception):
                shutil.rmtree(test_frames)
        if os.path.exists(test_db_dir):
            try:
                # Chroma 객체 소멸 유도
                db = None
                import gc

                gc.collect()
                shutil.rmtree(test_db_dir)
            except Exception as e:
                print(f"[Cleanup Warning] 임시 DB 폴더 삭제 건너뜀 (Windows 파일 잠금): {e}")
        if os.path.exists(test_video):
            with contextlib.suppress(Exception):
                os.remove(test_video)
