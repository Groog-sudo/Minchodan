import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from server.orchestration.llm_client_factory import LLMClientFactory
from server.rag.embedding_engine_factory import EmbeddingEngineFactory
from server.rag.vector_db_factory import VectorDBFactory

load_dotenv()


CONVENIENCE_QUERY_KEYWORDS = [
    "기관",
    "센터",
    "복지",
    "복지카드",
    "서비스",
    "병원",
    "재활",
    "안과",
    "연락처",
    "전화번호",
    "담당자",
    "보호자",
    "긴급",
    "응급",
    "보행훈련",
    "보조기기",
    "점자",
    "스크린리더",
    "안내견",
    "생활지원",
    "자립지원",
    "장애인",
    "시각장애",
    "김도윤",
    "이정희",
    "박서준",
    "정하늘",
    "최민아",
    "윤서연",
    "윤지수",
    "한빛",
    "새봄",
    "푸른나무",
    "생활안전협회",
    "보조기기센터",
]

CONVENIENCE_SYSTEM_PROMPT = """당신은 시각장애인 생활지원 통합 안내 AI입니다.
반드시 검색된 문서에 근거해서만 답변하세요.

[답변 규칙]
1. 한국어로 2~5문장만 답하세요.
2. 기관명, 전화번호, 주소, 운영시간, 신청 방법은 질문에 맞게 정확히 적으세요.
3. 문서에 없는 내용은 추측하지 말고, 확인되지 않았다고 말하세요.
4. 사용자가 바로 행동할 수 있도록 가장 중요한 정보부터 먼저 말하세요.
5. 보호자, 담당자, 병원, 긴급 연락망 질의는 번호와 관계를 명확히 구분해서 답하세요.
"""


def _project_root() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _join(values) -> str:
    if not values:
        return "없음"
    cleaned = [_text(value) for value in values if _text(value)]
    return ", ".join(cleaned) if cleaned else "없음"


def _format_address(address: dict | None) -> str:
    if not address:
        return "주소 정보 없음"
    parts = [
        _text(address.get("sido")),
        _text(address.get("sigungu")),
        _text(address.get("road_address")),
    ]
    parts = [part for part in parts if part]
    postal_code = _text(address.get("postal_code"))
    if postal_code:
        parts.append(f"우편번호 {postal_code}")
    return " / ".join(parts) if parts else "주소 정보 없음"


def _format_contact(contact: dict | None) -> str:
    if not contact:
        return "연락처 정보 없음"
    lines = []
    phone_fields = [
        ("대표전화", contact.get("representative_phone")),
        ("상담전화", contact.get("counseling_phone")),
        ("예약전화", contact.get("appointment_phone")),
        ("긴급전화", contact.get("emergency_phone")),
        ("사무실전화", contact.get("office_phone")),
        ("휴대전화", contact.get("mobile_phone")),
    ]
    for label, value in phone_fields:
        text_value = _text(value)
        if text_value and text_value.lower() != "none":
            lines.append(f"{label}: {text_value}")
    email = _text(contact.get("email"))
    website = _text(contact.get("website"))
    preferred = _text(contact.get("preferred_contact_method"))
    if preferred:
        lines.append(f"선호 연락 수단: {preferred}")
    if email:
        lines.append(f"이메일: {email}")
    if website:
        lines.append(f"웹사이트: {website}")
    return " / ".join(lines) if lines else "연락처 정보 없음"


def _format_business_hours(hours: dict | None) -> str:
    if not hours:
        return "운영시간 정보 없음"
    ordered = [
        ("평일", hours.get("weekday")),
        ("토요일", hours.get("saturday")),
        ("일요일", hours.get("sunday")),
        ("점심", hours.get("lunch_time")),
    ]
    parts = []
    for label, value in ordered:
        text_value = _text(value)
        if text_value:
            parts.append(f"{label}: {text_value}")
    return " / ".join(parts) if parts else "운영시간 정보 없음"


def _metadata_line(metadata: dict) -> str:
    return ", ".join(f"{key}={_text(value)}" for key, value in metadata.items() if _text(value))


def _build_dataset_overview(dataset_info: dict) -> Document:
    purpose = dataset_info.get("purpose", [])
    page_content = (
        f"데이터셋명: {_text(dataset_info.get('dataset_name'))}\n"
        f"버전: {_text(dataset_info.get('version'))}\n"
        f"언어: {_text(dataset_info.get('language'))}\n"
        f"용도: {_join(purpose)}\n"
        f"데이터 유형: {_text(dataset_info.get('data_type'))}\n"
        f"개인정보 고지: {_text(dataset_info.get('privacy_notice'))}"
    )
    return Document(
        page_content=page_content,
        metadata={
            "source_type": "dataset_info",
            "source_id": _text(dataset_info.get("dataset_name")) or "dataset_info",
            "title": _text(dataset_info.get("dataset_name"))
            or "시각장애인 생활지원 통합 안내 데이터",
            "category": "dataset_overview",
        },
    )


def build_convenience_documents(json_path: str | None = None) -> list[Document]:
    json_file = json_path or os.getenv(
        "CONVENIENCE_JSON_PATH",
        os.path.join(_project_root(), "data", "convenience_guidelines.json"),
    )
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"생활지원 JSON 파일이 존재하지 않습니다: {json_file}")

    with open(json_file, encoding="utf-8") as handle:
        data = json.load(handle)

    documents: list[Document] = []

    dataset_info = data.get("dataset_info") or {}
    if dataset_info:
        documents.append(_build_dataset_overview(dataset_info))

    for organization in data.get("organizations", []):
        organization_id = _text(organization.get("organization_id"))
        organization_name = _text(organization.get("name"))
        organization_type = _text(organization.get("organization_type_ko"))
        page_content = (
            f"기관명: {organization_name}\n"
            f"기관 구분: {organization_type}\n"
            f"설명: {_text(organization.get('description'))}\n"
            f"주소: {_format_address(organization.get('address'))}\n"
            f"연락처: {_format_contact(organization.get('contact'))}\n"
            f"운영시간: {_format_business_hours(organization.get('business_hours'))}\n"
            f"접근성: 점자표지={_text(organization.get('accessibility', {}).get('braille_signage'))}, "
            f"음성안내={_text(organization.get('accessibility', {}).get('voice_guidance'))}, "
            f"휠체어접근={_text(organization.get('accessibility', {}).get('wheelchair_accessible'))}, "
            f"안내견허용={_text(organization.get('accessibility', {}).get('guide_dog_allowed'))}\n"
            f"키워드: {_join(organization.get('keywords'))}\n"
            f"대표 안내: {_text(organization.get('rag_text'))}"
        )
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source_type": "organization",
                    "source_id": organization_id,
                    "title": organization_name,
                    "category": organization_type,
                },
            )
        )

        for service in organization.get("services", []):
            service_name = _text(service.get("service_name"))
            page_content = (
                f"기관명: {organization_name}\n"
                f"기관 구분: {organization_type}\n"
                f"서비스명: {service_name}\n"
                f"설명: {_text(service.get('description'))}\n"
                f"대상 사용자: {_join(service.get('target_users'))}\n"
                f"신청 방법: {_join(service.get('application_method'))}\n"
                f"필요 서류: {_join(service.get('required_documents'))}\n"
                f"기관 주소: {_format_address(organization.get('address'))}\n"
                f"기관 연락처: {_format_contact(organization.get('contact'))}\n"
                f"키워드: {_join(organization.get('keywords'))}\n"
                f"서비스 안내: {_text(service.get('description'))}"
            )
            documents.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "source_type": "service",
                        "source_id": _text(service.get("service_id")),
                        "parent_id": organization_id,
                        "title": service_name,
                        "category": organization_type,
                    },
                )
            )

    for person in data.get("people", []):
        person_id = _text(person.get("person_id"))
        name = _text(person.get("name"))
        person_type = _text(person.get("person_type_ko"))
        availability = (
            person.get("availability")
            or person.get("working_hours")
            or person.get("working_schedule")
        )
        page_content = (
            f"이름: {name}\n"
            f"구분: {person_type}\n"
            f"관계: {_text(person.get('relationship_to_user'))}\n"
            f"연결 사용자: {_text(person.get('related_user_id'))}\n"
            f"소속 기관: {_text(person.get('organization_id'))}\n"
            f"연락처: {_format_contact(person.get('contact'))}\n"
            f"가능 시간 또는 근무 일정: {_text(availability)}\n"
            f"권한/역할: {_join(person.get('authorized_actions') or person.get('responsibilities') or person.get('specialties'))}\n"
            f"의학/지원 메모: {_join(person.get('medical_notes'))}\n"
            f"키워드 요약: {_text(person.get('rag_text'))}"
        )
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source_type": "person",
                    "source_id": person_id,
                    "title": name,
                    "category": person_type,
                },
            )
        )

    for emergency_contact in data.get("emergency_contacts", []):
        emergency_id = _text(emergency_contact.get("emergency_id"))
        page_content = (
            f"긴급 구분: {_text(emergency_contact.get('category_ko'))}\n"
            f"이름: {_text(emergency_contact.get('name'))}\n"
            f"전화번호: {_text(emergency_contact.get('phone'))}\n"
            f"가능 시간: {_text(emergency_contact.get('available_hours'))}\n"
            f"설명: {_text(emergency_contact.get('description'))}\n"
            f"키워드: {_join(emergency_contact.get('keywords'))}\n"
            f"대표 안내: {_text(emergency_contact.get('rag_text'))}"
        )
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source_type": "emergency_contact",
                    "source_id": emergency_id,
                    "title": _text(emergency_contact.get("name")),
                    "category": _text(emergency_contact.get("category_ko")),
                },
            )
        )

    for faq in data.get("faq", []):
        faq_id = _text(faq.get("faq_id"))
        page_content = (
            f"질문: {_text(faq.get('question'))}\n"
            f"답변: {_text(faq.get('answer'))}\n"
            f"카테고리: {_text(faq.get('category'))}\n"
            f"관련 기관: {_join(faq.get('related_organization_ids'))}\n"
            f"관련 인물: {_join(faq.get('related_person_ids'))}\n"
            f"키워드: {_join(faq.get('keywords'))}\n"
            f"검색용 텍스트: {_text(faq.get('rag_text'))}"
        )
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source_type": "faq",
                    "source_id": faq_id,
                    "title": _text(faq.get("question")),
                    "category": _text(faq.get("category")),
                },
            )
        )

    for rag_document in data.get("rag_documents", []):
        document_id = _text(rag_document.get("document_id"))
        page_content = (
            f"문서 제목: {_text(rag_document.get('title'))}\n"
            f"문서 유형: {_text(rag_document.get('document_type'))}\n"
            f"내용: {_text(rag_document.get('content'))}\n"
            f"소스 ID: {_join(rag_document.get('source_ids'))}\n"
            f"메타데이터: {_metadata_line(rag_document.get('metadata') or {})}"
        )
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source_type": "rag_document",
                    "source_id": document_id,
                    "title": _text(rag_document.get("title")),
                    "category": _text(rag_document.get("document_type")),
                },
            )
        )

    if not documents:
        raise ValueError("생활지원 RAG로 빌드할 문서가 비어 있습니다.")

    return documents


def build_convenience_database(
    json_path: str | None = None,
    persist_directory: str | None = None,
    embeddings=None,
    collection_name: str | None = None,
) -> Chroma:
    json_file = json_path or os.getenv(
        "CONVENIENCE_JSON_PATH",
        os.path.join(_project_root(), "data", "convenience_guidelines.json"),
    )
    persist_dir = persist_directory or os.getenv(
        "CONVENIENCE_CHROMA_PATH",
        os.path.join(_project_root(), "data", "chroma_db", "convenience_guidelines"),
    )
    collection = collection_name or os.getenv(
        "CONVENIENCE_CHROMA_COLLECTION", "convenience_guidelines"
    )

    if embeddings is None:
        embeddings = EmbeddingEngineFactory.get_embeddings(
            provider=os.getenv("CONVENIENCE_EMBEDDING_PROVIDER", "ollama"),
            model_name=os.getenv("CONVENIENCE_EMBEDDING_MODEL", "nomic-embed-text"),
        )

    os.makedirs(persist_dir, exist_ok=True)

    documents = build_convenience_documents(json_file)
    db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection,
        collection_metadata={"hnsw:space": "cosine"},
    )

    if hasattr(db, "persist"):
        db.persist()

    return db


class ConvenienceKnowledgeBase:
    """시각장애인 생활지원 안내용 RAG 검색 및 응답 생성기."""

    def __init__(self, vector_db: VectorStore):
        self.vector_db = vector_db

    def search(self, question: str, k: int = 5) -> list[dict]:
        query = _text(question)
        if not query:
            return []

        results = self.vector_db.similarity_search_with_score(query, k=k)
        formatted_results = []
        for document, score in results:
            formatted_results.append(
                {
                    "content": document.page_content,
                    "metadata": dict(document.metadata or {}),
                    "score": float(score),
                }
            )
        return formatted_results

    async def answer(self, question: str, k: int = 5) -> dict:
        query = _text(question)
        start_time = time.perf_counter()
        results = self.search(query, k=k)
        latency_ms = (time.perf_counter() - start_time) * 1000

        if not results:
            return {
                "query": query,
                "answer": "관련 정보를 찾지 못했습니다. 더 구체적으로 말씀해 주세요.",
                "results": [],
                "latency_ms": round(latency_ms, 2),
                "used_fallback_llm": True,
            }

        context_lines = []
        for index, result in enumerate(results[:k], 1):
            metadata = result.get("metadata", {})
            context_lines.append(
                f"[문서 {index}]\n"
                f"제목: {_text(metadata.get('title'))}\n"
                f"유형: {_text(metadata.get('source_type'))}\n"
                f"카테고리: {_text(metadata.get('category'))}\n"
                f"내용:\n{_text(result.get('content'))}"
            )

        user_prompt = (
            f"[사용자 질문]\n{query}\n\n"
            f"[검색 문서]\n{chr(10).join(context_lines)}\n\n"
            "위 검색 문서만 바탕으로 답변하세요. 질문에 맞는 기관명, 연락처, 주소, 운영시간, 신청 방법, 보호자 또는 담당자 정보를 정확히 알려주세요. "
            "문서에 없는 내용은 추측하지 말고, 확인되지 않았다고 말하세요."
        )

        messages = [
            {"role": "system", "content": CONVENIENCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            client = LLMClientFactory.get_client(provider="gemini")
            response = await client.ainvoke(messages)
            answer = _text(response.content)
        except Exception as exc:
            return {
                "query": query,
                "answer": "관련 정보를 찾았지만 답변 생성에 실패했습니다. 다시 말씀해 주세요.",
                "results": results,
                "latency_ms": round(latency_ms, 2),
                "used_fallback_llm": True,
                "error": str(exc),
            }

        return {
            "query": query,
            "answer": answer,
            "results": results,
            "latency_ms": round(latency_ms, 2),
            "used_fallback_llm": False,
        }


_default_service: ConvenienceKnowledgeBase | None = None


def looks_like_convenience_query(question: str) -> bool:
    text = _text(question)
    if not text:
        return False
    return any(keyword in text for keyword in CONVENIENCE_QUERY_KEYWORDS)


def get_default_convenience_service() -> ConvenienceKnowledgeBase | None:
    global _default_service
    if _default_service is not None:
        return _default_service

    try:
        embeddings = EmbeddingEngineFactory.get_embeddings(
            provider=os.getenv("CONVENIENCE_EMBEDDING_PROVIDER", "ollama"),
            model_name=os.getenv("CONVENIENCE_EMBEDDING_MODEL", "nomic-embed-text"),
        )
        vector_db = VectorDBFactory.get_vector_db(
            "chroma",
            os.getenv(
                "CONVENIENCE_CHROMA_PATH",
                os.path.join(_project_root(), "data", "chroma_db", "convenience_guidelines"),
            ),
            embeddings,
            collection_name=os.getenv("CONVENIENCE_CHROMA_COLLECTION", "convenience_guidelines"),
        )
        _default_service = ConvenienceKnowledgeBase(vector_db)
        return _default_service
    except Exception as exc:
        print(f"[Convenience RAG] 기본 서비스 초기화 실패: {exc}")
        return None


async def answer_convenience_question(question: str, k: int = 5) -> dict:
    service = get_default_convenience_service()
    if service is None:
        return {
            "query": _text(question),
            "answer": "생활지원 안내 검색 저장소를 불러오지 못했습니다.",
            "results": [],
            "latency_ms": 0.0,
            "used_fallback_llm": True,
        }
    return await service.answer(question, k=k)


if __name__ == "__main__":
    print("convenience_rag.py 스모크 테스트 실행")
    try:
        db = build_convenience_database()
        print(f"DB 빌드 성공: {db is not None}")
        service = ConvenienceKnowledgeBase(db)
        sample_question = "한빛 시각장애인 자립지원센터 보행훈련은 어디서 받을 수 있나요?"
        print(service.search(sample_question, k=3))
    except Exception as exc:
        print(f"스모크 테스트 실패: {exc}")
