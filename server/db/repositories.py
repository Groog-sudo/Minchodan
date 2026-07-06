import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 데이터베이스 CRUD를 전담하는 Repository 계층입니다.
# 아래 주석의 안내에 따라 코드를 직접 타이핑해 보세요!
# ==========================================

# 1. 필요한 모듈과 모델을 임포트하세요.
# (힌트: typing.Optional, sqlalchemy.ext.asyncio.AsyncSession, sqlalchemy.select)
# (힌트: server.db.models 에서 AdminAccount, AdminLoginAudit, AppUser, UserDevice 임포트)
# 여기에 작성:

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import AdminAccount, AdminLoginAudit, AppUser, UserDevice


# 2. AdminRepository 클래스를 만드세요.
# (힌트: __init__ 에서 session: AsyncSession 을 받습니다.)
# (힌트: async def get_by_employee_no(self, employee_no: str) -> Optional[AdminAccount]: 구현)
# (힌트: async def create(self, admin: AdminAccount) -> AdminAccount: 구현. add, commit, refresh 사용)
# 여기에 작성:
class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # await self.session.execute >>>>  일반 동기 쿼리처럼 쓰면 응답이 올 때까지 서버가 멈춥니다(Blocking). and await keyword을 붙여서 , DB의 employee_no 검색 다른 시각장애인 유저의 요청을 처리 할 수 있도록(None-blocking) 효율성
    async def get_by_employee_no(self, employee_no: str) -> AdminAccount | None:
        result = await self.session.execute(
            select(AdminAccount).where(AdminAccount.employee_no == employee_no)
        )
        return result.scalars().first()

    async def create(self, admin: AdminAccount) -> AdminAccount:
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin


# 3. AuditRepository 클래스를 만드세요.
# (힌트: AdminLoginAudit을 저장하는 create 메서드를 구현합니다)
# 여기에 작성:
class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, audit: AdminLoginAudit) -> AdminLoginAudit:
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(audit)
        return audit

        # add -> Tranjaction memory 에 Obejct를 Push Commit으로 실제 DB 반영 마지막 refresh 저장되면 자동으로 화면나오게


# 4. UserRepository 클래스를 만드세요.
# (힌트: get_by_phone 과 create 메서드를 구현합니다)
# 여기에 작성:


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_phone(self, phone: str) -> AppUser | None:
        result = await self.session.execute(select(AppUser).where(AppUser.phone == phone))
        return result.scalars().first()

    async def create(self, user: AppUser) -> AppUser:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


# 5. DeviceRepository 클래스를 만드세요.
# (힌트: get_by_uuid 와 create 메서드를 구현합니다)
# 여기에 작성:


# 시각장애인 사용자 한 명이 폰을 바꾸시거나 혹은 태블릿 웨어러블 등등 여러기기의 동시에 접속할 가능성을 염두에 두었습니다.
class DeviceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_uuid(self, uuid: str) -> UserDevice | None:
        result = await self.session.execute(
            select(UserDevice).where(UserDevice.device_uuid == uuid)
        )
        return result.scalars().first()

    async def create(self, device: UserDevice) -> UserDevice:
        self.session.add(device)
        await self.session.commit()
        await self.session.refresh(device)
        return device
