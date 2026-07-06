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

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.connection import get_db
from server.db.schemas import AppUserCreate, AppUserResponse, UserDeviceCreate
from server.services.user_service import UserService

# 💡 [면접 대비 주석 - 계층 분리의 장점]
# Q. 굳이 API 엔드포인트 파일(user_router)을 분리한 이유가 있나요?
# A. "도메인별(Admin/User)로 관심사를 철저히 분리하기 위해서입니다!
#    라우터는 오직 '데이터를 받고 돌려주는 우체국' 역할만 하고,
#    실제 처리는 Service가 전담하여 코드가 꼬이는 것을 원천 차단했습니다."


# 2. APIRouter 인스턴스를 생성하세요.
# (힌트: prefix="/api/v1/users", tags=["users"])
# 여기에 작성:
# type: ignore noqa: S105
router = APIRouter(prefix="/api/v1/users", tags=["users"])


# 3. Request Body 용 DTO(UserRegistrationRequest)를 만드세요.
# (힌트: user: UserCreate, device: DeviceCreate 를 담는 BaseModel)
# 여기에 작성:
class UserRegistrationRequest(BaseModel):
    user: AppUserCreate
    device: UserDeviceCreate


# 4. 사용자/기기 등록 API 엔드포인트(@router.post("/register"))를 만드세요.
# (힌트: UserService 인스턴스를 만들고 register_user_and_device 호출)
# 여기에 작성:
# 💡 [면접 대비 주석 - 통합 DTO 패턴]
# Q. 유저 생성 정보와 기기 생성 정보를 굳이 UserRegistrationRequest라는
#    별도의 DTO(BaseModel)로 묶어서 받은 이유가 뭔가요?
# A. "클라이언트와 서버 간의 '데이터 계약(Contract)'을 명확히 하기 위해서입니다!
#    이렇게 명시적으로 묶어두면 Swagger UI 문서에 계층 구조가 아주 깔끔하게 나오고,
#    프론트엔드 개발자가 API 명세서를 헷갈릴 일이 없어 협업 효율이 극대화됩니다."
@router.post("/register", response_model=AppUserResponse)
async def register_user(request: UserRegistrationRequest, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.register_user_and_device(
        user_data=request.user, device_data=request.device
    )
