import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from types import SimpleNamespace

import pytest

import server.stt.stt_to_llm_bridge as stt_bridge_module
from server.stt.stt_schema import SegmentOut, SttTranscribeResult
from server.stt.stt_to_llm_bridge import SttToLlmBridge

# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - STT 결과를 오케스트레이션 입력으로 변환하는 틀을 검증.
# - invoke_existing_llm의 빈 입력 폴백/정상 응답 매핑을 검증.
#
# [하드 코딩 부분]
# - 목적지 파싱 -> navigation 연동 핵심 분기를 고정 케이스로 검증.
# - 최소 핵심 시나리오:
#   1) Wake-up 명령으로 WAITING_FOR_DESTINATION 상태 전환
#   2) Shutdown 명령으로 IDLE 상태 및 경로 초기화
#   3) WAITING 상태에서 목적지 입력 시 경로 수립 성공
#   4) 목적지 검색 실패 시 navigation-setup-fail 폴백


def _make_stt_result(text: str, has_input: bool = True) -> SttTranscribeResult:
    return SttTranscribeResult(
        model_name="faster-whisper-base",
        text=text,
        language="ko",
        duration=1.0,
        segments=[SegmentOut(start=0.0, end=1.0, text=text)] if has_input else [],
        has_input=has_input,
        saved_file=Path("dummy.wav").name,
    )


class _FakeNavManager:
    """테스트에서 navigation 상태 전이와 경로 갱신 호출만 추적한다."""

    def __init__(self, status: str = "IDLE", detection_enabled: bool = False):
        self.status = status
        self.last_route: list[dict] = []
        self.session = SimpleNamespace(lat=None, lon=None)
        self.awaiting_question = False
        self.awaiting_intent = False
        self.detection_enabled = detection_enabled
        self.pending_poi_candidates: list[dict] | None = None

    def get_status(self, device_id: str) -> str:
        _ = device_id
        return self.status

    def set_status(self, device_id: str, status: str) -> None:
        _ = device_id
        self.status = status
        if status != "WAITING_FOR_POI_CONFIRMATION":
            self.pending_poi_candidates = None

    def set_pending_poi_candidates(self, device_id: str, candidates: list[dict] | None) -> None:
        _ = device_id
        self.pending_poi_candidates = candidates

    def get_pending_poi_candidates(self, device_id: str) -> list[dict] | None:
        _ = device_id
        return self.pending_poi_candidates

    def update_route(self, device_id: str, waypoints: list[dict]) -> None:
        _ = device_id
        self.last_route = waypoints

    def _get_or_create_session(self, device_id: str):
        _ = device_id
        return self.session

    def is_awaiting_question(self, device_id: str) -> bool:
        _ = device_id
        return self.awaiting_question

    def set_awaiting_question(self, device_id: str, value: bool) -> None:
        _ = device_id
        self.awaiting_question = value

    def is_awaiting_intent(self, device_id: str) -> bool:
        _ = device_id
        return self.awaiting_intent

    def set_awaiting_intent(self, device_id: str, value: bool) -> None:
        _ = device_id
        self.awaiting_intent = value

    def is_detection_enabled(self, device_id: str) -> bool:
        _ = device_id
        return self.detection_enabled

    def set_detection_enabled(self, device_id: str, enabled: bool) -> None:
        _ = device_id
        self.detection_enabled = enabled
        if not enabled and self.status == "WAITING_FOR_DESTINATION":
            self.status = "IDLE"
        if not enabled:
            self.awaiting_intent = False


def test_build_orch_input_success() -> None:
    bridge = SttToLlmBridge()
    result = _make_stt_result("전방에 장애물이 있습니다")

    orch_input = bridge.build_orch_input(result)

    assert orch_input["event"]["source"] == "stt"
    assert orch_input["rag_context"] == "전방에 장애물이 있습니다"
    assert orch_input["detected_classes"] == ["speech_to_text"]


@pytest.mark.asyncio
async def test_invoke_existing_llm_empty_fallback() -> None:
    bridge = SttToLlmBridge()
    # 쿨다운 상태 초기화 (다른 테스트 오염 방지)
    SttToLlmBridge._last_empty_notice_ts.pop("test-device", None)
    result = _make_stt_result("", has_input=False)

    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "stt-bridge-empty"
    assert response["used_fallback_llm"] is True
    assert "인식되지" in response["guidance_text"]

    # 쿨다운 내 재호출은 무음 억제
    suppressed = await bridge.invoke_existing_llm(result, "test-device")
    assert suppressed["source"] == "stt-bridge-empty-suppressed"
    assert suppressed["guidance_text"] == ""
    SttToLlmBridge._last_empty_notice_ts.pop("test-device", None)


@pytest.mark.asyncio
async def test_invoke_existing_llm_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import server.navigation.manager as nav_manager_module

    async def _fake_run_orchestrator(state: dict) -> dict:
        assert state["event"]["source"] == "stt"
        return {
            "guidance_text": "오른쪽으로 피해 이동하세요",
            "used_fallback_llm": False,
        }

    monkeypatch.setattr(stt_bridge_module, "run_orchestrator", _fake_run_orchestrator)
    # 탐지 ON일 때만 장애물 orch 경로를 탄다(2026-07-13 분기).
    monkeypatch.setattr(
        nav_manager_module,
        "nav_manager",
        _FakeNavManager(status="IDLE", detection_enabled=True),
    )

    bridge = SttToLlmBridge()
    result = _make_stt_result("테스트")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response == {
        "guidance_text": "오른쪽으로 피해 이동하세요",
        "used_fallback_llm": False,
        "source": "stt-bridge",
    }


@pytest.mark.asyncio
async def test_invoke_existing_llm_error_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import server.navigation.manager as nav_manager_module

    async def _fake_run_orchestrator(_state: dict) -> dict:
        raise RuntimeError("forced-error")

    monkeypatch.setattr(stt_bridge_module, "run_orchestrator", _fake_run_orchestrator)
    monkeypatch.setattr(
        nav_manager_module,
        "nav_manager",
        _FakeNavManager(status="IDLE", detection_enabled=True),
    )

    bridge = SttToLlmBridge()
    result = _make_stt_result("테스트")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "stt-bridge-error"
    assert response["used_fallback_llm"] is True


@pytest.mark.asyncio
async def test_detection_off_routes_to_free_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """탐지 OFF면 일반 발화가 물체탐지 orch가 아니라 자유 질문으로 간다."""
    import server.navigation.manager as nav_manager_module

    async def _fake_answer(self, _device_id: str, question: str) -> dict:
        return {
            "guidance_text": f"답:{question}",
            "used_fallback_llm": False,
            "source": "question-llm",
        }

    monkeypatch.setattr(
        nav_manager_module,
        "nav_manager",
        _FakeNavManager(status="IDLE", detection_enabled=False),
    )
    monkeypatch.setattr(SttToLlmBridge, "_answer_free_question", _fake_answer)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("날씨 알려줘"), "test-device")

    assert response["source"] == "question-llm"
    assert "날씨" in response["guidance_text"]


@pytest.mark.asyncio
async def test_destination_wait_question_escapes_to_free_qa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """목적지 대기 중 질문형 발화는 POI 검색 대신 자유 질문으로 탈출한다."""
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION", detection_enabled=True)

    async def _fake_answer(self, _device_id: str, question: str) -> dict:
        return {
            "guidance_text": f"답:{question}",
            "used_fallback_llm": False,
            "source": "question-llm",
        }

    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)
    monkeypatch.setattr(SttToLlmBridge, "_answer_free_question", _fake_answer)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("지금 몇 시야"), "test-device")

    assert response["source"] == "question-llm"
    assert fake_manager.status == "IDLE"


# [바이브 코딩 부분]
# - 아래 테스트는 부가 설명보다 실제 사용자 음성 흐름(켜기/목적지/끄기)에 맞춰 동작 검증을 제공한다.
# - 명령어 문구 자체보다 상태 전환과 source 값이 기대대로 나오는지에 집중한다.


@pytest.mark.asyncio
async def test_navigation_wakeup_command_sets_waiting_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="IDLE")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    result = _make_stt_result("네비게이션 시작")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-wakeup"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"


@pytest.mark.asyncio
async def test_navigation_shutdown_command_resets_status_and_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="NAVIGATING")
    fake_manager.last_route = [{"index": 1, "lat": 37.1, "lon": 127.1}]
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    result = _make_stt_result("네비게이션 꺼줘")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-shutdown"
    assert fake_manager.status == "IDLE"
    assert fake_manager.last_route == []


# [하드 코딩 부분 - 핵심]
# - 목적지 파싱 후 helper_search_poi/helper_fetch_route를 거쳐 waypoints를 구성하는 경로를 검증한다.
# - WAITING_FOR_DESTINATION 상태에서만 목적지 처리 분기가 타도록 고정한다.


@pytest.mark.asyncio
async def test_navigation_destination_setup_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    # 2026-07-18(th): 서울역 GPS 폴백이 제거되어 session.lat/lon이 None이면
    # navigation-setup-no-gps로 조기 반환한다 - 이 테스트는 GPS 수신 상태의
    # 목적지 설정 성공 경로를 검증하므로 실좌표를 채워야 한다.
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    def _fake_resolve(keyword: str, center_lat: float, center_lon: float) -> dict:
        _ = (keyword, center_lat, center_lon)
        return {
            "best": {"name": "서울역", "x": "126.9707", "y": "37.5547", "distance_m": 10.0},
            "candidates": [],
            "ambiguous": False,
        }

    def _fake_fetch_route(_start: dict, _end: dict) -> dict:
        return {
            "features": [
                {
                    "geometry": {"type": "Point", "coordinates": [126.9710, 37.5550]},
                    "properties": {
                        "description": "직진",
                        "facilityType": "crosswalk",
                    },
                }
            ]
        }

    monkeypatch.setattr(nav_server_module, "helper_resolve_destination_poi", _fake_resolve)
    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    result = _make_stt_result("서울역으로 설정")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-success"
    # 2026-07-20(P0 §6.5): 성공 안내는 실제 선택된 POI 이름을 읽는다.
    assert "서울역" in response["guidance_text"]
    assert fake_manager.status == "NAVIGATING"
    assert len(fake_manager.last_route) == 1
    assert fake_manager.last_route[0]["description"] == "직진"


@pytest.mark.asyncio
async def test_navigation_destination_setup_fail_when_poi_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    # 2026-07-18(th): GPS 미수신이면 POI 검색 이전에 navigation-setup-no-gps로
    # 조기 반환하므로, POI 미발견 분기를 검증하려면 실좌표가 필요하다.
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    def _fake_resolve(_keyword: str, _center_lat: float, _center_lon: float):
        return None

    monkeypatch.setattr(nav_server_module, "helper_resolve_destination_poi", _fake_resolve)

    bridge = SttToLlmBridge()
    result = _make_stt_result("없는목적지로 설정")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-fail"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"


@pytest.mark.asyncio
async def test_navigation_destination_setup_no_gps(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-07-18(th): GPS 미수신 상태에서는 서울역 등 가짜 출발점 없이
    navigation-setup-no-gps로 조기 반환하고 POI/경로 조회를 아예 시도하지 않는다."""
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    search_calls: list[str] = []

    def _fake_search_poi(keyword: str) -> dict:
        search_calls.append(keyword)
        return {"name": "서울역", "x": "126.9707", "y": "37.5547"}

    monkeypatch.setattr(nav_server_module, "helper_search_poi", _fake_search_poi)

    bridge = SttToLlmBridge()
    result = _make_stt_result("서울역으로 설정")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-no-gps"
    assert search_calls == []
    assert fake_manager.status == "WAITING_FOR_DESTINATION"


# [하드 코딩 부분 - 핵심]
# 2026-07-20: 실기기 필드 테스트 회귀 분석 보고서(P0 확정 결함 1~3) 재발 방지 테스트.
# - 목적지 파서가 장소명 내부 문자(로/으로)를 보존하는지 실제 TMAP 호출 인자로 검증.
# - fuzzy wake("길댕")가 "길동역"/"길음역"/"길상사" 같은 정상 목적지를 가로채지 않는지 검증.
# - "까지 어떻게 가"처럼 질문 힌트 단어가 있어도 명시적 경로 의도가 있으면 목적지로 처리하는지 검증.


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("utterance", "expected_keyword"),
    [
        ("구로역으로 설정", "구로역"),
        ("종로3가역으로 안내해줘", "종로3가역"),
        ("가로수길로 가줘", "가로수길"),
        ("압구정로데오역까지 안내해줘", "압구정로데오역"),
        ("목적지는 서울역", "서울역"),
    ],
)
async def test_destination_parser_preserves_place_name(
    monkeypatch: pytest.MonkeyPatch, utterance: str, expected_keyword: str
) -> None:
    """전역 replace가 아니라 위치기반 파서를 써서 TMAP searchKeyword가 원래 장소명과 같아야 한다."""
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    search_calls: list[str] = []

    def _fake_resolve(keyword: str, center_lat: float, center_lon: float) -> dict:
        _ = (center_lat, center_lon)
        search_calls.append(keyword)
        return {
            "best": {"name": keyword, "x": "126.9707", "y": "37.5547", "distance_m": 10.0},
            "candidates": [],
            "ambiguous": False,
        }

    def _fake_fetch_route(_start: dict, _end: dict) -> dict:
        return {"features": []}

    monkeypatch.setattr(nav_server_module, "helper_resolve_destination_poi", _fake_resolve)
    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    await bridge.invoke_existing_llm(_make_stt_result(utterance), "test-device")

    assert search_calls == [expected_keyword]


@pytest.mark.asyncio
@pytest.mark.parametrize("place_name", ["길동역", "길음역", "길상사"])
async def test_gildaeng_fuzzy_wake_does_not_intercept_real_destination(
    monkeypatch: pytest.MonkeyPatch, place_name: str
) -> None:
    """편집거리 1 이하로 '길댕'과 유사한 정상 목적지가 wake로 오인돼 재질문만 반환되면 안 된다."""
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    search_calls: list[str] = []

    def _fake_resolve(keyword: str, center_lat: float, center_lon: float) -> dict:
        _ = (center_lat, center_lon)
        search_calls.append(keyword)
        return {
            "best": {"name": keyword, "x": "126.9707", "y": "37.5547", "distance_m": 10.0},
            "candidates": [],
            "ambiguous": False,
        }

    def _fake_fetch_route(_start: dict, _end: dict) -> dict:
        return {"features": []}

    monkeypatch.setattr(nav_server_module, "helper_resolve_destination_poi", _fake_resolve)
    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result(place_name), "test-device")

    assert search_calls == [place_name]
    assert response["source"] != "navigation-destination-reprompt"


@pytest.mark.asyncio
async def test_gildaeng_exact_reconfirm_still_reprompts(monkeypatch: pytest.MonkeyPatch) -> None:
    """목적지 대기 중 '길댕아'를 정확히 다시 말하면(재확인 습관) 여전히 재질문으로 받는다."""
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("길댕아"), "test-device")

    assert response["source"] == "navigation-destination-reprompt"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"


@pytest.mark.asyncio
async def test_destination_intent_overrides_question_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'까지'+이동 표현이 있으면 '어떻게' 같은 질문 힌트 단어가 있어도 목적지로 처리한다."""
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    search_calls: list[str] = []

    def _fake_resolve(keyword: str, center_lat: float, center_lon: float) -> dict:
        _ = (center_lat, center_lon)
        search_calls.append(keyword)
        return {
            "best": {"name": keyword, "x": "126.9707", "y": "37.5547", "distance_m": 10.0},
            "candidates": [],
            "ambiguous": False,
        }

    def _fake_fetch_route(_start: dict, _end: dict) -> dict:
        return {"features": []}

    monkeypatch.setattr(nav_server_module, "helper_resolve_destination_poi", _fake_resolve)
    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(
        _make_stt_result("서울역까지 어떻게 가"), "test-device"
    )

    assert search_calls == ["서울역"]
    assert response["source"] != "question-llm"
    assert fake_manager.status != "IDLE"


# [하드 코딩 부분 - 핵심]
# 2026-07-20: 회귀 분석 보고서 P0 "사용자 확인" - 동명 POI 후보가 모호하면
# 자동 확정하지 않고 음성으로 확인한 뒤, 다음 발화의 순번 선택으로 경로를 확정한다.


@pytest.mark.asyncio
async def test_ambiguous_poi_triggers_confirmation_instead_of_auto_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """동명 후보 간 거리 우위가 불분명하면 자동 확정 대신 확인 질문으로 대기 상태를 바꾼다."""
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    def _fake_resolve(_keyword: str, _center_lat: float, _center_lon: float) -> dict:
        return {
            "best": {"name": "스타벅스", "x": "127.0280", "y": "37.4980", "distance_m": 300.0},
            "candidates": [
                {"name": "스타벅스", "x": "127.0280", "y": "37.4980", "distance_m": 300.0},
                {"name": "스타벅스", "x": "126.9220", "y": "37.5563", "distance_m": 500.0},
            ],
            "ambiguous": True,
        }

    monkeypatch.setattr(nav_server_module, "helper_resolve_destination_poi", _fake_resolve)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("스타벅스로 설정"), "test-device")

    assert response["source"] == "navigation-poi-confirm-needed"
    assert fake_manager.status == "WAITING_FOR_POI_CONFIRMATION"
    assert fake_manager.pending_poi_candidates is not None
    assert len(fake_manager.pending_poi_candidates) == 2


@pytest.mark.asyncio
async def test_poi_confirmation_selection_completes_route(monkeypatch: pytest.MonkeyPatch) -> None:
    """확인 대기 중 '2번'을 말하면 두 번째 후보로 경로를 확정하고 실제 선택 POI를 읽는다."""
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_POI_CONFIRMATION")
    fake_manager.session.lat = 37.5665
    fake_manager.session.lon = 126.9780
    fake_manager.pending_poi_candidates = [
        {
            "poi": {"name": "스타벅스", "x": "127.0280", "y": "37.4980"},
            "destination": "스타벅스",
        },
        {
            "poi": {"name": "스타벅스", "x": "126.9220", "y": "37.5563"},
            "destination": "스타벅스",
        },
    ]
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    fetch_calls: list[dict] = []

    def _fake_fetch_route(_start: dict, end: dict) -> dict:
        fetch_calls.append(end)
        return {"features": []}

    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("2번"), "test-device")

    assert response["source"] == "navigation-setup-success"
    assert fake_manager.status == "NAVIGATING"
    assert fake_manager.pending_poi_candidates is None
    # 두 번째 후보(홍대 좌표)가 선택되어 helper_fetch_route에 전달되어야 한다.
    assert fetch_calls == [{"name": "스타벅스", "x": "126.9220", "y": "37.5563"}]


@pytest.mark.asyncio
async def test_poi_confirmation_unrecognized_reply_reprompts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """확인 대기 중 순번으로 해석되지 않는 발화는 추측하지 않고 재입력을 유도한다."""
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_POI_CONFIRMATION")
    fake_manager.pending_poi_candidates = [
        {"poi": {"name": "스타벅스", "x": "1", "y": "1"}, "destination": "스타벅스"},
        {"poi": {"name": "스타벅스", "x": "2", "y": "2"}, "destination": "스타벅스"},
    ]
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("음 잘 모르겠어"), "test-device")

    assert response["source"] == "navigation-poi-confirm-retry"
    assert fake_manager.status == "WAITING_FOR_POI_CONFIRMATION"
    assert fake_manager.pending_poi_candidates is not None


@pytest.mark.asyncio
async def test_recent_guidance_echo_is_ignored() -> None:
    bridge = SttToLlmBridge()
    bridge._recent_guidance.clear()
    bridge._record_guidance("echo-device", "길찾아줘 또는 물어볼게 중 하나로 다시 말씀해 주세요.")

    response = await bridge.invoke_existing_llm(
        _make_stt_result("길찾아줘 또는 물어볼게 중 하나로 다시 말씀해 주세요"),
        "echo-device",
    )

    assert response["source"] == "stt-echo-detected"
    assert response["guidance_text"] == ""
    bridge._recent_guidance.clear()


@pytest.mark.asyncio
async def test_navigation_intent_wins_over_repeated_wake(monkeypatch: pytest.MonkeyPatch) -> None:
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="IDLE")
    fake_manager.awaiting_intent = True
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(
        _make_stt_result("길댕아 길찾아줘"),
        "test-device",
    )

    assert response["source"] == "navigation-setup-wakeup"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"
    assert fake_manager.awaiting_intent is False
