# -*- coding: utf-8 -*-
import json
import logging
import sys
from typing import Any, Dict, Optional

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os

from redis.asyncio import Redis

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DEFAULT_TRACK_TTL = 30


class RedisBus:
    """Redis Streams + Hash 컨텍스트 인터페이스."""

    def __init__(self, url: str = DEFAULT_REDIS_URL):
        self.url = url
        self._redis: Optional[Redis] = None

    async def connect(self) -> bool:
        try:
            self._redis = Redis.from_url(self.url, decode_responses=True)
            await self._redis.ping()
            logger.info("[RedisBus] 연결 성공")
            return True
        except Exception as e:
            logger.warning(f"[RedisBus] 연결 실패: {e}")
            self._redis = None
            return False

    async def close(self):
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"[RedisBus] 종료 오류: {e}")
            finally:
                self._redis = None

    async def publish_event(self, stream: str, payload: Dict[str, Any]) -> Optional[str]:
        if self._redis is None:
            return None
        try:
            message_id = await self._redis.xadd(stream, payload)
            return message_id
        except Exception as e:
            logger.warning(f"[RedisBus] xadd 실패({stream}): {e}")
            return None

    async def set_track_context(
        self,
        track_id: str,
        mapping: Dict[str, str],
        ttl: int = DEFAULT_TRACK_TTL,
    ) -> bool:
        if self._redis is None:
            return False
        try:
            key = f"ctx:{track_id}"
            await self._redis.hset(key, mapping=mapping)
            await self._redis.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning(f"[RedisBus] ctx 업데이트 실패({track_id}): {e}")
            return False

    async def get_track_context(self, track_id: str) -> Dict[str, str]:
        if self._redis is None:
            return {}
        try:
            return await self._redis.hgetall(f"ctx:{track_id}")
        except Exception as e:
            logger.warning(f"[RedisBus] ctx 조회 실패({track_id}): {e}")
            return {}


# 전역 싱글턴 (선택적 사용)
redis_bus = RedisBus()
