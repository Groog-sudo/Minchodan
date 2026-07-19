# -*- coding: utf-8 -*-
"""단일 프로세스 기준의 가벼운 슬라이딩 윈도우 요청 제한기."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

_EVENTS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = asyncio.Lock()
_MAX_IDENTITIES = 10_000


async def enforce_rate_limit(
    scope: str,
    identity: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """범위와 식별자별 요청 횟수를 제한한다."""
    now = time.monotonic()
    key = f"{scope}:{identity}"
    async with _LOCK:
        if key not in _EVENTS and len(_EVENTS) >= _MAX_IDENTITIES:
            oldest_key = min(
                _EVENTS,
                key=lambda candidate: _EVENTS[candidate][-1] if _EVENTS[candidate] else 0.0,
            )
            _EVENTS.pop(oldest_key, None)
        events = _EVENTS[key]
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            retry_after = max(1, int(window_seconds - (now - events[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="요청이 너무 많습니다. 잠시 후 다시 시도하세요.",
                headers={"Retry-After": str(retry_after)},
            )
        events.append(now)
