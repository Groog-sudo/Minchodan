import sys

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.rag.convenience_dial_resolver import resolve_convenience_dial

pytestmark = pytest.mark.ollama


def test_resolve_organization_dial() -> None:
    target = resolve_convenience_dial("실로암시각장애인복지관에 전화 걸어줘")
    assert target is not None
    assert target.contact_name == "실로암시각장애인복지관"
    assert target.phone_number == "028800500"
    assert target.source_type == "organization"


def test_resolve_mobility_support_dial() -> None:
    target = resolve_convenience_dial("복지콜에 전화 연결해줘")
    assert target is not None
    assert target.contact_name == "서울특별시 시각장애인 플러스 지원센터"
    assert target.phone_number == "16004477"


def test_private_guardian_contact_is_not_in_public_dataset() -> None:
    assert resolve_convenience_dial("보호자에게 전화 연결해줘") is None
