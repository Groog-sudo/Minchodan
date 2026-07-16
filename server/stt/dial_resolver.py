"""STT 발화에서 전화 연결 대상을 해석한다."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.db.connection import async_sessionmaker_factory
from server.db.repositories import UserRepository
from server.rag.convenience_dial_resolver import resolve_convenience_dial
from server.services.device_registry_service import get_cached_device_ids
from server.stt.phone_utils import (
    is_dial_intent,
    normalize_phone_to_dialable,
    resolve_emergency_number,
)


async def _lookup_guardian_phone(device_uuid: str) -> tuple[str | None, str]:
    user_id, _ = get_cached_device_ids(device_uuid)
    if user_id is None:
        return None, "보호자"

    async with async_sessionmaker_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if user is None:
            return None, "보호자"
        phone = normalize_phone_to_dialable(user.guardian_phone)
        label = user.name or "보호자"
        if phone:
            return phone, f"{label} 보호자"
    return None, "보호자"


async def resolve_dial_action(device_id: str, text: str | None) -> dict | None:
    """전화 연결 의도가 있으면 bridge_result 형태 dict를 반환한다."""
    normalized = (text or "").strip()
    if not is_dial_intent(normalized):
        return None

    emergency_number, emergency_label = resolve_emergency_number(normalized)
    if emergency_number:
        return {
            "guidance_text": f"{emergency_label}로 전화를 연결합니다.",
            "used_fallback_llm": True,
            "source": "stt-dial-emergency",
            "dial_action": {
                "contact_name": emergency_label,
                "phone_number": emergency_number,
            },
        }

    if "보호자" in normalized:
        phone, label = await _lookup_guardian_phone(device_id)
        if phone:
            return {
                "guidance_text": f"{label}에게 전화를 연결합니다.",
                "used_fallback_llm": True,
                "source": "stt-dial-guardian-db",
                "dial_action": {
                    "contact_name": label,
                    "phone_number": phone,
                },
            }

    convenience_target = resolve_convenience_dial(normalized)
    if convenience_target:
        return {
            "guidance_text": f"{convenience_target.contact_name}로 전화를 연결합니다.",
            "used_fallback_llm": True,
            "source": "stt-dial-convenience",
            "dial_action": {
                "contact_name": convenience_target.contact_name,
                "phone_number": convenience_target.phone_number,
                "source_type": convenience_target.source_type,
                "source_id": convenience_target.source_id,
            },
        }

    return {
        "guidance_text": "전화를 걸 연락처를 찾지 못했습니다. 기관명이나 이름을 다시 말씀해 주세요.",
        "used_fallback_llm": True,
        "source": "stt-dial-not-found",
    }
