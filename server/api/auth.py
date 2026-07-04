"""
디바이스 토큰 검증 모듈 (MVP 하드코딩 방식).
hello 핸드셰이크 시 device_id와 token을 검증합니다.
추후 .env 또는 DB 연동으로 확장 예정.
"""

import contextlib
import logging
import sys

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

REGISTERED_DEVICES: dict[str, str] = {
    "dev-001": "token-abc-001",
    "dev-002": "token-abc-002",
}


async def verify_device(device_id: str, token: str) -> bool:
    """디바이스 토큰 검증.

    Args:
        device_id: 단말 식별자
        token: 사전 발급된 디바이스 토큰

    Returns:
        검증 성공 여부
    """
    expected_token = REGISTERED_DEVICES.get(device_id)
    if expected_token is None:
        logger.warning(f"[Auth] 미등록 디바이스: {device_id}")
        return False
    if expected_token != token:
        logger.warning(f"[Auth] 토큰 불일치: device_id={device_id}")
        return False
    logger.info(f"[Auth] 인증 성공: device_id={device_id}")
    return True
