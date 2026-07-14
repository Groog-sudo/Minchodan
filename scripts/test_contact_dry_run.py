# -*- coding: utf-8 -*-
"""연락처 기능 드라이런 스모크 테스트 (실제 전화/tel: 없음, RAG 영속).

공기계·에뮬레이터 등 통화 불가 환경에서 확인할 항목:
- STT 브리지 저장/전화 분기
- RAG(ChromaDB) 저장/조회
- 서버 재시작 시뮬(RAM 비운 뒤 RAG 조회)
- dial_action / contact_save WS 페이로드 계약

Ollama가 떠 있지 않으면 EmbeddingEngineFactory가 MockEmbeddingEngine으로
폴백하므로 Ollama 없이도 저장/조회 흐름은 검증된다.
"""

import asyncio
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.rag.contact_rag import get_default_contact_rag_store
from server.services.device_registry_service import (
    ensure_device_registered,
    get_cached_device_ids,
)
from server.stt.contact_service import ContactService
from server.stt.contact_store import ContactStore
from server.stt.stt_schema import SegmentOut, SttTranscribeResult
from server.stt.stt_to_llm_bridge import SttToLlmBridge

DEVICE_UUID = os.getenv("CONTACT_SMOKE_DEVICE", "dev-contact-smoke")


def _stt(text: str) -> SttTranscribeResult:
    return SttTranscribeResult(
        model_name="dry-run",
        text=text,
        language="ko",
        duration=1.0,
        segments=[SegmentOut(start=0.0, end=1.0, text=text)],
        has_input=True,
        saved_file="dry-run.wav",
    )


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


async def main() -> int:
    _print_section("1) 단말 등록 (ensure_device_registered)")
    user_id, device_pk = await ensure_device_registered(DEVICE_UUID, "android")
    print(f"device_uuid={DEVICE_UUID}, user_id={user_id}, device_id={device_pk}")

    _print_section("2) RAG 스토어 초기화")
    store = get_default_contact_rag_store()
    if store is None:
        print("FAIL: RAG 스토어 초기화 실패 (ChromaDB 경로/임베딩 확인 필요)")
        return 1
    print(f"RAG store OK: {store.__class__.__name__}")

    _print_section("3) 음성 저장 시뮬: 엄마 번호 저장")
    bridge = SttToLlmBridge()
    save_result = await bridge.invoke_existing_llm(
        _stt("엄마 번호는 010-1234-5678 저장해줘"), DEVICE_UUID
    )
    print(f"source={save_result.get('source')}")
    print(f"guidance={save_result.get('guidance_text')}")
    print(f"contact_save={save_result.get('contact_save')}")
    assert save_result.get("source") == "contact-save-success"

    _print_section("4) RAG 저장 확인 (list_by_user)")
    contacts = store.list_by_user(user_id)
    엄마_rows = [c for c in contacts if c["normalized_name"] == "엄마"]
    if not 엄마_rows:
        print("FAIL: RAG에 엄마 행 없음")
        return 1
    print(f"RAG OK: {엄마_rows[0]}")

    _print_section("5) 서버 재시작 시뮬 (RAM 캐시 비우기)")
    ContactStore._contacts.clear()
    cached = get_cached_device_ids(DEVICE_UUID)
    print(f"device_registry 캐시={cached}")

    _print_section("6) 음성 전화 시뮬 (tel: 호출 없음, dial_action만 확인)")
    call_result = await bridge.invoke_existing_llm(
        _stt("엄마한테 전화 걸어줘"), DEVICE_UUID
    )
    print(f"source={call_result.get('source')}")
    print(f"guidance={call_result.get('guidance_text')}")
    dial = call_result.get("dial_action")
    print(f"dial_action={dial}")
    assert call_result.get("source") == "contact-call-success"
    assert dial and dial.get("phone_number") == "010-1234-5678"
    print("DRY-RUN: Linking.openURL(tel:...) 단계는 스킵 (공기계 통화 불가)")

    _print_section("7) hydrate_cache (WS 재접속 시뮬)")
    ContactStore._contacts.clear()
    n = await ContactService.hydrate_cache(DEVICE_UUID)
    print(f"hydrated={n}, RAM lookup={ContactStore.lookup(DEVICE_UUID, '엄마')}")

    _print_section("결과")
    print("PASS - 저장/RAG/재시작 후 조회/dial_action 계약 모두 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
