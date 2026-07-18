import logging
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):  # 한글 깨짐을 방지하기 위한 방어적 인코딩 설정
    sys.stdout.reconfigure(encoding="utf-8")

from server.bus.redis_client import redis_bus  # 기존 redis 연결 재사용

logger = logging.getLogger(__name__)

# P0-1 (2026-07-17): 반사 억제 재무장(Re-arm) 정책 상수.
# 60초 무조건 침묵 -> "같은 상황 반복은 억제, 상황 변화(새 객체/거리 악화) 시 즉시 재발화".
# 동일 키(같은 track_id+distance_band) TTL. 보행 속도(1m/s) 기준 5초면 동일 객체 반복 스팸 방지 충분.
REFLEX_SUPPRESS_TTL_S = int(os.getenv("REFLEX_SUPPRESS_TTL_S", "5"))
# 서로 다른 객체 경보의 최소 간격 (device 단위). 알림 폭탄 방지.
REFLEX_MIN_GAP_S = float(os.getenv("REFLEX_MIN_GAP_S", "1.5"))
# near(<=0.6m) 햅틱+비프 스로틀 간격. 충돌 임박 촉각 신호는 반복되어도 안전 이득이 손실보다 큼.
REFLEX_NEAR_HAPTIC_THROTTLE_S = float(os.getenv("REFLEX_NEAR_HAPTIC_THROTTLE_S", "0.5"))


class AlertSuppressor:
    """
    중복 경보 억제기
    - alert_id 기준으로 일정 시간 동안 동일 경보 재발행 방지
    - Redis SETEX 사용
    - 반사 Option A: alert_id는 high_obstacle (방향 제외). 방향만 바뀌어 TTL을 우회하지 않는다.

    P0-1 (2026-07-17): 재무장 정책 추가.
    - 억제 키: high_obstacle:{track_id}:{distance_band} (새 객체/거리 악화 시 키가 달라져 억제 우회)
    - 동일 키 TTL: REFLEX_SUPPRESS_TTL_S(5s)
    - 신규 트랙 최소 쿨다운: REFLEX_MIN_GAP_S(1.5s, device 단위)
    - near(<=0.6m) 햅틱+비프: TTL 억제 제외, REFLEX_NEAR_HAPTIC_THROTTLE_S(500ms) 스로틀만
    """

    DEFAULT_TTL = 60  # 기존 억제 기본 유효시간 60초 (레거시 should_suppress용)
    DEFALUT_TTL = DEFAULT_TTL  # 기존 오타 상수 호환 유지

    def __init__(self, ttl: int = DEFAULT_TTL):  # ttl은 DEFAULT_TTL로 기본값 설정
        self.ttl = ttl
        # P0-1: device 단위 최소 쿨다운 추적 (non-near 클립/비프)
        self._last_device_alert_ts: dict[str, float] = {}
        # near 햅틱+비프 스로틀 추적 (TTL 억제 제외)
        self._last_near_alert_ts: dict[str, float] = {}
        # 직전 경보 상태 (track_id + distance_band) - 밴드 악화 재발화 판정용
        self._last_alert_state: dict[str, dict] = {}

    def _make_key(self, device_id: str, alert_id: str) -> str:
        """suppress:{device_id}:{alert_id} - 레거시 (방향 제외 high_obstacle 고정)."""
        return f"suppress:{device_id}:{alert_id}"

    def _make_reflex_key(self, device_id: str, track_id: str | None, distance_band: str) -> str:
        """P0-1: suppress:{device_id}:high_obstacle:{track_id}:{distance_band}.

        track_id가 None(Mock 등)이면 'unknown'으로 폴백해 키 충돌을 방지한다.
        방향 버킷은 기존 결정(2026-07-16 Option A)대로 키에서 제외한다.
        """
        tid = track_id or "unknown"
        return f"suppress:{device_id}:high_obstacle:{tid}:{distance_band}"

    @staticmethod
    def should_rearm(prev_band: str | None, current_band: str | None) -> bool:
        """같은 track_id 내에서 거리 밴드가 악화(far->medium->near)되었는지 판정.

        # [면접 대비 주석]
        # 재무장(Re-arm) 정책의 핵심 판정 함수.
        # 설계 의도: "같은 상황의 반복 안내는 억제하되, 상황이 바뀌면 즉시 다시 경보".
        # - 신규 트랙(prev=None) 또는 밴드 알 수 없음 -> True (보수적 재발화)
        # - 밴드가 가까워진 경우(far->medium->near) -> True (위험 악화, 즉시 재발화)
        # - 동일/멀어진 밴드 -> False (기존 억제 유지, 동일 키 TTL이 발화 여부 결정)
        # 밴드 순서는 보행 접근 방향(far->medium->near)을 따른다.
        """
        band_order = {"far": 0, "medium": 1, "near": 2}
        if prev_band is None or current_band is None:
            return True
        prev_rank = band_order.get(prev_band, 0)
        current_rank = band_order.get(current_band, 0)
        return current_rank > prev_rank

    async def _key_exists(self, key: str) -> bool:
        """Redis EXISTS 안전 조회 (개발용 스텁의 비정상 응답 방어)."""
        try:
            if redis_bus._redis is None:
                connected = await redis_bus.connect()
                if not connected or redis_bus._redis is None:
                    return False
            exists = await redis_bus._redis.exists(key)
            # 개발용 Redis 스텁이 EXISTS를 잘못 구현해 "+OK"를 반환하면
            # bool("OK") == True 가 되어 모든 반사 경보가 영구 억제된다.
            # 정수(존재 개수)만 신뢰하고, 그 외 타입은 억제하지 않는다.
            if isinstance(exists, bool):
                return exists
            if isinstance(exists, int):
                return exists > 0
            try:
                return int(exists) > 0
            except (TypeError, ValueError):
                logger.warning(f"[Suppressor] EXISTS 응답 타입 이상: key={key}, value={exists!r}")
                return False
        except Exception as e:
            logger.warning(f"[Suppressor] Redis 조회 실패 : {e}")
            return False  # 실패 시 억제하지 않음 (안전 측면)

    async def _setex(self, key: str, ttl: int, value: str = "1") -> None:
        """Redis SETEX 안전 설정."""
        try:
            if redis_bus._redis is None:
                connected = await redis_bus.connect()
                if not connected or redis_bus._redis is None:
                    return
            await redis_bus._redis.setex(key, ttl, value)
            logging.debug(f"[Suppressor] {key} 등록 (TTL={ttl}s)")
        except Exception as e:
            logger.error(f"[Suppressor] Redis setex 실패 {e}")

    async def should_emit_reflex(
        self,
        device_id: str,
        track_id: str | None,
        distance_band: str,
        is_near: bool,
    ) -> bool:
        """P0-1: 반사 경보 발화 여부 판정 (재무장 정책).

        순서:
            1. near(<=0.6m): TTL 억제 제외, REFLEX_NEAR_HAPTIC_THROTTLE_S 스로틀만.
            2. non-near: device 단위 최소 쿨다운(REFLEX_MIN_GAP_S).
            3. 동일 트랙+밴드 TTL(REFLEX_SUPPRESS_TTL_S) 체크.
               - 단, 거리 밴드 악화(should_rearm) 시 재발화.
            4. 위 조건 통과 시 발화 허용.
        """
        now = time.time()
        # 1. near: 스로틀만 (충돌 임박 촉각 신호는 반복되어도 안전 이득)
        if is_near:
            last_near = self._last_near_alert_ts.get(device_id, 0.0)
            if now - last_near < REFLEX_NEAR_HAPTIC_THROTTLE_S:
                return False
            self._last_near_alert_ts[device_id] = now
            self._last_alert_state[device_id] = {
                "track_id": track_id,
                "distance_band": distance_band,
            }
            return True
        # 2. non-near: device 단위 최소 쿨다운
        last_device = self._last_device_alert_ts.get(device_id, 0.0)
        if now - last_device < REFLEX_MIN_GAP_S:
            return False
        # 3. 동일 트랙+밴드 TTL 체크
        key = self._make_reflex_key(device_id, track_id, distance_band)
        if await self._key_exists(key):
            # 밴드 악화 시 재발화 (should_rearm)
            prev = self._last_alert_state.get(device_id, {})
            if prev.get("track_id") == track_id and self.should_rearm(
                prev.get("distance_band"), distance_band
            ):
                self._last_device_alert_ts[device_id] = now
                self._last_alert_state[device_id] = {
                    "track_id": track_id,
                    "distance_band": distance_band,
                }
                return True
            return False
        # 4. 발화 허용
        self._last_device_alert_ts[device_id] = now
        self._last_alert_state[device_id] = {
            "track_id": track_id,
            "distance_band": distance_band,
        }
        return True

    async def mark_reflex_sent(
        self,
        device_id: str,
        track_id: str | None,
        distance_band: str,
    ) -> None:
        """P0-1: 반사 경보 전송 완료 마킹 (track_id+band 키, REFLEX_SUPPRESS_TTL_S)."""
        key = self._make_reflex_key(device_id, track_id, distance_band)
        await self._setex(key, REFLEX_SUPPRESS_TTL_S)

    async def should_suppress(self, device_id: str, alert_id: str) -> bool:
        """[레거시] 해당 alert_id가 최근에 발행되었는지 확인.

        Returns:
            True  -> 억제해야 함 (이미 최근에 보냄)
            False -> 발행해도 됨
        """
        key = self._make_key(device_id, alert_id)
        return await self._key_exists(key)

    async def should_supperss(self, device_id: str, alert_id: str) -> bool:
        """기존 오타 메서드 호환용 래퍼."""
        return await self.should_suppress(device_id, alert_id)

    async def mark_as_sent(self, device_id: str, alert_id: str, ttl: int | None = None) -> None:
        """[레거시] 경보를 보냈음을 표시 (TTL 동안 중복 방지)."""
        key = self._make_key(device_id, alert_id)
        ttl_seconds = ttl or self.ttl
        await self._setex(key, ttl_seconds)


# 싱글톤 인스턴트 (필요시)
Alert_suppressor = AlertSuppressor()
