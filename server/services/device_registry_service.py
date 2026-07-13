"""
단말 자동 등록 서비스.

배경: WS 접속 시 클라이언트가 보내는 device_id(예: "dev-001")는 세션 식별용 문자열일
뿐, detection_guidance_logs.user_id/device_id가 참조하는 app_users/user_devices의
정수 PK와는 다르다. 정식 회원가입/기기 등록 플로우가 아직 없어(디바이스 인증
bootstrap은 별도 담당 영역) 이 두 FK가 항상 NULL로 남아 콘솔 이력 테이블의
"사용자"/"기기" 컬럼이 비어 있었다(2026-07-12 발견).

이 모듈은 완전한 회원가입 대신, 처음 보는 device_id를 만나면 익명 app_user 1명과
그 사용자의 user_devices 행을 자동으로 만들어 최소한 FK를 채운다. 실제 로그인/본인
인증을 대체하지 않는다 - 그 작업은 별도 스코프로 남겨둔다.
"""

import sys
from asyncio import Lock

from server.db.connection import async_sessionmaker_factory
from server.db.models import ANON_PHONE_PREFIX, AppUser, DevicePlatform, UserDevice, UserStatus
from server.db.repositories import DeviceRepository, UserRepository

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# device_uuid -> (user_id, device_id). 매 로그 저장마다 DB를 조회하지 않도록
# 프로세스 내 캐시로 둔다(서버 재기동 시 초기화 - 재기동 후 첫 이벤트에서 다시 채워짐).
_cache: dict[str, tuple[int, int]] = {}
_lock = Lock()


async def ensure_device_registered(device_uuid: str, platform: str = "unknown") -> tuple[int, int]:
    """device_uuid에 대응하는 (user_id, device_id) 정수 PK를 반환한다.

    이미 등록돼 있으면 조회만 하고, 처음 보는 device_uuid면 익명 app_user +
    user_devices 행을 새로 만든다. 동시 접속 시 중복 생성을 막기 위해 락으로
    직렬화한다(WS 연결 시 1회만 호출되므로 병목이 되지 않는다).
    """
    if device_uuid in _cache:
        return _cache[device_uuid]

    async with _lock:
        if device_uuid in _cache:
            return _cache[device_uuid]

        platform_enum = (
            DevicePlatform(platform)
            if platform in (p.value for p in DevicePlatform)
            else DevicePlatform.UNKNOWN
        )

        async with async_sessionmaker_factory() as session:
            device_repo = DeviceRepository(session)
            user_repo = UserRepository(session)

            device = await device_repo.get_by_uuid(device_uuid)
            if device is None:
                # phone은 UNIQUE라 device_uuid를 그대로 재사용해 익명 사용자 1명당
                # 단말 1대를 자동 매칭한다(정식 회원 phone과 충돌하지 않도록
                # "anon:" 접두사를 붙인다).
                anon_phone = f"{ANON_PHONE_PREFIX}{device_uuid}"
                user = await user_repo.get_by_phone(anon_phone)
                if user is None:
                    user = await user_repo.create(
                        AppUser(
                            name=f"익명 단말({device_uuid})",
                            phone=anon_phone,
                            disability_severity="미상",
                            status=UserStatus.ACTIVE,
                        )
                    )
                device = await device_repo.create(
                    UserDevice(
                        user_id=user.user_id,
                        device_uuid=device_uuid,
                        platform=platform_enum,
                        is_active=True,
                    )
                )

            _cache[device_uuid] = (device.user_id, device.device_id)
            return _cache[device_uuid]


def get_cached_device_ids(device_uuid: str) -> tuple[int | None, int | None]:
    """캐시에 있으면 (user_id, device_id)를, 없으면 (None, None)을 반환한다.

    로그 저장 경로(반사/인지/STT)는 매 프레임마다 호출되므로 비동기 DB 조회 없이
    캐시만 확인한다 - WS 연결 시 ensure_device_registered()가 미리 채워둔다.
    """
    return _cache.get(device_uuid, (None, None))
