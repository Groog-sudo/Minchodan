# -*- coding: utf-8 -*-
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 관리자용 HTTP 엔드포인트(Router) 계층입니다.
# 아래 주석의 안내에 따라 코드를 직접 타이핑해 보세요!
# ==========================================

# 1. FastAPI 관련 모듈과 get_db 의존성을 임포트하세요.
# (힌트: fastapi.APIRouter, fastapi.Depends, fastapi.security.OAuth2PasswordRequestForm)
# (힌트: server.db.connection 에서 get_db 임포트)
# 여기에 작성:
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.connection import get_db
from server.db.schemas import AdminCreate, AdminResponse, TokenResponse
from server.services.admin_service import AdminService



# 💡 [면접 대비 주석 - 의존성 주입(Depends)]
# Q. 라우터 파일에 `get_db`를 임포트해서 굳이 `Depends`로 묶어 쓰는 이유가 뭔가요?
# A. "FastAPI의 강력한 무기인 의존성 주입(Dependency Injection)을 쓰기 위해서입니다!
#    이렇게 하면 API 요청이 들어올 때마다 자동으로 DB 커넥션을 열어주고, 
#    요청이 끝나면 성공이든 에러든 상관없이 커넥션을 안전하게 닫아줍니다(자동 수거).
#    덕분에 개발자가 매번 연결하고 닫는 코드를 안 짜도 되어 실수가 0%가 됩니다!"

# 2. APIRouter 인스턴스를 생성하세요.
# (힌트: prefix="/api/v1/admin", tags=["admin"])
# 여기에 작성:
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# 3. 관리자 가입 API 엔드포인트(@router.post("/register"))를 만드세요.
# (힌트: Depends(get_db) 로 세션을 주입받아 AdminService 호출)
# 여기에 작성:
@router.post("/register", response_model=AdminResponse)
async def register_admin(admin_data: AdminCreate, db: AsyncSession = Depends(get_db)):
    service = AdminService(db)
    return await service.register_admin(admin_data)


# 4. 관리자 로그인 API 엔드포인트(@router.post("/login"))를 만드세요.
# (힌트: OAuth2PasswordRequestForm 을 인자로 받아서 폼 데이터 기반 로그인 처리)
# 여기에 작성:
# 💡 [면접 대비 주석 - 로그인 폼 데이터]
# Q. 로그인할 때 일반 JSON(AdminCreate) 안 쓰고 OAuth2PasswordRequestForm을 쓴 이유?
# A. "FastAPI 내장 OAuth2 인증 표준을 따르기 위해서입니다! 이 폼을 쓰면 
#    클라이언트가 JSON이 아니라 'x-www-form-urlencoded' 방식으로 아이디/비번을 
#    전송하게 되고, 향후 Swagger UI에서도 자동으로 자물쇠 모양(Authorize 버튼)이
#    생성되어 API 테스트나 프론트 연동이 압도적으로 편해집니다."
@router.post("/login", response_model=TokenResponse)
async def login_admin(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    service = AdminService(db)
    return await service.login(employee_no=form_data.username, password=form_data.password)
