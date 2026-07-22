"""convenience_guidelines.json 기반 전화 연결 대상 해석."""

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.stt.phone_utils import normalize_phone_to_dialable


@dataclass(frozen=True)
class DialTarget:
    contact_name: str
    phone_number: str
    source_type: str
    source_id: str


def _project_root() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pick_phone_from_contact(contact: dict | None) -> str | None:
    if not contact:
        return None
    for key in (
        "representative_phone",
        "counseling_phone",
        "appointment_phone",
        "emergency_phone",
        "office_phone",
        "mobile_phone",
        "phone",
    ):
        candidate = normalize_phone_to_dialable(contact.get(key))
        if candidate:
            return candidate
    return None


def _load_guidelines() -> dict[str, Any]:
    json_file = os.getenv(
        "CONVENIENCE_JSON_PATH",
        os.path.join(_project_root(), "data", "convenience_guidelines.json"),
    )
    with open(json_file, encoding="utf-8") as handle:
        return json.load(handle)


def _iter_dial_candidates(data: dict[str, Any]) -> list[tuple[str, str, str, str, str]]:
    """(match_name, contact_name, phone, source_type, source_id) 목록."""
    candidates: list[tuple[str, str, str, str, str]] = []

    for organization in data.get("organizations", []):
        org_name = _text(organization.get("name"))
        short_name = _text(organization.get("short_name"))
        phone = _pick_phone_from_contact(organization.get("contact"))
        if org_name and phone:
            for label in (org_name, short_name):
                if label:
                    candidates.append(
                        (
                            label,
                            org_name,
                            phone,
                            "organization",
                            _text(organization.get("organization_id")),
                        )
                    )

    for person in data.get("people", []):
        name = _text(person.get("name"))
        phone = _pick_phone_from_contact(person.get("contact"))
        if name and phone:
            candidates.append((name, name, phone, "person", _text(person.get("person_id"))))

    for emergency in data.get("emergency_contacts", []):
        name = _text(emergency.get("name"))
        phone = normalize_phone_to_dialable(emergency.get("phone"))
        if name and phone:
            candidates.append(
                (
                    name,
                    name,
                    phone,
                    "emergency_contact",
                    _text(emergency.get("emergency_id")),
                )
            )
        for entry in emergency.get("contact_order") or []:
            entry_name = _text(entry.get("name"))
            entry_phone = normalize_phone_to_dialable(entry.get("phone"))
            if entry_name and entry_phone:
                candidates.append(
                    (
                        entry_name,
                        entry_name,
                        entry_phone,
                        "emergency_contact",
                        _text(emergency.get("emergency_id")),
                    )
                )
            guardian_label = f"{entry_name} 보호자" if entry_name else ""
            if guardian_label:
                candidates.append(
                    (
                        guardian_label,
                        guardian_label,
                        entry_phone or "",
                        "emergency_contact",
                        _text(emergency.get("emergency_id")),
                    )
                )

    return [item for item in candidates if item[2]]


def resolve_convenience_dial(text: str | None) -> DialTarget | None:
    """발화 문맥에서 convenience 코퍼스 연락처를 찾는다."""
    query = _text(text)
    if not query:
        return None

    data = _load_guidelines()
    best: tuple[int, DialTarget] | None = None

    for match_name, contact_name, phone, source_type, source_id in _iter_dial_candidates(data):
        if match_name not in query:
            continue
        score = len(match_name)
        target = DialTarget(
            contact_name=contact_name,
            phone_number=phone,
            source_type=source_type,
            source_id=source_id,
        )
        if best is None or score > best[0]:
            best = (score, target)

    if best:
        return best[1]

    lowered = query.replace(" ", "")
    guardian_aliases = ("보호자", "보호자연락망", "보호자연락")
    if any(alias in lowered for alias in guardian_aliases):
        for _, contact_name, phone, source_type, source_id in _iter_dial_candidates(data):
            if "보호자" in contact_name:
                return DialTarget(
                    contact_name=contact_name,
                    phone_number=phone,
                    source_type=source_type,
                    source_id=source_id,
                )

    return None
