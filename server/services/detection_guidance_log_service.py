import json
import sys
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import DetectionGuidanceLog
from server.db.repositories import DetectionGuidanceLogRepository
from server.db.schemas import DetectionGuidanceLogCreate, DetectionGuidanceLogResponse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ==========================================
# VIBE PART (설명 중심, 반복 작업 위임 영역)
# - 함수/변수/구조를 빠르게 조립하고 전체 흐름을 연결하는 영역입니다.
# - 핵심 판단(중복 기준, 필수 필드 정책)은 HARDCODE PART에서 확정합니다.
# ==========================================
class DetectionGuidanceLogService:
    """detction_guidance_logs 적재 서비스.

    역할:
    1) DTO 입력 검증 결과를 ORM으로 변환
    2) event_id 중복 시 재적재 방지
    3) 저장 완료 후 응답 DTO 반환
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.log_repo = DetectionGuidanceLogRepository(session)

    # ==========================================
    # HARDCODE PART (면접/발표 핵심 방어 영역)
    # 이 함수의 핵심 로직은 일부러 비워두었습니다.
    # 아래 힌트 순서대로 직접 작성하세요.
    #
    # 조건 설명:
    # 1) payload.event_id가 있으면 get_by_event_id()로 중복 검사
    # 2) 중복 로그가 있으면 Response로 바로 반환
    # 3) 없으면 DetectionGuidanceLog(...) 생성
    # 4) repo.create(...) 저장 후 Response 변환 반환
    # ==========================================
    async def create_log(self, payload: DetectionGuidanceLogCreate) -> DetectionGuidanceLogResponse:
        # HINT 1: event_id가 있으면 중복 조회
        # existed = ...
        # if existed is not None:
        #     return ...

        # HINT 2: ORM 객체 생성
        # log = DetectionGuidanceLog(...)

        # HINT 3: 저장 + 응답 변환
        # saved = await self.log_repo.create(log)
        # return DetectionGuidanceLogResponse.model_validate(saved)

        raise NotImplementedError("HARDCODE PART: create_log를 직접 구현하세요.")


# ==========================================
# HARDCODE PART (직접 작성용 유틸 템플릿)
# 이 함수는 "탐지 객체 리스트 -> JSON 문자열" 변환을 담당합니다.
# ==========================================
def build_detected_objects_json(detections: list[dict]) -> str:
    """탐지 객체 배열을 DB 저장용 JSON 문자열로 변환합니다.

    예시 입력:
    [
        {"class_name": "car", "confidence": 0.91, "direction": "front"},
        {"class_name": "bollard", "confidence": 0.74, "direction": "left"},
    ]
    """
    # HINT:
    # 1) ensure_ascii=False를 사용하면 한글이 \uXXXX로 깨지지 않습니다.
    # 2) DB 저장 컬럼은 LONGTEXT이므로 문자열 직렬화가 필요합니다.
    # return json.dumps(detections, ensure_ascii=False)
    raise NotImplementedError("HARDCODE PART: build_detected_objects_json을 직접 구현하세요.")


# ==========================================
# VIBE PART (테스트용 샘플 payload 생성)
# - detected_at은 클라이언트 프레임 시각을 원칙으로 합니다.
# ==========================================
def build_sample_payload() -> DetectionGuidanceLogCreate:
    return DetectionGuidanceLogCreate(
        event_id=None,
        user_id=None,
        device_id=None,
        detected_at=datetime.now(UTC),
        stream_type="unknown",
        detected_objects_json=build_detected_objects_json([]),
        tts_text="전방 상황을 확인했습니다.",
    )
