# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
import json
from dotenv import load_dotenv
from langchain_core.vectorstores import VectorStore

# 로컬 모듈 임포트
from server.rag.shared.labels import KICKBOARD, BOLLARD, BRAILLE_DAMAGED
load_dotenv()


# TODO(latency): 로컬 임베딩 적용 후에도 실제 50ms 실측은 아직 진행되지 않았음.
# 이번 스켈레톤 단계에서는 성능 튜닝/캐싱을 시도하지 않음.

class Retriever:
    """
    탐지된 사물 정보를 기반으로 Vector DB를 조회하여 적절한 안전 대처 수칙을 매칭하고 반환하는 검색 엔진 클래스입니다.
    """
    
    def __init__(self, vector_db: VectorStore):
        """
        Retriever를 초기화합니다.
        
        Args:
            vector_db: 조회할 주입된 VectorStore 인스턴스
        """
        self.vector_db = vector_db
        
    def search_guidance(self, detect_info: dict, k: int = 5) -> str:
        """
        실시간 탐지 정보(detect_info)를 분석하여 해당 장애물의 대처 수칙 가이드 템플릿을 검색합니다.
        검색 중 오류나 미적중 발생 시, 시스템 중단을 차단하기 위해 예외를 잡아서 빈 문자열("")을 반환하며
        이후 안전망(fallback.py)으로 가이드 생성이 유도되도록 합니다.
        
        Args:
            detect_info: 3단계 YOLO 탐지 결과 정보 딕셔너리
                         예: {"class_name": "kickboard", "confidence": 0.87, "bbox": [120, 200, 280, 360]}
            k: 가져올 상위 유사 문서 개수 (기본값 5)
            
        Returns:
            유사 매칭된 안전 지침 문자열 (실패/미적중 시 "")
        """
        # [DUMMY DATA] 설명: Retriever 테스트용 detect_info 입력 / 주의: class_name은 shared/labels.py 기준을 준수해야 함
        class_name = detect_info.get("class_name")
        if not class_name:
            print("[Retriever Warning] detect_info에 class_name이 존재하지 않습니다.")
            return ""
            
        query = f"{class_name} 보행 중 회피 방법"
        
        try:
            # 코사인 유사도 기반 의미 유사 검색 수행
            # 만약 DB가 비어있거나 검색 중 오류 발생 시, 빈 결과를 리턴하도록 try-except 가드 적용 (비협상 가드)
            results = self.vector_db.similarity_search_with_score(query, k=k)
            if not results:
                return ""
                
            # 가장 높은 스코어를 기록한 문서 중, metadata의 guidance_template을 반환
            best_doc, score = results[0]
            
            # 메타데이터 추출 및 라벨 매칭 검증 (비협상 가드)
            metadata = best_doc.metadata
            scene_type = metadata.get("scene_type")
            if scene_type != class_name:
                print(f"[Retriever] 라벨 불일치 (질의: {class_name}, 결과: {scene_type}) -> RAG 미적중 처리")
                return ""
                
            guidance = metadata.get("guidance_template")
            if not guidance:
                # 본문에서 행동 수칙 분리 파싱 시도
                content = best_doc.page_content
                if "행동 수칙:" in content:
                    guidance = content.split("행동 수칙:")[-1].strip()
                else:
                    guidance = content
                    
            return str(guidance)
            
        except Exception as e:
            # 검색 도중 예외가 발생하더라도 빈 문자열을 리턴하여 프로그램 중단을 막고 fallback으로 우회시킴
            print(f"[Retriever Error] RAG 검색 실패 (fallback 모드로 진입합니다): {e}")
            return ""

if __name__ == "__main__":
    print("retriever.py 스모크 테스트 실행")
    
    # 1. 테스트용 임시 임베딩 및 Chroma DB 생성
    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document
    from server.rag.embedding_engine_factory import EmbeddingEngineFactory
    import shutil
    
    test_db_dir = "temp_smoke_retriever_chromadb"
    mock_embeds = EmbeddingEngineFactory.get_embeddings(provider="mock")
    
    # 더미 문서 생성
    doc = Document(
        page_content="장면 설명: 킥보드가 쓰러져 있습니다. 행동 수칙: 킥보드를 조심히 피해서 돌아가세요.",
        metadata={
            "scene_type": KICKBOARD,
            "risk_level": "mid",
            "objects": json.dumps([KICKBOARD]),
            "guidance_template": "킥보드를 조심히 피해서 돌아가세요."
        }
    )
    
    try:
        db = Chroma.from_documents(
            documents=[doc],
            embedding=mock_embeds,
            persist_directory=test_db_dir,
            collection_metadata={"hnsw:space": "cosine"}
        )
        retriever = Retriever(db)
        
        # 조회 테스트
        detect_info = {"class_name": KICKBOARD, "confidence": 0.9}
        res = retriever.search_guidance(detect_info)
        print(f"RAG 매칭 검색 결과: {res}")
        
    except Exception as e:
        print(f"테스트 중 오류: {e}")
    finally:
        if os.path.exists(test_db_dir):
            try:
                db = None
                import gc
                gc.collect()
                shutil.rmtree(test_db_dir)
            except Exception as e:
                print(f"[Cleanup Warning] 임시 DB 폴더 삭제 건너뜀 (Windows 파일 잠금): {e}")
