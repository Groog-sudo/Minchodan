# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
import shutil
import pytest
import cv2
import numpy as np
from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.shared.labels import KICKBOARD, BOLLARD, BRAILLE_DAMAGED
from server.rag.embedding_engine_factory import MockEmbeddingEngine
from server.rag.build.db_builder import build_database
from server.rag.vector_db_factory import VectorDBFactory
from server.rag.retriever import Retriever
from server.rag.fallback import get_fallback_guidance
load_dotenv()


def test_e2e_rag_pipeline(tmp_path):
    video_path = str(tmp_path / "e2e_test_video.mp4")
    frames_dir = str(tmp_path / "e2e_frames")
    db_dir = str(tmp_path / "e2e_chromadb")
    
    # 1. 2초짜리 (60프레임) 더미 비디오 파일 생성
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (100, 100))
    for i in range(60):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # pHash 중복 검출 우회를 위해 각 프레임마다 점진적 변화 드로잉
        cv2.circle(frame, (50 + i//2, 50), 10, (255, 255, 255), -1)
        out.write(frame)
    out.release()
    
    # 2. 결정론적 Mock 임베딩 엔진 생성
    mock_embeds = MockEmbeddingEngine()
    
    # 3. 4단계 DB 빌더 실행 (비디오 -> 프레임 추출 -> pHash 중복제거 -> Mock 캡셔닝 -> ChromaDB 빌드)
    db_instance = build_database(
        video_path=video_path,
        output_dir=frames_dir,
        db_persist_dir=db_dir,
        embeddings=mock_embeds,
        force_mock_captioner=True
    )
    
    assert db_instance is not None
    
    # 4. 5단계 DB 팩토리를 통해 인덱싱된 Chroma DB 인스턴스 획득
    loaded_db = VectorDBFactory.get_vector_db("chroma", db_dir, mock_embeds)
    assert loaded_db is not None
    
    # 5. Retriever 객체 생성 및 실시간 3단계 YOLO 결과 주입 검색 수행
    retriever = Retriever(loaded_db)
    
    # CASE A: 정상적으로 ChromaDB에 인덱싱된 킥보드 검색 검증
    detect_info_kick = {
        "class_name": KICKBOARD,
        "confidence": 0.88,
        "bbox": [100, 200, 300, 400],
        "track_id": 1
    }
    guidance_kick = retriever.search_guidance(detect_info_kick)
    assert "킥보드" in guidance_kick
    
    # CASE B: DB에 인덱싱되지 않은 미확인 사물 검색 시, Retriever의 가드레일이 작동하여 빈 문자열 반환하고 fallback.py로 이어지는지 검증
    detect_info_unknown = {
        "class_name": "unknown_obstacle_type",
        "confidence": 0.75
    }
    guidance_fallback_empty = retriever.search_guidance(detect_info_unknown)
    # RAG 검색결과가 매칭되지 않아 빈 문자열을 기대함
    assert guidance_fallback_empty == ""
    
    # 빈 문자열을 받았으므로 fallback.py 룰북을 호출하여 지침 획득
    final_fallback_guidance = get_fallback_guidance(detect_info_unknown["class_name"])
    assert "unknown_obstacle_type" in final_fallback_guidance
    assert "서행" in final_fallback_guidance
    
    # 6. E2E 리소스 최종 정리 (Windows 파일 잠금 회피용 가드)
    try:
        db_instance = None
        loaded_db = None
        retriever = None
        import gc
        gc.collect()
        if os.path.exists(frames_dir):
            shutil.rmtree(frames_dir)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)
        if os.path.exists(video_path):
            os.remove(video_path)
    except Exception:
        pass
