# -*- coding: utf-8 -*-
import sys

from server.db.models import AdminAccount, AdminLoginAudit

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 관리자 비즈니스 핵심 로직을 담당하는 Service 계층입니다.
# 아래 주석의 안내에 따라 코드를 직접 타이핑해 보세요!
# ==========================================

# 1. 필요한 FastAPI 예외 모듈, 세션, 의존성들을 임포트하세요.
# (힌트: fastapi.HTTPException, fastapi.status, sqlalchemy.ext.asyncio.AsyncSession)
# (힌트: server.db.models, server.db.repositories, server.db.schemas, server.db.security 관련 모듈 임포트)
# 여기에 작성:
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.repositories import AdminRepository, AuditRepository
from server.db.schemas import AdminCreate, AdminResponse, TokenResponse
from server.db.security import get_password_hash, verify_password, create_access_token


# 2. AdminService 클래스를 만드세요.
# (힌트: __init__ 에서 session을 받고, admin_repo와 audit_repo 인스턴스를 생성합니다)
# 여기에 작성:


# Obejctf -> in Server Producter(__init__) 묶어서 reset 이는 만약에 에러가 나서 부분저장할때 대참사 막기용 
class AdminService:

    def __init__(self, session: AsyncSession):
        self.session = session 
        self.admin_repo = AdminRepository(session)
        self.audit_repo = AuditRepository(session)


# 3. 관리자 회원가입 로직(register_admin)을 구현하세요.
# (힌트: 이미 존재하는 사번이면 400 에러 발생. 존재하지 않으면 비밀번호를 해싱해서 DB에 저장)
# 여기에 작성:

    # 💡 [면접 대비 주석]
    # Q. 마지막에 AdminResponse.model_validate(created)를 쓴 이유?
    # A. "DB에서 갓 꺼낸 데이터에는 비밀번호 해시값 등 민감정보가 다 들어있습니다. 클라이언트에게 응답을 줄 때는
    #    비밀번호가 빠져있는 Pydantic 스키마(AdminResponse) 틀에 맞춰 필터링(검증)해서 안전하게 내보내기 위함입니다!"
    async def register_admin(self, admin_data: AdminCreate) -> AdminResponse:
        existing = await self.admin_repo.get_by_employee_no(admin_data.employee_no)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee number already exists")

        new_admin = AdminAccount(
            employee_no=admin_data.employee_no,
            name=admin_data.name,
            password_hash=get_password_hash(admin_data.password),
            role=admin_data.role
        )

        created = await self.admin_repo.create(new_admin)
        return AdminResponse.model_validate(created)

# 4. 관리자 로그인 로직(login)을 구현하세요.
# (힌트: 비밀번호 검증 실패 시 401 에러. 계정 잠김/삭제 상태면 403 에러)
# (힌트: 성공/실패 여부를 AuditRepository를 통해 기록 남기기)
# (힌트: 최종적으로 create_access_token 을 호출해 TokenResponse 반환)
# 여기에 작성:

    # 💡 [면접 대비 주석 - 로그인 보안]
    # Q. 로그인 실패 처리 시 특별히 신경 쓴 부분?
    # A. "존재하지 않는 사번이든, 비밀번호가 틀렸든 모두 똑같이 '401 UNAUTHORIZED' 와 'Invalid credentials'로
    #    뭉뚱그려 에러를 반환했습니다. 해커가 유효한 사번을 유추하는 것을 막기 위한 보안 취약점 방어입니다.
    #    또한 어떤 이유로든 실패하면 Audit(감사) 로그를 무조건 남겨 이상 행동을 추적할 수 있게 했습니다!"
    async def login(self, employee_no: str, password: str) -> TokenResponse:
        admin = await self.admin_repo.get_by_employee_no(employee_no)

        if not admin or not verify_password(password, admin.password_hash):
            if admin:
                await self.audit_repo.create(AdminLoginAudit(employee_no=employee_no, success=False))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

        if admin.status != "active":
            await self.audit_repo.create(AdminLoginAudit(employee_no=employee_no, success=False))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

        # 로그인 성공 시 기록 및 토큰 발급
        await self.audit_repo.create(AdminLoginAudit(employee_no=employee_no, success=True))

        access_token = create_access_token(data={"sub": admin.employee_no, "role": admin.role})
        return TokenResponse(access_token=access_token)
