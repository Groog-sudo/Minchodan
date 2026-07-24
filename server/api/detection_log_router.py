"""
탐지/안내 로그 조회 및 이벤트 프레임 이미지 서빙 라우터.

콘솔(운영자)의 사후 이력 조회 화면이 사용합니다:
- GET /api/v1/admin/detection-logs: 최신 로그 목록 (frame_path 포함)
- GET /api/v1/admin/event-frames/{event_id}: 이벤트 발생 시점 프레임 JPEG

인증: get_current_admin의 Authorization Bearer 헤더만 허용합니다.
콘솔은 인증 fetch로 프레임 Blob을 받은 뒤 브라우저 전용 object URL로 표시합니다.
"""

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.dependencies import get_current_admin, require_operator
from server.db.connection import get_db
from server.db.schemas import DetectionGuidanceLogResponse, FalsePositiveUpdateRequest
from server.services.detection_guidance_log_service import DetectionGuidanceLogService
from server.services.event_frame_store import is_valid_event_id, resolve_frame_path
from server.services.remote_storage_client import fetch_event_frame, resolve_event_frame_url

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.put("/detection-logs/{log_id}/false-positive", response_model=DetectionGuidanceLogResponse)
async def update_detection_log_false_positive(
    log_id: int,
    payload: FalsePositiveUpdateRequest,
    admin_id: str = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
) -> DetectionGuidanceLogResponse:
    # ==========================================
    # 🧠 HARDCODE PART - update_detection_log_false_positive
    #
    # [기능 설명]
    # - DetectionGuidanceLogService를 호출하여 log_id 로그의 false_positive를 payload.false_positive 값으로 업데이트합니다.
    # - 결과가 None인 경우, 404 HTTP 예외(HTTPException)를 발생시킵니다.
    # - 업데이트에 성공한 로그 응답 DTO를 반환합니다.
    # ==========================================
    # 💡 [면접 대비 주석]: Service 계층에 데이터 제어를 위임하며,
    # 존재하지 않는 로그에 대해서는 RESTful 가이드에 따라 404 Not Found 예외를 프론트엔드에 응답합니다.
    service = DetectionGuidanceLogService(db)
    log = await service.update_false_positive(log_id, payload.false_positive)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 로그를 찾을 수 없습니다.",
        )
    return log


@router.get("/detection-logs", response_model=list[DetectionGuidanceLogResponse])
async def list_detection_logs(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    stream_type: str = Query("all", pattern="^(all|reflex|cognitive)$"),
    admin_id: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[DetectionGuidanceLogResponse]:
    """콘솔 이력 테이블용 최신 탐지/안내 로그 목록을 반환합니다.

    전체 건수는 X-Total-Count 응답 헤더로 함께 내려준다(응답 바디는 기존과 동일한
    배열 형태를 유지 - 콘솔 페이지네이션이 전체 페이지 수를 계산하는 데 사용).
    """
    service = DetectionGuidanceLogService(db)
    total = await service.count_logs(stream_type=stream_type)
    response.headers["X-Total-Count"] = str(total)
    return await service.list_logs(limit=limit, offset=offset, stream_type=stream_type)


@router.get("/event-frames/{event_id}")
async def get_event_frame(
    event_id: str,
    delivery: str = Query(
        "proxy",
        pattern="^(proxy|presigned)$",
        description="proxy=JPEG 바이트 프록시(기본), presigned=R2 단기 URL로 302",
    ),
    admin_id: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """이벤트 발생 시점 프레임 JPEG을 반환합니다.

    DB에 등록된 frame_path만 서빙하며(임의 파일 접근 차단),
    event_id 형식 검증과 저장소 경로 검증(resolve_frame_path)을 이중으로 거칩니다.
    R2 백엔드에서 delivery=presigned 이면 GetObject 프록시 대신 단기 URL로 리다이렉트합니다.
    """
    if not is_valid_event_id(event_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_id 형식이 올바르지 않습니다.",
        )
    service = DetectionGuidanceLogService(db)
    log = await service.get_log_by_event_id(event_id)
    if log is None or not log.frame_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이벤트의 프레임 이미지가 없습니다.",
        )
    file_path = resolve_frame_path(log.frame_path)
    if file_path is not None:
        return FileResponse(file_path, media_type="image/jpeg")

    if delivery == "presigned":
        url = resolve_event_frame_url(log.frame_path)
        if url:
            return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    remote_frame = await fetch_event_frame(log.frame_path)
    if remote_frame is not None:
        return Response(content=remote_frame, media_type="image/jpeg")

    # DB에는 경로가 있으나 파일이 보존 기간 만료 등으로 삭제된 경우
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="프레임 이미지 파일이 존재하지 않습니다 (보존 기간 만료 가능).",
    )
