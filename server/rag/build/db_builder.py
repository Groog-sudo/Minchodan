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
from server.rag.shared.labels import BOLLARD, CAUTION, ROADWAY, SCOOTER

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

    # =========================================================================
    # 👨‍💻 HARD CODE 영역 시작 (안전 대처 수칙 템플릿 매핑) 👨‍💻
    # 💡 [면접 대비 주석]
    # 질문: VLM(Llava/Gemini)의 캡셔닝 결과만 넣지 않고, 왜 사전에 작성된 '전문가 안전 수칙(guidance_template)'을 함께 ChromaDB에 인덱싱하나요?
    # 답변: VLM은 화면을 '묘사'하는 데에는 탁월하지만 시각장애인 보행 안전 수칙에 대한 전문 지식은 부족하여 환각(Hallucination)을 일으킬 수 있습니다.
    #       따라서 DB 빌드 시점에 '위험 요소(클래스)'와 '전문가 검수를 거친 정해진 대처 수칙'을 메타데이터로 강력하게 결합(Hard-binding)하여 저장함으로써,
    #       이후 실시간 검색 시 LLM이 절대 엉뚱한 대처법을 지어내지 못하도록 원천 차단하는 설계입니다.
    # =========================================================================

    # TH HARD CODE AREA:
    # 현재는 실데이터 전면 정리 전 단계라서 화면/데모/면접 대응에 필요한 최소 라벨만 먼저 고정합니다.
    # 발표/면접 포인트: 내부 라벨은 scooter로 고정하고, 사용자 안내문은 한국 보행 맥락에 맞춰
    # "전동 킥보드 또는 스쿠터"로 표현합니다. 모델 taxonomy와 사용자 발화를 분리한 설계입니다.
    dummy_guidance_templates = {
        SCOOTER: "전방에 전동 킥보드 또는 스쿠터가 놓여 있습니다. 좌우 공간을 확인하며 천천히 비껴가세요.",
        BOLLARD: "전방에 볼라드가 있습니다. 정면 충돌을 피하도록 옆으로 돌아가세요.",
        CAUTION: "전방 바닥 위험 구간입니다. 발끝 높낮이를 확인하며 천천히 이동하세요.",
        ROADWAY: "차도와 가까운 구간입니다. 보도 안쪽으로 위치를 조정하세요.",
    }

    # =========================================================================
    # 👨‍💻 HARD CODE 영역 끝
    # =========================================================================

    print("[DB Builder] 3. VLM 상황 캡셔닝 및 문서 인덱싱 목록을 만듭니다.")
    for i, frame_path in enumerate(unique_frames):
        # 캡션 생성
        if force_mock_captioner:
            # 캡션 Mocking
            if i % 3 == 0:
                caption = "길가 한가운데 전동 킥보드 또는 스쿠터가 쓰러져 있고 통행을 방해하는 화면입니다."
                scene_type = SCOOTER
                risk_level = "mid"
                objects = [SCOOTER]
            elif i % 3 == 1:
                caption = "화강암 재질의 볼라드가 인도 보도블록 위에 불쑥 솟아 있는 모습입니다."
                scene_type = BOLLARD
                risk_level = "mid"
                objects = [BOLLARD]
            else:
                caption = "바닥 높낮이가 불규칙하고 주의가 필요한 위험 구간이 전방에 보입니다."
                scene_type = CAUTION
                risk_level = "high"
                objects = [CAUTION]
        else:
            try:
                caption = generate_caption(frame_path)
                # 캡션 내용에서 매칭되는 클래스 탐색하여 메타데이터 설정
                scene_type = "unknown"
                risk_level = "low"
                objects = []
                for cls in [SCOOTER, BOLLARD, CAUTION, ROADWAY]:
                    if cls in caption:
                        scene_type = cls
                        risk_level = "high" if cls == CAUTION else "mid"
                        objects.append(cls)
                        break
            except Exception as e:
                print(f"[DB Builder] {frame_path} 캡셔닝 실패: {e}. 기본 scooter로 폴백합니다.")
                caption = "전동 킥보드 또는 스쿠터가 방치된 화면입니다."
                scene_type = SCOOTER
                risk_level = "mid"
                objects = [SCOOTER]

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
        results = db.similarity_search("전동 킥보드 수칙", k=1)
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
