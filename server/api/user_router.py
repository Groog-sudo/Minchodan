# -*- coding: utf-8 -*-
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 앱 클라이언트 엔드포인트(Router) 계층입니다.
# 아래 주석의 안내에 따라 코드를 직접 타이핑해 보세요!
# ==========================================

# 1. 필요한 모듈들을 임포트하세요.
# (힌트: pydantic.BaseModel, fastapi.APIRouter, fastapi.Depends)
# 여기에 작성:


# 2. APIRouter 인스턴스를 생성하세요.
# (힌트: prefix="/api/v1/users", tags=["users"])
# 여기에 작성:


# 3. Request Body 용 DTO(UserRegistrationRequest)를 만드세요.
# (힌트: user: UserCreate, device: DeviceCreate 를 담는 BaseModel)
# 여기에 작성:


# 4. 사용자/기기 등록 API 엔드포인트(@router.post("/register"))를 만드세요.
# (힌트: UserService 인스턴스를 만들고 register_user_and_device 호출)
# 여기에 작성:
