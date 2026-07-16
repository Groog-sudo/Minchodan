import logging
import sys

if hasattr(sys.stdout, "reconfigure"):  # 한글 깨짐을 방지하기 위한 방어적 인코딩 설정
    sys.stdout.reconfigure(encoding="utf-8")

from server.bus.redis_client import redis_bus  # 기존 redis 연결 재사용

logger = logging.getLogger(__name__)


class AlertSuppressor:
    """
    중복 경보 억제기
    - alert_id 기준으로 일정 시간 동안 동일 경보 재발행 방지
    - Redis SETEX 사용
    - 반사 Option A: alert_id는 high_obstacle (방향 제외). 방향만 바뀌어 TTL을 우회하지 않는다.
    """

    DEFAULT_TTL = 60  # 기본 유효시간 60초
    DEFALUT_TTL = DEFAULT_TTL  # 기존 오타 상수 호환 유지

    def __init__(self, ttl: int = DEFAULT_TTL):  # ttl은 DEFAULT_TTL로 기본값 설정
        self.ttl = ttl

    def _make_key(self, device_id: str, alert_id: str) -> str:
        """suppress:{device_id}:{alert_id} — 반사 근접은 alert_id=high_obstacle 고정."""
        return f"suppress:{device_id}:{alert_id}"

    async def should_suppress(self, device_id: str, alert_id: str) -> bool:
        """
        해당 alert_id가 최근에 발행되었는지 확인
        Returns:
            True  -> 억제해야 함 (이미 최근에 보냄)
            False -> 발행해도 됨
        """
        key = self._make_key(device_id, alert_id)
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

    async def should_supperss(self, device_id: str, alert_id: str) -> bool:
        """기존 오타 메서드 호환용 래퍼."""
        return await self.should_suppress(device_id, alert_id)

    async def mark_as_sent(self, device_id: str, alert_id: str, ttl: int | None = None) -> None:
        """
        경보를 보냈음을 표시 (TTL 동안 중복 방지)
        """
        # 억제용 키 생성
        key = self._make_key(device_id, alert_id)

        # 전달된 유효시간이 있으면 사용하고 없으면 기본 유효시간 사용
        ttl_seconds = ttl or self.ttl
        try:
            if redis_bus._redis is None:
                connected = await redis_bus.connect()
                if not connected or redis_bus._redis is None:
                    return

            await redis_bus._redis.setex(key, ttl_seconds, "1")
            logging.debug(f"[Suppressor] {key} 등록 (TTL={ttl_seconds}s)")
        except Exception as e:
            logger.error(f"[Suppressor] Redis setex 실패 {e}")


# 싱글톤 인스턴트 (필요시)
Alert_suppressor = AlertSuppressor()
