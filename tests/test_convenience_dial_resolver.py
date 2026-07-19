import sys

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.rag.convenience_dial_resolver import resolve_convenience_dial

pytestmark = pytest.mark.ollama


def test_resolve_organization_dial() -> None:
    target = resolve_convenience_dial("서울시 장애인 생활지원센터에 전화 걸어줘")
    assert target is not None
    assert target.contact_name == "서울시 장애인 생활지원센터"
    assert target.phone_number == "02222223690"
    assert target.source_type == "organization"


def test_resolve_guardian_contact_from_convenience() -> None:
    target = resolve_convenience_dial("윤대근 보호자에게 전화 연결해줘")
    assert target is not None
    assert "보호자" in target.contact_name
    assert target.phone_number == "01095903210"
