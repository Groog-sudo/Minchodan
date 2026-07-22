import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest

from server.tts.suppressor import AlertSuppressor


class TestShouldRearm:
    """P0-1: should_rearm() 거리 밴드 악화 판정 단위 테스트."""

    def test_new_track_rearms(self):
        """신규 트랙(prev=None)은 보수적 재발화 (True)."""
        assert AlertSuppressor.should_rearm(None, "near") is True
        assert AlertSuppressor.should_rearm(None, "medium") is True

    def test_unknown_band_rearms(self):
        """알 수 없는 밴드는 보수적 재발화."""
        assert AlertSuppressor.should_rearm("medium", None) is True
        assert AlertSuppressor.should_rearm(None, None) is True

    def test_band_worsening_rearms(self):
        """밴드가 가까워지면(far->medium->near) 재발화."""
        assert AlertSuppressor.should_rearm("far", "medium") is True
        assert AlertSuppressor.should_rearm("medium", "near") is True
        assert AlertSuppressor.should_rearm("far", "near") is True

    def test_same_band_no_rearm(self):
        """동일 밴드는 재발화하지 않음 (동일 키 TTL이 발화 여부 결정)."""
        assert AlertSuppressor.should_rearm("near", "near") is False
        assert AlertSuppressor.should_rearm("medium", "medium") is False
        assert AlertSuppressor.should_rearm("far", "far") is False

    def test_band_improvement_no_rearm(self):
        """밴드가 멀어지면(near->medium->far) 재발화하지 않음 (위험 감소)."""
        assert AlertSuppressor.should_rearm("near", "medium") is False
        assert AlertSuppressor.should_rearm("medium", "far") is False
        assert AlertSuppressor.should_rearm("near", "far") is False


class TestShouldEmitReflexNear:
    """P0-1: near(<=0.6m) 햅틱+비프 스로틀 동작 (TTL 억제 제외)."""

    @pytest.mark.asyncio
    async def test_near_first_emits(self, monkeypatch):
        """near 첫 경보는 발화 허용."""
        sup = AlertSuppressor()
        # Redis 미연결이면 _key_exists가 False 반환하므로 near 경로(스로틀만)는 Redis 없이 동작
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        result = await sup.should_emit_reflex("dev1", "t1", "near", is_near=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_near_throttled_within_500ms(self, monkeypatch):
        """near 500ms 이내 재경보는 스로틀로 억제."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        first = await sup.should_emit_reflex("dev1", "t1", "near", is_near=True)
        second = await sup.should_emit_reflex("dev1", "t1", "near", is_near=True)
        assert first is True
        assert second is False  # 500ms 이내

    @pytest.mark.asyncio
    async def test_near_emits_after_throttle_window(self, monkeypatch):
        """near 스로틀 창(500ms)과 동일 track_id 최소 간격(1.2s) 모두 경과 후 재경보는 발화."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        # 첫 경보 후 타임스탬프를 과거로 돌려 스로틀/트랙 간격 모두 경과 시뮬레이션
        await sup.should_emit_reflex("dev1", "t1", "near", is_near=True)
        sup._last_near_alert_ts["dev1"] -= 1.3
        sup._last_near_track_alert["dev1"] = ("t1", sup._last_near_track_alert["dev1"][1] - 1.3)
        result = await sup.should_emit_reflex("dev1", "t1", "near", is_near=True)
        assert result is True


class TestShouldEmitReflexNearTrackGap:
    """2026-07-20: near에서 동일 track_id 재발동 최소 간격(REFLEX_NEAR_TRACK_MIN_GAP_S)."""

    @pytest.mark.asyncio
    async def test_same_track_blocked_within_track_min_gap(self, monkeypatch):
        """500ms 스로틀은 지났지만 1.2s 미만이면 동일 track_id는 억제."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        first = await sup.should_emit_reflex("dev1", "T-0008", "near", is_near=True)
        sup._last_near_alert_ts["dev1"] -= 0.6  # 500ms 스로틀만 회피(1.2s 미만)
        second = await sup.should_emit_reflex("dev1", "T-0008", "near", is_near=True)
        assert first is True
        assert second is False

    @pytest.mark.asyncio
    async def test_same_track_emits_after_track_min_gap(self, monkeypatch):
        """1.2s 경과 후에는 동일 track_id도 재발화."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        first = await sup.should_emit_reflex("dev1", "T-0008", "near", is_near=True)
        sup._last_near_alert_ts["dev1"] -= 1.3
        sup._last_near_track_alert["dev1"] = ("T-0008", sup._last_near_track_alert["dev1"][1] - 1.3)
        second = await sup.should_emit_reflex("dev1", "T-0008", "near", is_near=True)
        assert first is True
        assert second is True

    @pytest.mark.asyncio
    async def test_different_track_emits_after_throttle_only(self, monkeypatch):
        """다른 track_id는 기존 500ms 스로틀만 통과하면 즉시 발화(반응성 유지)."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        first = await sup.should_emit_reflex("dev1", "T-0008", "near", is_near=True)
        sup._last_near_alert_ts["dev1"] -= 0.6  # 500ms 스로틀만 회피
        second = await sup.should_emit_reflex("dev1", "T-0099", "near", is_near=True)
        assert first is True
        assert second is True


class TestShouldEmitReflexNonNear:
    """P0-1: non-near 클립/비프 TTL + device 쿨다운 동작."""

    @pytest.mark.asyncio
    async def test_first_medium_emits(self, monkeypatch):
        """medium 첫 경보는 발화 허용 (Redis 키 없음)."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        result = await sup.should_emit_reflex("dev1", "t1", "medium", is_near=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_device_cooldown_blocks_rapid_second(self, monkeypatch):
        """device 단위 최소 쿨다운(1.5s) 이내 다른 트랙 경보는 억제."""
        sup = AlertSuppressor()
        monkeypatch.setattr(sup, "_key_exists", lambda key: _afalse())
        first = await sup.should_emit_reflex("dev1", "t1", "medium", is_near=False)
        # 다른 트랙이지만 같은 device, 쿨다운 이내
        second = await sup.should_emit_reflex("dev1", "t2", "medium", is_near=False)
        assert first is True
        assert second is False

    @pytest.mark.asyncio
    async def test_same_track_band_ttl_blocks(self, monkeypatch):
        """동일 트랙+밴드 TTL 내 재경보는 억제 (밴드 악화 없음)."""
        sup = AlertSuppressor()
        keys: set[str] = set()

        async def fake_exists(key):
            return key in keys

        async def fake_setex(key, ttl, value="1"):
            keys.add(key)

        monkeypatch.setattr(sup, "_key_exists", fake_exists)
        monkeypatch.setattr(sup, "_setex", fake_setex)
        # 첫 경보 발화 후 전송 성공 마킹
        first = await sup.should_emit_reflex("dev1", "t1", "medium", is_near=False)
        await sup.mark_reflex_sent("dev1", "t1", "medium")
        sup._last_device_alert_ts["dev1"] -= 5.0  # 쿨다운 회피
        # 동일 트랙+밴드, TTL 내 -> 억제
        second = await sup.should_emit_reflex("dev1", "t1", "medium", is_near=False)
        assert first is True
        assert second is False  # 동일 트랙+밴드 TTL

    @pytest.mark.asyncio
    async def test_band_worsening_rearms_within_ttl(self, monkeypatch):
        """동일 트랙에서 밴드가 악화(medium->near)하면 TTL 내라도 재발화.

        단, near는 is_near=True 경로이므로 스로틀만 적용. 이 테스트는 non-near
        밴드 악화(far->medium) 시나리오로 should_rearm 분기 검증.
        """
        sup = AlertSuppressor()
        keys: set[str] = set()

        async def fake_exists(key):
            return key in keys

        async def fake_setex(key, ttl, value="1"):
            keys.add(key)

        monkeypatch.setattr(sup, "_key_exists", fake_exists)
        monkeypatch.setattr(sup, "_setex", fake_setex)
        # far 밴드 첫 경보
        first = await sup.should_emit_reflex("dev1", "t1", "far", is_near=False)
        sup._last_device_alert_ts["dev1"] -= 5.0  # 쿨다운 회피
        # 동일 트랙이 medium으로 악화 -> should_rearm True -> 재발화
        # 단, medium 키는 다르므로 _key_exists False여야 함 (다른 키)
        second = await sup.should_emit_reflex("dev1", "t1", "medium", is_near=False)
        assert first is True
        assert second is True  # 밴드 악화로 재발화


# 헬퍼: 항상 False를 반환하는 코루틴 (Redis 미연결 시뮬레이션)
async def _afalse() -> bool:
    return False
