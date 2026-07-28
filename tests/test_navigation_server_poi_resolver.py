import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest

import server.navigation.server as nav_server_module

# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - 2026-07-20: 실기기 필드 테스트 회귀 분석 보고서 P0 확정 결함 3(현재 위치와
#   무관한 첫 POI 강제 선택) 재발 방지 테스트.
# - helper_resolve_destination_poi가 (1) count=1이 아니라 여러 후보를 받고,
#   (2) 정확 이름 일치 -> 거리 순으로 점수화하며, (3) 동명 후보 간 거리 우위가
#   불분명하면 ambiguous=True로 신호하는지 검증한다.
# - P0 오류 폴백(fail-closed): TMAP 키 누락/플레이스홀더 시 helper_search_poi/
#   helper_search_nearest_poi/helper_fetch_route/helper_resolve_destination_poi
#   전부 가상 좌표 성공 처리 대신 None(실패)을 반환해야 한다.


def _poi(name: str, lat: float, lon: float) -> dict:
    return {"name": name, "noorLat": str(lat), "noorLon": str(lon)}


class _FakeResponse:
    def __init__(self, status_code: int, pois: list[dict]):
        self.status_code = status_code
        self._pois = pois

    def json(self) -> dict:
        return {"searchPoiInfo": {"pois": {"poi": self._pois}}}


def test_resolver_requires_at_least_five_candidates(monkeypatch) -> None:
    """count=1 고정이 아니라 최소 5개 이상을 요청해야 한다."""
    captured_params: dict = {}

    def _fake_get(url, params=None, headers=None, timeout=None):
        captured_params.update(params or {})
        return _FakeResponse(200, [_poi("서울역", 37.5547, 126.9707)])

    monkeypatch.setattr(nav_server_module, "APP_KEY", "x" * 40)
    monkeypatch.setattr(nav_server_module.requests, "get", _fake_get)

    nav_server_module.helper_resolve_destination_poi("서울역", 37.5665, 126.9780)

    assert captured_params.get("count", 0) >= 5
    assert captured_params.get("centerLat") == 37.5665
    assert captured_params.get("centerLon") == 126.9780


def test_resolver_picks_nearest_same_name_candidate(monkeypatch) -> None:
    """동명 POI 중 현재 위치에서 훨씬 가까운 쪽이 압도적으로 가까우면 확인 없이 확정한다."""

    def _fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            [
                # 강남역: 사용자 근처(약 100m 이내)
                _poi("스타벅스", 37.4980, 127.0280),
                # 홍대: 사용자로부터 훨씬 멀리(수 km)
                _poi("스타벅스", 37.5563, 126.9220),
            ],
        )

    monkeypatch.setattr(nav_server_module, "APP_KEY", "x" * 40)
    monkeypatch.setattr(nav_server_module.requests, "get", _fake_get)

    result = nav_server_module.helper_resolve_destination_poi(
        "스타벅스", center_lat=37.4979, center_lon=127.0276
    )

    assert result is not None
    assert result["ambiguous"] is False
    assert result["best"]["y"] == "37.498"


def test_resolver_flags_ambiguous_when_same_name_candidates_are_close(monkeypatch) -> None:
    """동명 POI가 여러 곳에 있고 거리 우위가 뚜렷하지 않으면 ambiguous=True로 신호한다."""

    def _fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            [
                _poi("이디야커피", 37.5000, 127.0300),
                _poi("이디야커피", 37.5010, 127.0310),  # 첫 후보와 매우 인접(수백 m)
            ],
        )

    monkeypatch.setattr(nav_server_module, "APP_KEY", "x" * 40)
    monkeypatch.setattr(nav_server_module.requests, "get", _fake_get)

    result = nav_server_module.helper_resolve_destination_poi(
        "이디야커피", center_lat=37.4995, center_lon=127.0295
    )

    assert result is not None
    assert result["ambiguous"] is True
    assert len(result["candidates"]) == 2


def test_resolver_prioritizes_exact_name_match_over_relevance_order(monkeypatch) -> None:
    """TMAP이 첫 번째로 반환해도 정확 이름 일치가 아니면 정확 일치 후보를 우선한다."""

    def _fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            [
                _poi("서울역버스환승센터", 37.5555, 126.9700),  # 부분 일치, relevance 1위
                _poi("서울역", 37.5547, 126.9707),  # 정확 일치, 더 멀 수도 있음
            ],
        )

    monkeypatch.setattr(nav_server_module, "APP_KEY", "x" * 40)
    monkeypatch.setattr(nav_server_module.requests, "get", _fake_get)

    result = nav_server_module.helper_resolve_destination_poi(
        "서울역", center_lat=37.4979, center_lon=127.0276
    )

    assert result is not None
    assert result["best"]["name"] == "서울역"


def test_resolver_returns_none_when_no_candidates(monkeypatch) -> None:
    def _fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(200, [])

    monkeypatch.setattr(nav_server_module, "APP_KEY", "x" * 40)
    monkeypatch.setattr(nav_server_module.requests, "get", _fake_get)

    result = nav_server_module.helper_resolve_destination_poi(
        "없는장소", center_lat=37.4979, center_lon=127.0276
    )

    assert result is None


def test_resolver_returns_none_without_valid_app_key(monkeypatch) -> None:
    """P0 오류 폴백: 키가 없으면 가상 좌표 대신 None(실패)을 반환해야 한다."""
    monkeypatch.setattr(nav_server_module, "APP_KEY", "")

    result = nav_server_module.helper_resolve_destination_poi(
        "아무데나", center_lat=37.4979, center_lon=127.0276
    )

    assert result is None


# [하드 코딩 부분 - 핵심]
# 2026-07-20: 회귀 분석 보고서 P0 오류 폴백 - 나머지 TMAP 헬퍼(helper_search_poi/
# helper_search_nearest_poi/helper_fetch_route)도 키 누락·플레이스홀더 시
# 고정 가상 좌표(126.8722/37.4590 등)로 성공 처리하던 것을 fail-closed(None)로 전환했다.


@pytest.mark.parametrize("invalid_key", ["", "YOUR_TMAP_APP_KEY_HERE", "   "])
def test_search_poi_fails_closed_without_valid_key(monkeypatch, invalid_key: str) -> None:
    monkeypatch.setattr(nav_server_module, "APP_KEY", invalid_key)

    result = nav_server_module.helper_search_poi("아무데나")

    assert result is None


@pytest.mark.parametrize("invalid_key", ["", "YOUR_TMAP_APP_KEY_HERE"])
def test_search_nearest_poi_fails_closed_without_valid_key(monkeypatch, invalid_key: str) -> None:
    monkeypatch.setattr(nav_server_module, "APP_KEY", invalid_key)

    result = nav_server_module.helper_search_nearest_poi(
        "화장실", center_lat=37.4979, center_lon=127.0276
    )

    assert result is None


@pytest.mark.parametrize("invalid_key", ["", "YOUR_TMAP_APP_KEY_HERE"])
def test_fetch_route_fails_closed_without_valid_key(monkeypatch, invalid_key: str) -> None:
    monkeypatch.setattr(nav_server_module, "APP_KEY", invalid_key)

    result = nav_server_module.helper_fetch_route(
        {"name": "출발", "x": "127.0", "y": "37.5"},
        {"name": "도착", "x": "127.1", "y": "37.6"},
    )

    assert result is None


# [하드 코딩 부분 - 핵심]
# 2026-07-28: 시연용 가상 경로가 기본 동작으로 되돌아갔던 회귀를 재차 차단한다.
# (1) 가상 경로는 NAV_MOCK_ROUTE opt-in에서만 허용하고,
# (2) 유효한 키로 호출했다가 실패한 경우는 opt-in 여부와 무관하게 항상 fail-closed다.
#     실패를 가상 경로로 덮으면 사용자가 실재하지 않는 회전 안내를 듣게 된다.


@pytest.mark.parametrize("placeholder_key", ["", "DUMMY_TMAP_KEY", "YOUR_TMAP_APP_KEY_HERE"])
def test_fetch_route_returns_mock_only_when_opt_in(monkeypatch, placeholder_key: str) -> None:
    monkeypatch.setattr(nav_server_module, "APP_KEY", placeholder_key)
    monkeypatch.setattr(nav_server_module, "NAV_MOCK_ROUTE_ENABLED", True)

    result = nav_server_module.helper_fetch_route(
        {"name": "출발", "x": "127.0", "y": "37.5"},
        {"name": "도착", "x": "127.1", "y": "37.6"},
    )

    assert result is not None
    assert result["type"] == "FeatureCollection"


def test_fetch_route_fails_closed_on_api_error_even_with_opt_in(monkeypatch) -> None:
    monkeypatch.setattr(nav_server_module, "APP_KEY", "REAL_LOOKING_APP_KEY_1234")
    monkeypatch.setattr(nav_server_module, "NAV_MOCK_ROUTE_ENABLED", True)

    class _ErrorResponse:
        status_code = 500

    monkeypatch.setattr(
        nav_server_module.requests, "post", lambda *args, **kwargs: _ErrorResponse()
    )

    result = nav_server_module.helper_fetch_route(
        {"name": "출발", "x": "127.0", "y": "37.5"},
        {"name": "도착", "x": "127.1", "y": "37.6"},
    )

    assert result is None


def test_resolver_fails_closed_on_api_error_even_with_opt_in(monkeypatch) -> None:
    monkeypatch.setattr(nav_server_module, "APP_KEY", "REAL_LOOKING_APP_KEY_1234")
    monkeypatch.setattr(nav_server_module, "NAV_MOCK_ROUTE_ENABLED", True)

    class _ErrorResponse:
        status_code = 503

    monkeypatch.setattr(nav_server_module.requests, "get", lambda *args, **kwargs: _ErrorResponse())

    result = nav_server_module.helper_resolve_destination_poi(
        "강남역", center_lat=37.4979, center_lon=127.0276
    )

    assert result is None
