import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 시각장애인 앱 기기 등록 및 사용자 맵핑을 담당하는 Service입니다.
# 아래 주석의 안내에 따라 코드를 직접 타이핑해 보세요!
# ==========================================

# 1. 필요한 FastAPI 모듈과 세션, 모델/스키마 등을 임포트하세요.
# 여기에 작성:

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import AppUser, UserDevice
from server.db.repositories import DeviceRepository, UserRepository
from server.db.schemas import AppUserCreate, AppUserResponse, UserDeviceCreate

# 💡 [면접 대비 주석 - 서비스 계층의 역할]
# Q. 굳이 API 라우터 놔두고 Service를 따로 만든 이유가 뭡니까?
# A. "유저를 생성하고 기기를 등록하는 2개의 DB 작업이 무조건 '하나의 트랜잭션'으로
#    묶여야 안전하기 때문입니다. 비즈니스 로직과 DB 트랜잭션 관리를 Service에 몰아넣어
#    API 라우터 코드를 가볍게 유지했습니다!"


# 2. UserService 클래스를 만드세요.
# (힌트: __init__ 에서 user_repo 와 device_repo 생성)
# 여기에 작성:
class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.device_repo = DeviceRepository(session)

    # 3. 사용자 및 기기 동시 등록 로직(register_user_and_device)을 구현하세요.
    # (힌트: 유저가 없으면 새로 AppUser 생성. 이후 기기가 없으면 새로 등록.)
    # (힌트: 기기가 이미 있는데 다른 유저의 것이라면 400 에러(Device UUID conflict) 발생)
    # 여기에 작성:

    # 💡 [면접 대비 주석 - 스마트폰 기기 충돌(Conflict) 방어 로직]
    # Q. 기기 등록 로직 중에 특별히 에러 처리를 넣은 이유가 있나요?
    # A. "중고폰 거래나, 번호가 바뀌는 상황 등을 고려해 '기기 고유 식별자(UUID)'가
    #    이미 다른 유저 이름으로 등록되어 있다면 해킹이나 충돌 우려가 있으므로
    #    HTTP 400 에러를 던져 기존 매핑을 보호하도록 짰습니다!"
    async def register_user_and_device(
        self, user_data: AppUserCreate, device_data: UserDeviceCreate
    ) -> AppUserResponse:
        # 1. 사용자 생성 또는 조회
        user = await self.user_repo.get_by_phone(user_data.phone)
        if not user:
            new_user = AppUser(
                name=user_data.name,
                phone=user_data.phone,
                disability_severity=user_data.disability_severity,
            )
            user = await self.user_repo.create(new_user)

        # 2. 기기 등록 및 충돌 검사
        device = await self.device_repo.get_by_uuid(device_data.device_uuid)
        if not device:
            new_device = UserDevice(
                user_id=user.user_id,
                device_uuid=device_data.device_uuid,
                platform=device_data.platform,
            )

            await self.device_repo.create(new_device)
        elif device.user_id != user.user_id:
            # 남의 폰(UUID)으로 자기 계정에 등록하려고 하면 컷!
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device UUID is registered to another user",
            )

        return AppUserResponse.model_validate(user)
