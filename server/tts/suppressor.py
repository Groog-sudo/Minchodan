import sys
if hasattr(sys.stdout, "reconfigure"):      # 한글 깨짐을 방지하기 위한 방어적 인코딩 설정
    sys.stdout.reconfigure(encoding="utf-8")
import os
import json
from typing import Optional


import logging
from server.bus.redis_client import redis_bus      # 기존 redis 연결 재사용

logger = logging.getLogger(__name__)

class AlertSuppressor:
    """
    중복 경보 억제기
    - alert_id 기준으로 일정 시간 동안 동일 경보 재발행 방지
    - Redis SETEX 사용
    """

    DEFALUT_TTL = 60 # 기본 유효시간 60초

    def __init__(self, ttl:int = DEFALUT_TTL):  # ttl은 DEFAULT_TTL로 기본값 설정
        self.ttl = ttl

    def _make_key(self, device_id: str, alert_id: str) -> str :
        """device_id까지 포함하면 더 정밀하게 억제 가능"""
        return f"suppress:{device_id}:{alert_id}"
    
    async def should_supperss(self, device_id: str, alert_id: str) -> bool:
        """
        해당 alert_id가 최근에 발행되었는지 확인
        Returns:
            True  -> 억제해야 함 (이미 최근에 보냄)
            False -> 발행해도 됨
        """
        key = self._make_key(device_id, alert_id)
        try:
            exists = await redis_bus.redis.exists(key)
            return bool(exists)
        except Exception as e:
            logger.warning(f"[Suppressor] Redis 조회 실패 : {e}")
            return False # 실패 시 억제하지 않음 (안전 측면)
        
    async def mark_as_sent(self, device_id: str, alert_id: str, ttl: Optional[int] = None) -> None :
        """
        경보를 보냈음을 표시 (TTL 동안 중복 방지)
        """
        # 억제용 키 생성
        key = self._make_key(device_id, alert_id)

        # 전달된 유효시간이 있으면 사용하고 없으면 기본 유효시간 사용
        ttl_seconds = ttl or self.ttl
        try:
            await redis_bus._redis.setex(key, ttl_seconds, "1")
            logging.debug(f"[Suppressor] {key} 등록 (TTL={ttl_seconds}s)")
        except Exception as e:
            logger.error(f"[Suppressor] Redis setex 실패 {e}")

# 싱글톤 인스턴트 (필요시)
Alert_suppressor = AlertSuppressor()