# -*- coding: utf-8 -*-
"""RAG(ChromaDB) 기반 ContactService 영속화 검증.

MockEmbeddingEngine + 임시 ChromaDB 디렉토리로 Ollama 없이도 저장/조회/캐시
복구 흐름을 검증한다. LLM 환각 위험은 metadata.phone_number를 직접 꺼내는
설계로 이미 제거되어 있어, 이 테스트는 "이름 -> 번호" 정합성을 확인한다.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from langchain_community.vectorstores import Chroma

from server.rag.contact_rag import ContactRagStore
from server.rag.embedding_engine_factory import MockEmbeddingEngine
from server.stt.contact_service import ContactService
from server.stt.contact_store import ContactStore


@pytest.fixture
def rag_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    embeddings = MockEmbeddingEngine()
    vector_db = Chroma(
        persist_directory=str(tmp_path / "chroma_contacts"),
        embedding_function=embeddings,
        collection_name="user_contacts_test",
        collection_metadata={"hnsw:space": "cosine"},
    )
    store = ContactRagStore(vector_db, embeddings)

    monkeypatch.setattr(
        ContactService, "_get_store", staticmethod(lambda: store)
    )
    monkeypatch.setattr(
        "server.stt.contact_service.get_cached_device_ids",
        lambda device_uuid: (1, 1) if device_uuid == "dev-contact-001" else (None, None),
    )

    ContactStore._contacts.clear()
    yield store
    ContactStore._contacts.clear()


@pytest.mark.asyncio
async def test_contact_service_save_and_lookup_from_rag(rag_env) -> None:
    saved = await ContactService.save("dev-contact-001", "엄마", "010-1234-5678")
    assert saved is True

    ContactStore._contacts.clear()
    phone = await ContactService.lookup("dev-contact-001", "엄마")
    assert phone == "010-1234-5678"


@pytest.mark.asyncio
async def test_contact_service_hydrate_cache_on_reconnect(rag_env) -> None:
    await ContactService.save("dev-contact-001", "아빠", "010-9876-5432")
    ContactStore._contacts.clear()

    count = await ContactService.hydrate_cache("dev-contact-001")
    assert count == 1
    assert ContactStore.lookup("dev-contact-001", "아빠") == "010-9876-5432"


@pytest.mark.asyncio
async def test_contact_rag_store_overwrite_updates_phone(rag_env) -> None:
    store = rag_env
    store.save(
        user_id=1,
        device_uuid="dev-contact-001",
        display_name="엄마",
        normalized_name="엄마",
        phone_number="010-1111-2222",
    )
    store.save(
        user_id=1,
        device_uuid="dev-contact-001",
        display_name="엄마",
        normalized_name="엄마",
        phone_number="010-3333-4444",
    )

    contacts = store.list_by_user(1)
    엄마_rows = [c for c in contacts if c["normalized_name"] == "엄마"]
    assert len(엄마_rows) == 1
    assert 엄마_rows[0]["phone_number"] == "010-3333-4444"

    assert store.lookup(1, "엄마") == "010-3333-4444"


@pytest.mark.asyncio
async def test_contact_service_lookup_misses_unknown_name(rag_env) -> None:
    await ContactService.save("dev-contact-001", "엄마", "010-1234-5678")
    ContactStore._contacts.clear()

    phone = await ContactService.lookup("dev-contact-001", "삼촌")
    assert phone is None
