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
from server.rag.build.db_builder import build_database
from server.rag.embedding_engine_factory import MockEmbeddingEngine
load_dotenv()


def test_build_database_success(tmp_path):
    video_path = str(tmp_path / "test_video.mp4")
    output_frames_dir = str(tmp_path / "output_frames")
    db_persist_dir = str(tmp_path / "chromadb_test")
    
    # 1. 1.5초짜리 (45프레임) 더미 비디오 동적 생성
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (100, 100))
    for i in range(45):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # 매 프레임 다르게 텍스트를 그려서 pHash 중복 검사를 통과하게 유도
        cv2.putText(frame, str(i), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        out.write(frame)
    out.release()
    
    # 2. Mock 임베딩 모델 인스턴스 주입
    mock_embeds = MockEmbeddingEngine()
    
    # 3. 데이터베이스 빌드 수행 (Mock 캡셔너 강제 실행)
    db = build_database(
        video_path=video_path,
        output_dir=output_frames_dir,
        db_persist_dir=db_persist_dir,
        embeddings=mock_embeds,
        force_mock_captioner=True
    )
    
    assert db is not None
    
    # 4. 조회 검증
    search_res = db.similarity_search("킥보드", k=1)
    assert len(search_res) > 0
    assert "킥보드" in search_res[0].page_content or "볼라드" in search_res[0].page_content or "점자블록" in search_res[0].page_content
    assert "guidance_template" in search_res[0].metadata
    
    # 5. DB 객체 해제 및 수동 정리 (Windows 파일 잠금 회피용 가드)
    try:
        db = None
        import gc
        gc.collect()
        if os.path.exists(db_persist_dir):
            shutil.rmtree(db_persist_dir)
    except Exception:
        pass
