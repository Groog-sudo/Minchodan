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

from server.db.models import (
    AdminAccount,
    AdminLoginAudit,
    AppUser,
    DetectionGuidanceLog,
    UserDevice,
)


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


class DetectionGuidanceLogRepository:
    # ==========================================
    # VIBE PART - 클래스 설명
    # - 이 클래스는 detection_guidance_logs 테이블에 대한
    #   모든 DB 접근(조회/저장)을 전담하는 Repository 계층입니다.
    # - Router → Service → Repository 3계층 구조에서 가장 바닥 계층입니다.
    # - "DB와 직접 대화하는 번역가" 역할이라고 이해하면 쉽습니다.
    # ==========================================

    def __init__(self, session: AsyncSession):
        # VIBE: session은 SQLAlchemy가 제공하는 DB 연결 객체입니다.
        # FastAPI의 Depends(get_db)로 주입받아, 요청 하나당 세션 하나가 생성됩니다.
        # 세션이 있어야 SELECT/INSERT 같은 DB 명령을 실행할 수 있습니다.
        self.session = session

    # ==========================================
    # VIBE PART - get_by_event_id 설명
    # - event_id로 기존 로그를 조회합니다.
    # - Service에서 "이미 저장된 이벤트인지" 중복 검사할 때 사용합니다.
    # - event_id가 UNIQUE 컬럼이므로 결과는 0건 또는 1건입니다.
    # - 반환 타입이 DetectionGuidanceLog | None 인 이유:
    #   없으면 None, 있으면 ORM 객체를 돌려줍니다.
    # ==========================================
    async def get_by_event_id(self, event_id: str) -> DetectionGuidanceLog | None:
        result = await self.session.execute(
            select(DetectionGuidanceLog).where(DetectionGuidanceLog.event_id == event_id)
        )
        return result.scalars().first()

    # ==========================================
    # VIBE PART - list_recent 설명
    # - 콘솔 이력 조회용으로 최신 로그부터 페이지 단위로 반환합니다.
    # - detected_at 내림차순 정렬에 IDX_DETECTION_GUIDANCE_LOGS_DETECTED_AT
    #   인덱스가 사용됩니다.
    # ==========================================
    async def list_recent(self, limit: int = 50, offset: int = 0) -> list[DetectionGuidanceLog]:
        result = await self.session.execute(
            select(DetectionGuidanceLog)
            .order_by(DetectionGuidanceLog.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==========================================
    # HARDCODE PART - create 설명 및 작성 조건
    #
    # [기능 설명]
    # - DetectionGuidanceLog ORM 객체를 받아 DB에 INSERT하고 저장된 객체를 반환합니다.
    # - 트랜잭션 3단계(add → commit → refresh)가 핵심 로직입니다.
    #
    # [트랜잭션 3단계 원리]
    # 1) self.session.add(log)
    #    - ORM 객체를 세션의 "대기열(메모리)"에 등록합니다.
    #    - 아직 DB에 저장되지 않은 상태입니다.
    # 2) await self.session.commit()
    #    - 대기열에 있는 변경사항을 실제 DB에 반영합니다. (INSERT 실행)
    #    - await를 붙여야 비동기로 처리되어 다른 요청을 막지 않습니다.
    # 3) await self.session.refresh(log)
    #    - DB에서 방금 저장된 행을 다시 읽어 log 객체를 갱신합니다.
    #    - AUTO_INCREMENT로 생성된 log_id, server_default인 created_at 등
    #      DB가 자동으로 채운 값들이 이 단계에서 파이썬 객체에 반영됩니다.
    #
    # [작성 조건]
    # - 반드시 add → commit → refresh 순서를 지켜야 합니다.
    # - commit 없이 refresh를 호출하면 아직 저장 안 된 데이터를 읽으려 해서 오류가 납니다.
    # ==========================================
    async def create(self, log: DetectionGuidanceLog) -> DetectionGuidanceLog:
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def update_false_positive(
        self, log_id: int, false_positive: bool | None
    ) -> DetectionGuidanceLog | None:
        # ==========================================
        # 🧠 HARDCODE PART - update_false_positive
        #
        # [기능 설명]
        # - log_id로 DetectionGuidanceLog를 조회하여 false_positive 값을 업데이트하고 커밋한 후 반환합니다.
        # - 만약 해당하는 로그가 없으면 None을 반환합니다.
        # ==========================================
        # 💡 [면접 대비 주석]: log_id로 로그를 찾아서 false_positive 상태를 수정하고
        # 트랜잭션을 commit/refresh하여 DB와 파이썬 객체 상태를 동기화합니다.
        result = await self.session.execute(
            select(DetectionGuidanceLog).where(DetectionGuidanceLog.log_id == log_id)
        )
        log = result.scalars().first()
        if log:
            log.false_positive = false_positive
            await self.session.commit()
            await self.session.refresh(log)
        return log
