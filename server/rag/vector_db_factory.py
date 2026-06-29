import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
import shutil

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings

load_dotenv()


class VectorDBFactory:
    """
    Chroma, Qdrant 등 다양한 Vector DB 엔진 인스턴스를 동적으로 생성 및 연결하는 팩토리 클래스입니다.
    """

    @staticmethod
    def get_vector_db(db_type: str, persist_directory: str, embeddings: Embeddings):
        """
        요청된 db_type에 맞추어 로컬 Vector DB 객체를 반환합니다.

        Args:
            db_type: "chroma" | "qdrant" (현재 ChromaDB 기본 지원)
            persist_directory: DB가 영구 저장될 로컬 디렉토리 경로
            embeddings: 주입받을 외부 임베딩 모델 인스턴스 (결합 제거)

        Returns:
            VectorStore 구현체 인스턴스

        Raises:
            FileNotFoundError: 저장 경로의 부모 디렉토리가 존재하지 않거나 쓸 수 없을 경우 발생 (비협상 가드)
            ValueError: 지원하지 않는 db_type 지정 시 발생
        """
        db_type = db_type.lower().strip()

        # 저장 디렉토리 유효성 및 권한 검사
        parent_dir = os.path.dirname(os.path.abspath(persist_directory))
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                raise FileNotFoundError(
                    f"DB 영구 저장 경로를 생성할 수 없습니다: {parent_dir}. 에러: {e}"
                ) from e

        if os.path.exists(persist_directory) and not os.access(persist_directory, os.W_OK):
            raise FileNotFoundError(f"DB 저장 디렉토리에 쓰기 권한이 없습니다: {persist_directory}")

        if db_type == "chroma":
            # ChromaDB 인스턴스 로드/생성
            db = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings,
                collection_metadata={"hnsw:space": "cosine"},
            )
            return db
        elif db_type == "qdrant":
            # Qdrant 로컬 연동 (추후 확장 대비 플레이스홀더)
            try:
                from langchain_community.vectorstores import Qdrant

                # 로컬 Qdrant 클라이언트를 메모리 혹은 로컬 파일로 연동
                # 실제 운영 환경 도입 시 라이브러리 추가 필요
                db = Qdrant.from_documents(documents=[], embedding=embeddings, location=":memory:")
                return db
            except Exception as e:
                raise ValueError(f"Qdrant 로드 실패 (의존성 패키지를 확인하세요): {e}") from e
        else:
            raise ValueError(f"지원하지 않는 Vector DB 타입입니다: {db_type}")


# 스모크 테스트용 임시 임베딩 클래스
if __name__ == "__main__":
    print("vector_db_factory.py 스모크 테스트 실행")

    test_db_dir = "temp_smoke_factory_chromadb"
    try:
        from server.rag.embedding_engine_factory import MockEmbeddingEngine

        mock_embeds = MockEmbeddingEngine()
        # ChromaDB 팩토리 로드 검증
        db = VectorDBFactory.get_vector_db("chroma", test_db_dir, mock_embeds)
        print(f"ChromaDB 인스턴스 팩토리 생성 성공: {db is not None}")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if os.path.exists(test_db_dir):
            try:
                db = None
                import gc

                gc.collect()
                shutil.rmtree(test_db_dir)
            except Exception as e:
                print(f"[Cleanup Warning] 임시 DB 폴더 삭제 건너뜀 (Windows 파일 잠금): {e}")
