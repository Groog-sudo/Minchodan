# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
import pytest
from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.embedding_engine_factory import EmbeddingEngineFactory, MockEmbeddingEngine
load_dotenv()


def test_embedding_engine_factory_mock():
    # Mock 임베딩 엔진 획득 검증
    embed = EmbeddingEngineFactory.get_embeddings(provider="mock")
    assert isinstance(embed, MockEmbeddingEngine)
    
    q_vec = embed.embed_query("테스트 질문")
    assert len(q_vec) == 768
    
    docs_vecs = embed.embed_documents(["테스트 문서 1", "테스트 문서 2"])
    assert len(docs_vecs) == 2
    assert len(docs_vecs[0]) == 768

def test_embedding_engine_factory_ollama():
    # 로컬 Ollama 구동 여부 사전 확인
    import requests
    ollama_online = False
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        res = requests.get(ollama_host, timeout=1.0)
        if res.status_code == 200 or "Ollama" in res.text:
            ollama_online = True
    except Exception:
        pass
        
    if not ollama_online:
        pytest.skip("로컬 Ollama 서비스가 실행 중이지 않으므로 테스트를 건너뜁니다.")
        
    embed = EmbeddingEngineFactory.get_embeddings(provider="ollama")
    assert embed is not None
    
    q_vec = embed.embed_query("테스트")
    assert len(q_vec) == 768

def test_embedding_engine_factory_invalid_provider():
    # 존재하지 않는 임베딩 공급자 지정 시 ValueError 검증
    with pytest.raises(ValueError):
        EmbeddingEngineFactory.get_embeddings(provider="non_existent_provider")
