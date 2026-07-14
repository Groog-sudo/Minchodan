import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 음성 연락처 RAG 저장소: ChromaDB 기반 이름->번호 유사도 검색.
# 저장 문서는 시각장애인 보행 편의성 맥락을 담은 풍부한 문장이다.
# ==========================================
#
# 💡 [면접 대비 주석 - 왜 연락처를 RAG에 넣었는가 (사용자 결정)]
# Q. 연락처는 사실 데이터라 DB 정확 매칭이 맞지 않나요?
# A. "기본 설계는 user_contacts(MariaDB) 정확 매칭이었다. 하지만 RAG 경로를
#    종단 시연하기 위해 사용자가 RAG 기반 저장/조회로 전환을 결정했다. 단,
#    LLM 환각 위험(번호를 paraphrase)은 메타데이터에서 번호를 직접 꺼내는
#    방식으로 제거하고, 유사도 매칭 불확실성은 이름 정규화 후보 필터링으로
#    방어했다. 'RAG를 쓰되 사실 데이터 안전망을 같이 둔 설계'로 발표한다."
#
# 💡 [면접 대비 주석 - 왜 단순 번호 문장이 아니라 편의성 맥락 문장으로 저장하나]
# Q. "엄마의 전화번호는 010-1234-5678입니다"만 저장하면 안 되나요?
# A. "이 RAG는 시각장애인 보행 보조 편의성 기능의 일환이다. 단순 번호 문장보다
#    '보행 중 긴급 상황에 보호자에게 즉시 연결하기 위한 연락처'라는 편의성
#    맥락을 함께 적으면, '엄마한테 전화 걸어줘' 같은 사용자 발화와 의미 유사도가
#    더 높게 잡힌다. 번호 자체는 metadata.phone_number에서 직접 꺼내므로
#    임베딩 문장이 길어져도 번호 정합성에는 영향을 주지 않는다."
#
# 💡 [면접 대비 주석 - LLM을 거치지 않는 이유]
# Q. RAG 조회 결과를 LLM에 넘겨 번호를 추출하면 안 되나요?
# A. "LLM이 010-1234-5678을 01012345678이나 010-123-45678로 바꿔 출력할
#    위험이 있다. 그래서 similarity_search 결과의 metadata.phone_number를
#    그대로 반환하고 LLM은 번호를 만지지 않는다."

from langchain_core.documents import Document

CHROMA_CONTACT_PATH = os.getenv("CHROMA_CONTACT_PATH", "data/chroma_db_contacts")
CHROMA_CONTACT_COLLECTION = os.getenv("CHROMA_CONTACT_COLLECTION", "user_contacts")


def _doc_id(user_id: int, normalized_name: str) -> str:
    return f"contact-{user_id}-{normalized_name}"


def _build_contact_page_content(display_name: str, phone_number: str) -> str:
    """시각장애인 보행 편의성 맥락을 담은 저장용 문장을 만든다.

    임베딩은 이 문장으로 생성되고, 번호는 metadata에서 직접 꺼내므로
    문장이 길어져도 번호 정합성에는 영향을 주지 않는다.
    """
    return (
        f"{display_name}의 전화번호는 {phone_number}입니다. "
        f"시각장애인 보행 보조 중 긴급 상황이나 길 안내가 필요할 때 "
        f"{display_name}에게 즉시 연결하기 위한 필수 보호자 연락처입니다. "
        f"음성 명령으로 {display_name}에게 전화를 걸거나 연락처를 불러올 때 사용합니다."
    )


class ContactRagStore:
    """ChromaDB 기반 연락처 저장/조회. 임베딩은 검색용, 번호는 메타데이터."""

    def __init__(self, vector_db, embeddings):
        self.vector_db = vector_db
        self.embeddings = embeddings

    def save(
        self,
        *,
        user_id: int,
        device_uuid: str,
        display_name: str,
        normalized_name: str,
        phone_number: str,
    ) -> None:
        doc_id = _doc_id(user_id, normalized_name)
        try:
            self.vector_db.delete(ids=[doc_id])
        except Exception as e:
            print(f"[ContactRag] 기존 문서 삭제 스킵(신규 가능): {e}")

        page_content = _build_contact_page_content(display_name, phone_number)
        doc = Document(
            page_content=page_content,
            metadata={
                "user_id": str(user_id),
                "device_uuid": device_uuid,
                "display_name": display_name,
                "normalized_name": normalized_name,
                "phone_number": phone_number,
                "type": "contact",
            },
        )
        self.vector_db.add_documents([doc], ids=[doc_id])

    def lookup(self, user_id: int, query_name: str) -> str | None:
        normalized = query_name.strip()
        query_text = (
            f"{query_name}에게 전화 걸어줘. 보행 중 긴급 상황이나 길 안내가 "
            f"필요할 때 {query_name}에게 즉시 연결하기 위한 보호자 연락처를 찾습니다."
        )
        try:
            results = self.vector_db.similarity_search_with_score(
                query_text,
                k=5,
                filter={"user_id": str(user_id)},
            )
        except Exception as e:
            print(f"[ContactRag] 조회 실패: {e}")
            return None

        if not results:
            return None

        for doc, _score in results:
            metadata = doc.metadata
            saved_norm = str(metadata.get("normalized_name") or "").strip()
            saved_display = str(metadata.get("display_name") or "").strip()
            if saved_norm == normalized or saved_display == normalized:
                return str(metadata.get("phone_number") or "") or None
            if saved_norm and (saved_norm in normalized or normalized in saved_norm):
                return str(metadata.get("phone_number") or "") or None
            if saved_display and (saved_display in query_name or query_name in saved_display):
                return str(metadata.get("phone_number") or "") or None
        return None

    def list_by_user(self, user_id: int) -> list[dict]:
        try:
            existing = self.vector_db.get(where={"user_id": str(user_id)})
        except Exception as e:
            print(f"[ContactRag] 목록 조회 실패: {e}")
            return []

        metadatas = existing.get("metadatas") or []
        return [
            {
                "display_name": str(m.get("display_name") or ""),
                "normalized_name": str(m.get("normalized_name") or ""),
                "phone_number": str(m.get("phone_number") or ""),
            }
            for m in metadatas
        ]


_default_store: "ContactRagStore | None" = None


def get_default_contact_rag_store() -> "ContactRagStore | None":
    """Ollama 임베딩 + ChromaDB 기반 ContactRagStore 싱글턴. 실패 시 None."""
    global _default_store
    if _default_store is not None:
        return _default_store

    try:
        from server.rag.embedding_engine_factory import EmbeddingEngineFactory
        from server.rag.vector_db_factory import VectorDBFactory

        embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "ollama")
        embeddings = EmbeddingEngineFactory.get_embeddings(
            provider=embedding_provider, model_name=embedding_model
        )
        vector_db = VectorDBFactory.get_vector_db(
            "chroma",
            CHROMA_CONTACT_PATH,
            embeddings,
            collection_name=CHROMA_CONTACT_COLLECTION,
        )
        _default_store = ContactRagStore(vector_db, embeddings)
        return _default_store
    except Exception as e:
        print(f"[ContactRag] 기본 스토어 초기화 실패 (RAG 미사용): {e}")
        return None
