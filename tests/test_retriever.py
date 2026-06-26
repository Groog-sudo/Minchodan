# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
import shutil
import json
import pytest
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

# 로컬 모듈 임포트
from server.rag.shared.labels import KICKBOARD, BOLLARD, BRAILLE_DAMAGED
from server.rag.embedding_engine_factory import EmbeddingEngineFactory
from server.rag.retriever import Retriever
load_dotenv()


def test_retriever_search_success(tmp_path):
    persist_dir = str(tmp_path / "chromadb_retriever_test")
    mock_embeds = EmbeddingEngineFactory.get_embeddings(provider="mock")
    
    # 1. 테스트용 수칙 문서 생성
    doc_kick = Document(
        page_content="장면 설명: 킥보드가 쓰러져 있습니다. 행동 수칙: 킥보드를 피해서 안전하게 지나가세요.",
        metadata={
            "scene_type": KICKBOARD,
            "risk_level": "mid",
            "objects": json.dumps([KICKBOARD]),
            "guidance_template": "킥보드를 피해서 안전하게 지나가세요."
        }
    )
    doc_boll = Document(
        page_content="장면 설명: 무릎 높이의 돌볼라드가 보입니다. 행동 수칙: 볼라드와 부딪히지 않도록 서행 우회하세요.",
        metadata={
            "scene_type": BOLLARD,
            "risk_level": "mid",
            "objects": json.dumps([BOLLARD]),
            "guidance_template": "볼라드와 부딪히지 않도록 서행 우회하세요."
        }
    )
    
    # 2. 임시 Chroma DB 적재 및 Retriever 구동
    db = Chroma.from_documents(
        documents=[doc_kick, doc_boll],
        embedding=mock_embeds,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )
    retriever = Retriever(db)
    
    # 3. 킥보드 정보로 RAG 검색 실행 검증
    detect_info_kick = {"class_name": KICKBOARD, "confidence": 0.9}
    guidance_kick = retriever.search_guidance(detect_info_kick)
    assert guidance_kick == "킥보드를 피해서 안전하게 지나가세요."
    
    # 4. 볼라드 정보로 RAG 검색 실행 검증
    detect_info_boll = {"class_name": BOLLARD, "confidence": 0.8}
    guidance_boll = retriever.search_guidance(detect_info_boll)
    assert guidance_boll == "볼라드와 부딪히지 않도록 서행 우회하세요."
    
    # DB 정리
    try:
        db = None
        import gc
        gc.collect()
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
    except Exception:
        pass

def test_retriever_search_failure():
    # 주입된 DB가 비었거나 잘못되어 검색 오류 발생 시 빈 문자열("") 리턴 및 가드레일 작동 검증
    retriever = Retriever(None) # None DB 전달
    detect_info = {"class_name": KICKBOARD}
    
    guidance = retriever.search_guidance(detect_info)
    assert guidance == "" # 예외를 가로채고 빈 문자열 리턴하여 중단 방지
