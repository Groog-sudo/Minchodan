# -*- coding: utf-8 -*-
# server/api/auth.py
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logger = logging.getLogger(__name__)

REGISTERED_DEVICES = {
    "dev-001": "token-abc-001",
    "dev-002": "token-abc-002",
}

async def verify_device(device_id: str, token: str) -> bool:
    expected_token = REGISTERED_DEVICES.get(device_id)
    if expected_token is None:
        logger.warning(f"[인증 실패] 미등록 디바이스: {device_id}")
        return False
    if expected_token != token:
        logger.warning(f"[인증 실패] 토큰 불일치: device_id={device_id}")
        return False
    logger.info(f"[인증 성공] device_id={device_id}")
    return True
