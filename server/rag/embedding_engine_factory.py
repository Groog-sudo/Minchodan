# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
load_dotenv()


class EmbeddingEngineFactory:
    """
    Ollama nomic-embed-text 등 로컬 및 외부 API 임베딩 모델 인스턴스를 관리하고 반환하는 팩토리 클래스입니다.
    
    WARNING (임베딩 엔진 모델 변경 시 주의사항):
    - 다른 임베딩 모델로 변경 시, 기존에 생성되어 저장된 로컬 벡터 DB 인덱스의 벡터 차원 및 공간이 
      서로 불일치하여 호환이 차단됩니다.
    - 따라서 임베딩 모델 설정을 바꿀 경우, 반드시 '4단계 DB 구축 배치 파이프라인'을 재실행하여 
      전체 데이터를 새로 인덱싱(재구축)해야만 합니다.
    """
    
    @staticmethod
    def get_embeddings(provider: str = "ollama", model_name: str = "nomic-embed-text") -> Embeddings:
        """
        지정된 프로바이더와 모델명에 맞는 Embeddings 인스턴스를 반환합니다.
        
        Args:
            provider: "ollama" | "mock" | "openai" (기본값 "ollama")
            model_name: 사용할 모델명 (기본값 "nomic-embed-text")
            
        Returns:
            Embeddings 객체
        """
        provider = provider.lower().strip()
        
        if provider == "ollama":
            try:
                # langchain-ollama 패키지 로드
                from langchain_ollama import OllamaEmbeddings
                
                ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                return OllamaEmbeddings(
                    model=model_name,
                    base_url=ollama_host
                )
            except Exception as e:
                print(f"[Embedding Factory] OllamaEmbeddings 초기화 실패: {e}. Mock 임베딩으로 대체합니다.")
                return MockEmbeddingEngine()
                
        elif provider == "mock":
            return MockEmbeddingEngine()
            
        elif provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings
                return OpenAIEmbeddings(model=model_name)
            except Exception as e:
                raise ValueError(f"OpenAIEmbeddings 로드 실패: {e}")
                
        else:
            raise ValueError(f"지원하지 않는 임베딩 프로바이더입니다: {provider}")

class MockEmbeddingEngine(Embeddings):
    """
    Ollama 등 외부 서비스가 구동되지 않는 환경에서 동작을 보장하기 위한 결정론적 Mock 임베딩 클래스입니다.
    텍스트 내 키워드를 매칭하여 동일 범주 문서와 쿼리가 높은 유사도를 가지도록 설계되었습니다.
    """
    def _embed(self, text: str):
        import random
        import numpy as np
        
        target_keyword = "default"
        for keyword in ["kickboard", "bollard", "braille_damaged", "stairs", "crosswalk", "manhole", "grating", "점자", "킥보드", "볼라드"]:
            if keyword in text:
                # 관련 키워드 표준화
                if keyword in ["kickboard", "킥보드"]:
                    target_keyword = "kickboard"
                elif keyword in ["bollard", "볼라드"]:
                    target_keyword = "bollard"
                elif keyword in ["braille_damaged", "점자"]:
                    target_keyword = "braille_damaged"
                else:
                    target_keyword = keyword
                break
                
        # 해시 시드 설정
        seed = sum(ord(c) for c in target_keyword)
        random.seed(seed)
        vec = [random.gauss(0, 1) for _ in range(768)]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]
        
    def embed_query(self, text):
        return self._embed(text)

if __name__ == "__main__":
    print("embedding_engine_factory.py 스모크 테스트 실행")
    
    # 1. Mock 임베딩 테스트
    mock_embed = EmbeddingEngineFactory.get_embeddings(provider="mock")
    print(f"Mock 임베딩 인스턴스 팩토리 생성 완료: {mock_embed is not None}")
    q_vec = mock_embed.embed_query("테스트")
    print(f"- 임베딩 차원: {len(q_vec)} (768차원 기대)")
    
    # 2. Ollama 임베딩 테스트 (로컬 Ollama 서비스 연결 상태에 상관없이 에러 없이 넘어감)
    ollama_embed = EmbeddingEngineFactory.get_embeddings(provider="ollama")
    print(f"Ollama 임베딩 인스턴스 팩토리 획득 완료: {ollama_embed is not None}")
