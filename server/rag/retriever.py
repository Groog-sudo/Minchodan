import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import os

from dotenv import load_dotenv
from langchain_core.vectorstores import VectorStore

# TH HARD CODE AREA:
# shared/labels.py의 현재 SSOT는 구 라벨명이 아니라 SCOOTER입니다.
# 면접/발표 포인트: RAG 검색기는 탐지 taxonomy와 같은 라벨만 사용해야 모듈 import 단계에서 죽지 않고,
# YOLO -> RAG -> LangGraph 경로의 라벨 계약을 한 곳에서 설명할 수 있습니다.
from server.rag.shared.labels import SCOOTER

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
                         예: {"class_name": "scooter", "confidence": 0.87, "bbox": [120, 200, 280, 360]}
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

            class_name = class_name.lower().strip()
            best_doc = None

            # 면접/발표 포인트:
            # RAG 문서의 scene_type은 "sidewalk"처럼 상황/노면을 뜻할 수 있고,
            # YOLO 탐지 class_name은 "scooter"처럼 실제 장애물 객체를 뜻할 수 있습니다.
            # 따라서 Top-K 결과를 순회하며 scene_type 또는 objects 중 하나라도 맞는 문서를 채택합니다.
            for candidate_doc, _score in results:
                metadata = candidate_doc.metadata
                scene_type = str(metadata.get("scene_type") or "").lower().strip()

                objects_raw = metadata.get("objects", [])
                try:
                    if isinstance(objects_raw, str):
                        objects = json.loads(objects_raw)
                    else:
                        objects = objects_raw
                except json.JSONDecodeError:
                    objects = []

                objects = [str(obj).lower().strip() for obj in objects]
                if scene_type == class_name or class_name in objects:
                    best_doc = candidate_doc
                    break

            if best_doc is None:
                print(f"[Retriever] 라벨 불일치 (질의: {class_name}) -> RAG 미적중 처리")
                return ""

            metadata = best_doc.metadata
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


_default_retriever: "Retriever | None" = None


def get_default_retriever() -> "Retriever | None":
    """
    모듈 수준 싱글턴. .env의 CHROMA_PATH/CHROMA_COLLECTION/EMBEDDING_MODEL 기준으로
    Ollama 임베딩 + ChromaDB를 연결한 Retriever를 최초 호출 시 1회 생성해 재사용한다.
    임베딩/DB 연결 실패 시 None을 반환해 호출부가 fallback으로 우회하도록 한다(비협상 가드).
    """
    global _default_retriever
    if _default_retriever is not None:
        return _default_retriever

    try:
        from server.rag.embedding_engine_factory import EmbeddingEngineFactory
        from server.rag.vector_db_factory import VectorDBFactory

        chroma_path = os.getenv("CHROMA_PATH", "data/chroma_db")
        collection_name = os.getenv("CHROMA_COLLECTION", "safety_guidelines")
        embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "ollama")

        embeddings = EmbeddingEngineFactory.get_embeddings(
            provider=embedding_provider, model_name=embedding_model
        )
        vector_db = VectorDBFactory.get_vector_db(
            "chroma", chroma_path, embeddings, collection_name=collection_name
        )
        _default_retriever = Retriever(vector_db)
        return _default_retriever
    except Exception as e:
        print(f"[Retriever] 기본 Retriever 초기화 실패 (RAG 미사용으로 진행): {e}")
        return None


if __name__ == "__main__":
    print("retriever.py 스모크 테스트 실행")

    # 1. 테스트용 임시 임베딩 및 Chroma DB 생성
    import shutil

    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document

    from server.rag.embedding_engine_factory import EmbeddingEngineFactory

    test_db_dir = "temp_smoke_retriever_chromadb"
    mock_embeds = EmbeddingEngineFactory.get_embeddings(provider="mock")

    # TH HARD CODE AREA:
    # 모델 내부 라벨은 SCOOTER 하나로 통일하고, 사용자 안내문은 "전동킥보드 또는 스쿠터"로 표현합니다.
    # 발표/면접 포인트: 탐지 taxonomy와 발화 문구를 분리하면 모델 재학습 없이도 사용자 친화적인 한국어 안내가 가능합니다.
    doc = Document(
        page_content="장면 설명: 전동킥보드 또는 스쿠터가 쓰러져 있습니다. 행동 수칙: 좌우 여유 공간을 확인하며 천천히 우회하세요.",
        metadata={
            "scene_type": SCOOTER,
            "risk_level": "mid",
            "objects": json.dumps([SCOOTER]),
            "guidance_template": "전방에 전동킥보드 또는 스쿠터가 있습니다. 좌우 여유 공간을 확인하며 천천히 우회하세요.",
        },
    )

    try:
        db = Chroma.from_documents(
            documents=[doc],
            embedding=mock_embeds,
            persist_directory=test_db_dir,
            collection_metadata={"hnsw:space": "cosine"},
        )
        retriever = Retriever(db)

        # 조회 테스트
        detect_info = {"class_name": SCOOTER, "confidence": 0.9}
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
