"""
공공 단체 매뉴얼 텍스트 데이터(safety_guidelines.json)를 로딩하여
로컬 벡터 DB(ChromaDB)에 다이렉트로 임베딩 인덱싱 및 재구축하는 스크립트.
"""

import json
import os
import sys

# UTF-8 출력 재설정 (guide 3.1)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# sys.path에 프로젝트 루트 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from server.rag.embedding_engine_factory import EmbeddingEngineFactory


def build_database():
    json_path = os.path.join(project_root, "data", "safety_guidelines.json")
    persist_dir = os.path.join(project_root, "data", "chroma_db")

    print("==================================================")
    print(" 1. 시각장애인 보행 안전 수칙 RAG 데이터베이스 빌드")
    print("==================================================")

    # 1. JSON 파일 확인
    if not os.path.exists(json_path):
        print(f"[실패] 소스 수칙 JSON 파일이 없습니다: {json_path}")
        sys.exit(1)

    print(f"-> 소스 파일 탐색 완료: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        guidelines = json.load(f)

    # 2. 임베딩 엔진 획득 (Ollama 자동 탐색 및 폴백 제공)
    print("-> 임베딩 엔진(nomic-embed-text) 초기화 시도...")
    embeddings = EmbeddingEngineFactory.get_embeddings(provider="ollama")
    print(f"[성공] 임베딩 엔진 준비 완료: {type(embeddings).__name__}")

    # 3. Document 컬렉션 패킹
    documents = []
    for idx, item in enumerate(guidelines):
        objects = item["objects"]
        if not objects:
            objects = ["none"]
        doc = Document(
            page_content=item["caption"],
            metadata={
                "objects": objects,
                "scene_type": item["scene_type"],
                "risk_level": item["risk_level"],
                "guidance_template": item["guidance"],
            },
        )
        documents.append(doc)
        print(
            f"  - 문서 [{idx + 1:02d}]: scene_type={item['scene_type']}, objects={item['objects']}"
        )

    print(f"-> 총 {len(documents)}개의 문서를 패킹 완료하였습니다.")

    # 4. ChromaDB 적재 및 영구 저장
    print("-> ChromaDB 적재 및 디스크 물리 보존 파일 저장 중...")

    # 기존 DB 리셋 처리 (클래스 차원 불일치 방지)
    import shutil

    if os.path.exists(persist_dir):
        print(f"  - 기존 저장소 청소: {persist_dir}")
        shutil.rmtree(persist_dir)

    try:
        db = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_dir,
            collection_name="safety_guidelines",
        )
        # 1.0 미만 langchain 호환성 유지용 임시 persist 호출
        if hasattr(db, "persist"):
            db.persist()

        print("\n==================================================")
        print(" 🎉 [성공] ChromaDB 지식베이스 영구 인덱싱 재구축 완료!")
        print("==================================================")
        print(f" - 저장 위치: {persist_dir}")
        print(f" - 데이터 건수: {len(documents)} 건")
        print("==================================================")
    except Exception as e:
        print(f"[실패] ChromaDB 빌드 중 예외 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_database()
