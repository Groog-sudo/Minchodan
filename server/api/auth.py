"""
디바이스 토큰 검증 모듈.
hello 핸드셰이크 시 device_id와 token을 검증합니다.

[2026-07-09 정정] 기존에는 REGISTERED_DEVICES 정적 딕셔너리(만료 없는 고정 문자열
비교)만으로 검증해, 관리자 콘솔 로그인이 쓰는 server/db/security.py의 JWT 발급/검증
체계와 완전히 분리돼 있었다. UserDevice 테이블(server/db/models.py)이 device_uuid로
단말-사용자 관계를 이미 모델링해뒀으나 DB 마이그레이션이 아직 실행되지 않아(별도 후속
과제), 이번 정정에서는 DB 조회 없이도 즉시 쓸 수 있도록 verify_device()가 정적
딕셔너리와 서명된 JWT(decode_access_token) 두 경로를 모두 인정하도록 확장한다.
issue_device_token()으로 새 단말용 JWT를 발급할 수 있어, 하드코딩 딕셔너리에 단말을
추가하지 않고도 토큰 기반 등록이 가능해진다. UserDevice 테이블과의 실제 연동은
server/db/init_db.py(스키마 생성 스크립트) 실행 이후 후속 작업으로 남긴다.
"""

import contextlib
import hmac
import logging
import os
import sys

import jwt

from server.db.security import create_access_token, decode_access_token

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# 2026-07-11 인증 기본값 제거(dev 개선 계획서 §2): 정적 디바이스 토큰을 코드
# 하드코딩에서 환경 변수로 분리한다.
# - DEVICE_STATIC_TOKENS="dev-001:token-abc-001,dev-002:token-abc-002" 형식.
# - 미설정 시: 개발 환경은 기존 개발 기본 토큰으로 폴백(경고 로그, 하위 호환),
#   운영 환경(APP_ENV=production)은 빈 목록(fail-closed - JWT 경로만 인정).
_DEV_DEFAULT_DEVICES: dict[str, str] = {
    "dev-001": "token-abc-001",
    "dev-002": "token-abc-002",
}


def _load_registered_devices() -> dict[str, str]:
    raw = os.getenv("DEVICE_STATIC_TOKENS", "").strip()
    if raw:
        devices: dict[str, str] = {}
        for item in raw.split(","):
            device_id, _, token = item.strip().partition(":")
            if device_id and token:
                devices[device_id] = token
            else:
                logger.warning(f"[Auth] DEVICE_STATIC_TOKENS 항목 형식 오류(무시): {item!r}")
        return devices
    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        logger.warning(
            "[Auth] 운영 환경에서 DEVICE_STATIC_TOKENS 미설정 - 정적 토큰 경로를 "
            "비활성화합니다(JWT 디바이스 토큰만 인정)."
        )
        return {}
    logger.warning(
        "[Auth] DEVICE_STATIC_TOKENS 미설정 - 개발 기본 정적 토큰을 사용합니다. "
        "운영 배포 전 반드시 환경 변수로 교체하십시오."
    )
    return dict(_DEV_DEFAULT_DEVICES)


REGISTERED_DEVICES: dict[str, str] = _load_registered_devices()


def issue_device_token(device_id: str) -> str:
    """단말용 서명된 JWT를 발급한다(관리자 도구/등록 스크립트에서 호출).

    verify_device()의 JWT 검증 경로와 짝을 이룬다.
    """
    return create_access_token({"device_id": device_id, "type": "device"})


def _verify_static_token(device_id: str, token: str) -> bool:
    expected_token = REGISTERED_DEVICES.get(device_id)
    return expected_token is not None and hmac.compare_digest(expected_token, token)


def _verify_jwt_token(device_id: str, token: str) -> bool:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        return False
    return payload.get("type") == "device" and payload.get("device_id") == device_id


async def verify_device(device_id: str, token: str) -> bool:
    """디바이스 토큰 검증.

    정적 REGISTERED_DEVICES 딕셔너리(하위 호환) 또는 issue_device_token()이 발급한
    서명된 JWT 중 하나라도 일치하면 통과시킨다.

    Args:
        device_id: 단말 식별자
        token: 사전 발급된 디바이스 토큰(정적 문자열 또는 JWT)

    Returns:
        검증 성공 여부
    """
    if _verify_static_token(device_id, token):
        logger.info(f"[Auth] 인증 성공(정적 토큰): device_id={device_id}")
        return True
    if _verify_jwt_token(device_id, token):
        logger.info(f"[Auth] 인증 성공(JWT): device_id={device_id}")
        return True
    logger.warning(f"[Auth] 토큰 검증 실패: device_id={device_id}")
    return False
