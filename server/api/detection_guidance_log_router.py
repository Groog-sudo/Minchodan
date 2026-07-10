import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# HARDCODE PART - 라우터 파일 목적 및 계층 역할
#
# [이 파일이 하는 일]
# - detection_guidance_logs 로그를 HTTP API로 저장/조회할 수 있게 하는 입구(Router) 계층입니다.
# - Router는 요청을 받고(Service에 전달), Service 결과를 응답으로 돌려주는 역할만 담당합니다.
#
# [계층 분리 원칙]
# - Router: 입구/출구, HTTP 상태코드, 요청 파라미터
# - Service: 비즈니스 규칙(중복 event_id 처리, 저장 정책)
# - Repository: 실제 DB 쿼리 실행
#
# [작성 조건]
# - DB 세션은 반드시 Depends(get_db)로 주입받습니다.
# - 라우터에서 SQLAlchemy 쿼리를 직접 작성하지 않습니다.
# - 예외는 HTTPException으로 변환해 API 소비자가 이해할 수 있게 반환합니다.
# ==========================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.connection import get_db
from server.db.schemas import DetectionGuidanceLogCreate, DetectionGuidanceLogResponse
from server.services.detection_guidance_log_service import (
    DetectionGuidanceLogService,
    build_sample_payload,
)

# ==========================================
# VIBE PART - APIRouter 기본 설정 설명
#
# [prefix]
# - /api/v1/logs: 로그 관련 API를 한 그룹으로 묶습니다.
#
# [tags]
# - Swagger/OpenAPI에서 "detection-guidance-logs" 섹션으로 정리됩니다.
# ==========================================
router = APIRouter(prefix="/api/v1/logs", tags=["detection-guidance-logs"])


# ==========================================
# HARDCODE PART - 로그 생성 API
#
# [기능]
# - 클라이언트/내부 도구가 전달한 DetectionGuidanceLogCreate를 DB에 저장합니다.
# - 동일 event_id가 이미 있으면 Service 정책에 따라 기존 로그를 반환합니다.
#
# [입력]
# - body: DetectionGuidanceLogCreate
#
# [출력]
# - DetectionGuidanceLogResponse
#
# [작성 조건]
# - service = DetectionGuidanceLogService(db)로 생성
# - return await service.create_log(payload) 호출
# - 예외는 500으로 변환하되 내부 메시지는 로그 확인 가능하도록 detail에 유지
# ==========================================
@router.post("/detection-guidance", response_model=DetectionGuidanceLogResponse)
async def create_detection_guidance_log(
    payload: DetectionGuidanceLogCreate,
    db: AsyncSession = Depends(get_db),
) -> DetectionGuidanceLogResponse:
    # HARDCODE PART - 직접 작성 가이드
    # 1) service 객체를 생성하세요.
    #    HINT: service = DetectionGuidanceLogService(db)
    # 2) try/except 블록에서 service.create_log(payload)를 await 호출하세요.
    # 3) 예외 발생 시 HTTPException(500)으로 감싸 반환하세요.
    #    HINT: raise HTTPException(status_code=500, detail=f"로그 저장 실패: {e}") from e
    #
    # 아래는 구조를 이해하기 쉽도록 남긴 최소 템플릿입니다.
    # 핵심 로직 2줄(service 생성 / create_log 호출)은 직접 입력하세요.
    try:
        # TODO(HARDCODE): service 생성
        # service = DetectionGuidanceLogService(db)
        service = DetectionGuidanceLogService(db)

        # TODO(HARDCODE): 저장 서비스 호출
        # return await service.create_log(payload)
        # raise NotImplementedError("HARDCODE PART: create_detection_guidance_log 핵심 2줄을 직접 입력하세요.")
        return await service.log_repo.create_log(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 저장 실패: {e}") from e


# ==========================================
# VIBE PART - event_id 조회 API 설명
#
# [사용 목적]
# - 디버깅/운영 확인 시 event_id 기준으로 로그 존재 여부를 빠르게 확인합니다.
# - event_id는 UNIQUE 컬럼이므로 최대 1건만 반환됩니다.
# ==========================================
@router.get("/detection-guidance/by-event", response_model=DetectionGuidanceLogResponse)
async def get_detection_guidance_log_by_event_id(
    event_id: str = Query(..., min_length=1, max_length=64),
    db: AsyncSession = Depends(get_db),
) -> DetectionGuidanceLogResponse:
    service = DetectionGuidanceLogService(db)
    try:
        found = await service.get_by_event_id(event_id)
        if found is None:
            raise HTTPException(status_code=404, detail="해당 event_id 로그를 찾을 수 없습니다.")
        return DetectionGuidanceLogResponse.model_validate(found)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {e}") from e


# ==========================================
# HARDCODE PART - 샘플 저장 API
#
# [기능]
# - build_sample_payload()로 샘플 로그를 생성해 저장 경로를 빠르게 점검합니다.
# - Postman/Swagger에서 DB 연동 스모크 테스트할 때 사용합니다.
#
# [작성 조건]
# - 샘플 payload 생성 -> service.create_log 호출 순서를 유지합니다.
# ==========================================
@router.post("/detection-guidance/sample", response_model=DetectionGuidanceLogResponse)
async def create_detection_guidance_log_sample(
    db: AsyncSession = Depends(get_db),
) -> DetectionGuidanceLogResponse:
    # HARDCODE PART - 직접 작성 가이드
    # 1) service 객체 생성
    #    HINT: service = DetectionGuidanceLogService(db)
    # 2) 샘플 payload 생성
    #    HINT: sample_payload = build_sample_payload()
    # 3) service.create_log(sample_payload) 호출 후 반환
    # 4) 예외를 HTTPException(500)으로 래핑
    try:
        # TODO(HARDCODE): service 생성
        service = DetectionGuidanceLogService(db)

        # TODO(HARDCODE): 샘플 payload 생성
        sample_payload = build_sample_payload()

        # TODO(HARDCODE): 저장 호출
        return await service.create_log(sample_payload)
        # raise NotImplementedError("HARDCODE PART: create_detection_guidance_log_sample 핵심 3줄을 직접 입력하세요.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"샘플 로그 저장 실패: {e}") from e
