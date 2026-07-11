import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
import shutil

import pytest
from dotenv import load_dotenv

from server.rag.embedding_engine_factory import MockEmbeddingEngine

# 로컬 모듈 임포트
from server.rag.vector_db_factory import VectorDBFactory

load_dotenv()


def test_vector_db_factory_chroma(tmp_path):
    persist_dir = str(tmp_path / "chromadb_factory_test")
    mock_embeds = MockEmbeddingEngine()

    # 팩토리 메소드 호출 검증
    db = VectorDBFactory.get_vector_db("chroma", persist_dir, mock_embeds)
    assert db is not None

    # Windows 파일 잠금 해제를 위한 조치
    try:
        db = None
        import gc

        gc.collect()
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
    except Exception:
        pass


def test_vector_db_factory_invalid_type(tmp_path):
    persist_dir = str(tmp_path / "db_test")
    mock_embeds = MockEmbeddingEngine()

    # 지원하지 않는 DB타입 전달 시 ValueError 검증
    with pytest.raises(ValueError):
        VectorDBFactory.get_vector_db("invalid_db_engine", persist_dir, mock_embeds)


def test_vector_db_factory_invalid_path(tmp_path):
    mock_embeds = MockEmbeddingEngine()

    # 이미 존재하는 일반 파일 하위 경로를 지정하면 디렉토리 생성 실패(NotADirectoryError/FileNotFoundError 등) 발생
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("dummy")
    invalid_path = str(dummy_file / "chromadb_test")

    with pytest.raises(Exception):  # noqa: B017
        VectorDBFactory.get_vector_db("chroma", invalid_path, mock_embeds)
