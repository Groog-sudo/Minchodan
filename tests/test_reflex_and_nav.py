import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from server.tts.reflex_clip_sender import _resolve_reflex_patterns


def test_reflex_guidelines_loading():
    """reflex_guidelines.json 파일이 정상 구조로 존재하며 파싱되는지 검증합니다."""
    guidelines_path = os.path.join(project_root, "data", "reflex_guidelines.json")
    assert os.path.exists(guidelines_path), "reflex_guidelines.json 파일이 누락되었습니다."

    with open(guidelines_path, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list), "JSON 루트는 리스트 형식이어야 합니다."
    assert len(data) > 0, "가이드라인이 비어있습니다."

    # 필수 스키마 검증
    for entry in data:
        assert "beep_pattern" in entry
        assert "haptic_pattern" in entry
        assert "risk_level" in entry
        assert isinstance(entry["beep_pattern"], dict)
        assert isinstance(entry["haptic_pattern"], dict)


def test_reflex_pattern_resolving():
    """alert_id에 따라 적절한 비프/햅틱 패턴이 정상 도출되는지 검증합니다."""
    # 1. 차도 진입 케이스 검증
    beep, haptic = _resolve_reflex_patterns("roadway")
    assert beep["frequency"] == 2000
    assert haptic["intensity"] == "heavy"

    # 2. 계단/단차 진입 케이스 검증
    beep, haptic = _resolve_reflex_patterns("surface_stairs")
    assert beep["frequency"] == 1800
    assert haptic["pattern"] == "triple"

    # 3. 폴백 케이스 검증 (알 수 없는 경고)
    beep, haptic = _resolve_reflex_patterns("unknown_danger")
    assert beep["frequency"] == 1000
    assert haptic["intensity"] == "medium"
