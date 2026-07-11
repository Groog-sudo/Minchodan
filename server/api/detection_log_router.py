"""
탐지/안내 로그 조회 및 이벤트 프레임 이미지 서빙 라우터.

콘솔(운영자)의 사후 이력 조회 화면이 사용합니다:
- GET /api/v1/admin/detection-logs: 최신 로그 목록 (frame_path 포함)
- GET /api/v1/admin/event-frames/{event_id}: 이벤트 발생 시점 프레임 JPEG

인증: get_current_admin (Authorization 헤더 또는 ?token= 쿼리).
<img> 태그는 커스텀 헤더를 못 붙이므로 이미지 요청은 쿼리 토큰을 사용합니다
(SSE EventSource와 동일한 우회 패턴).
"""

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.dependencies import get_current_admin
from server.db.connection import get_db
from server.db.schemas import DetectionGuidanceLogResponse
from server.services.detection_guidance_log_service import DetectionGuidanceLogService
from server.services.event_frame_store import is_valid_event_id, resolve_frame_path

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/detection-logs", response_model=list[DetectionGuidanceLogResponse])
async def list_detection_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_id: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[DetectionGuidanceLogResponse]:
    """콘솔 이력 테이블용 최신 탐지/안내 로그 목록을 반환합니다."""
    service = DetectionGuidanceLogService(db)
    return await service.list_logs(limit=limit, offset=offset)


@router.get("/event-frames/{event_id}")
async def get_event_frame(
    event_id: str,
    admin_id: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """이벤트 발생 시점 프레임 JPEG을 반환합니다.

    DB에 등록된 frame_path만 서빙하며(임의 파일 접근 차단),
    event_id 형식 검증과 저장소 경로 검증(resolve_frame_path)을 이중으로 거칩니다.
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
    if file_path is None:
        # DB에는 경로가 있으나 파일이 보존 기간 만료 등으로 삭제된 경우
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프레임 이미지 파일이 존재하지 않습니다 (보존 기간 만료 가능).",
        )
    return FileResponse(file_path, media_type="image/jpeg")
