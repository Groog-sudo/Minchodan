import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.rag.convenience_rag import build_convenience_database
from server.rag.embedding_engine_factory import EmbeddingEngineFactory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="시각장애인 생활지원 통합 안내 JSON을 ChromaDB에 적재합니다."
    )
    parser.add_argument(
        "--json-path",
        default=os.getenv(
            "CONVENIENCE_JSON_PATH",
            os.path.join(project_root, "data", "convenience_guidelines.json"),
        ),
        help="입력 JSON 경로",
    )
    parser.add_argument(
        "--persist-dir",
        default=os.getenv(
            "CONVENIENCE_CHROMA_PATH",
            os.path.join(project_root, "data", "chroma_db", "convenience_guidelines"),
        ),
        help="ChromaDB 저장 경로",
    )
    parser.add_argument(
        "--collection-name",
        default=os.getenv("CONVENIENCE_CHROMA_COLLECTION", "convenience_guidelines"),
        help="Chroma 컬렉션명",
    )
    parser.add_argument(
        "--embedding-provider",
        default=os.getenv("CONVENIENCE_EMBEDDING_PROVIDER", "ollama"),
        help="임베딩 프로바이더",
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("CONVENIENCE_EMBEDDING_MODEL", "nomic-embed-text"),
        help="임베딩 모델명",
    )
    args = parser.parse_args()

    embeddings = EmbeddingEngineFactory.get_embeddings(
        provider=args.embedding_provider,
        model_name=args.embedding_model,
    )

    db = build_convenience_database(
        json_path=args.json_path,
        persist_directory=args.persist_dir,
        embeddings=embeddings,
        collection_name=args.collection_name,
    )

    count = db._collection.count() if hasattr(db, "_collection") else "unknown"
    print("생활지원 RAG DB 빌드 완료")
    print(f"- JSON: {args.json_path}")
    print(f"- 저장 경로: {args.persist_dir}")
    print(f"- 컬렉션: {args.collection_name}")
    print(f"- 문서 수: {count}")


if __name__ == "__main__":
    main()
