import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.gates.reflex_gate import HIGH_RISK_CLASSES

# 반사 위험도 SSOT 계약 (docs/design/risk_ssot_contract.md §2).
# 서버 게이트와 단말 온디바이스 게이트가 반드시 동일하게 유지해야 하는
# 고위험 5종 클래스와 최소 confidence. 값 변경 시 서버·단말 코드와
# 계약 문서 §2 표를 같은 커밋에서 함께 수정한다.
SSOT_HIGH_RISK: dict[str, float] = {
    "barricade": 0.35,
    "bench": 0.3,
    "bicycle": 0.3,
    "bollard": 0.3,
    "bus": 0.35,
    "car": 0.35,
    "carrier": 0.3,
    "cat": 0.3,
    "chair": 0.3,
    "dog": 0.3,
    "fire_hydrant": 0.35,
    "kiosk": 0.3,
    "motorcycle": 0.35,
    "movable_signage": 0.3,
    "parking_meter": 0.35,
    "person": 0.3,
    "pole": 0.3,
    "potted_plant": 0.3,
    "power_controller": 0.3,
    "scooter": 0.3,
    "stop": 0.35,
    "stroller": 0.3,
    "table": 0.3,
    "traffic_light": 0.35,
    "traffic_light_controller": 0.35,
    "traffic_sign": 0.35,
    "tree_trunk": 0.3,
    "truck": 0.35,
    "wheelchair": 0.3,
}

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAMERA_VIEW_PATH = os.path.join(_BASE_DIR, "client", "src", "components", "CameraView.tsx")


def _parse_client_class_min_confidence() -> dict[str, float]:
    """CameraView.tsx의 CLASS_MIN_CONFIDENCE 객체 리터럴을 텍스트 파싱한다.

    TSX를 직접 실행할 수 없으므로 선언 블록을 정규식으로 추출한다.
    선언 형식이 바뀌어 파싱이 실패하면 빈 dict 대신 예외를 내
    테스트가 조용히 통과하는 것을 막는다.
    """
    with open(_CAMERA_VIEW_PATH, encoding="utf-8") as f:
        source = f.read()

    match = re.search(
        r"const CLASS_MIN_CONFIDENCE:\s*Record<string,\s*number>\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(
            "CameraView.tsx에서 CLASS_MIN_CONFIDENCE 선언을 찾지 못했습니다. "
            "선언 형식이 바뀌었다면 tests/test_risk_ssot.py의 파서를 함께 갱신하십시오."
        )

    entries = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([0-9.]+)", match.group(1))
    if not entries:
        raise AssertionError("CLASS_MIN_CONFIDENCE 항목 파싱 결과가 비어 있습니다.")
    return {name: float(value) for name, value in entries}


def test_server_gate_matches_ssot():
    """서버 반사 게이트의 고위험 클래스·confidence가 계약 §2와 일치해야 한다."""
    assert HIGH_RISK_CLASSES == SSOT_HIGH_RISK, (
        "server/detection/gates/reflex_gate.py의 HIGH_RISK_CLASSES가 SSOT 계약과 다릅니다. "
        "docs/design/risk_ssot_contract.md §2 절차에 따라 양측을 같은 커밋에서 수정하십시오."
    )


def test_client_gate_matches_ssot():
    """단말 온디바이스 게이트의 SSOT 5종 confidence가 계약 §2와 일치해야 한다."""
    client_map = _parse_client_class_min_confidence()
    for class_name, min_conf in SSOT_HIGH_RISK.items():
        assert (
            class_name in client_map
        ), f"CameraView.tsx CLASS_MIN_CONFIDENCE에 SSOT 클래스 {class_name!r}가 없습니다."
        assert client_map[class_name] == min_conf, (
            f"{class_name!r} confidence 불일치: 단말={client_map[class_name]}, "
            f"SSOT={min_conf} (docs/design/risk_ssot_contract.md §2)"
        )


def test_client_extension_does_not_conflict_with_ssot():
    """단말 전용 확장 목록은 허용하되, SSOT 5종과 다른 값으로 재정의할 수 없다."""
    client_map = _parse_client_class_min_confidence()
    conflicts = {
        name: value
        for name, value in client_map.items()
        if name in SSOT_HIGH_RISK and value != SSOT_HIGH_RISK[name]
    }
    assert not conflicts, f"SSOT 5종을 다른 값으로 재정의한 항목: {conflicts}"
