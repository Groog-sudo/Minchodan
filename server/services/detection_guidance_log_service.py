import json
import os
import sys
import time
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from server.db.connection import async_sessionmaker_factory
from server.db.models import DetectionGuidanceLog, StreamType
from server.db.repositories import DetectionGuidanceLogRepository
from server.db.schemas import DetectionGuidanceLogCreate, DetectionGuidanceLogResponse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ==========================================
# VIBE PART - 서비스 클래스 설명
#
# [이 클래스가 하는 일]
# - detection_guidance_logs 테이블에 탐지/안내 이벤트 로그를 저장하는 서비스 계층입니다.
# - Router에서 넘겨받은 DTO(DetectionGuidanceLogCreate)를
#   ORM 객체(DetectionGuidanceLog)로 변환해 Repository에 전달합니다.
#
# [3계층 구조에서의 위치]
# Router (API 입구) -> Service (비즈니스 로직) -> Repository (DB 저장)
# 이 클래스는 중간(Service) 계층입니다.
#
# [event_id 중복 방지 원칙]
# - 같은 event_id가 두 번 들어오면 두 번째 요청은 저장하지 않고 기존 로그를 반환합니다.
# - 클라이언트 재전송(retry) 등 중복 요청으로 인한 데이터 오염을 막기 위한 설계입니다.
# ==========================================
class DetectionGuidanceLogService:
    def __init__(self, session: AsyncSession):
        # VIBE: AsyncSession을 주입받아 Repository에 넘깁니다.
        # 세션은 FastAPI의 Depends(get_db)에서 생성되고 요청이 끝나면 자동으로 닫힙니다.
        self.session = session
        self.log_repo = DetectionGuidanceLogRepository(session)

    # ==========================================
    # HARDCODE PART - create_log 설명 및 작성 조건
    #
    # [기능 설명]
    # - DTO(payload)를 받아 DB에 로그를 저장하고 응답 DTO를 반환합니다.
    # - 내부에서 event_id 중복 검사 -> ORM 객체 생성 -> 저장 -> 응답 변환 순서로 동작합니다.
    #
    # [파라미터 설명]
    # - payload: DetectionGuidanceLogCreate
    #   event_id, user_id, device_id, detected_at,
    #   stream_type, detected_objects_json, tts_text 필드를 가집니다.
    #
    # [반환 설명]
    # - DetectionGuidanceLogResponse: 저장된(또는 기존) 로그의 응답 DTO입니다.
    #
    # [작성 조건 - 반드시 이 순서대로 구현]
    # 1) payload.event_id가 있으면(None이 아니면) get_by_event_id()로 중복 조회
    #    - 이미 저장된 로그가 있으면 -> model_validate()로 Response 변환 후 즉시 반환
    # 2) DetectionGuidanceLog ORM 객체를 payload 값으로 생성
    #    - 컬럼명: event_id, user_id, device_id, detected_at,
    #              stream_type, detected_objects_json, tts_text
    # 3) self.log_repo.create(log)로 저장 후 Response 변환해 반환
    # ==========================================
    async def create_log(self, payload: DetectionGuidanceLogCreate) -> DetectionGuidanceLogResponse:
        # HINT 1: event_id 중복 검사
        # if payload.event_id:
        #     existed = await self.log_repo.get_by_event_id(payload.event_id)
        #     if existed is not None:
        #         return DetectionGuidanceLogResponse.model_validate(existed)

        # HINT 2: ORM 객체 생성
        # log = DetectionGuidanceLog(
        #     event_id=payload.event_id,
        #     user_id=payload.user_id,
        #     device_id=payload.device_id,
        #     detected_at=payload.detected_at,
        #     stream_type=payload.stream_type,
        #     detected_objects_json=payload.detected_objects_json,
        #     tts_text=payload.tts_text,
        # )

        # HINT 3: 저장 + 응답 변환 반환
        # saved = await self.log_repo.create(log)
        # return DetectionGuidanceLogResponse.model_validate(saved)

        if payload.event_id:
            existed = await self.log_repo.get_by_event_id(payload.event_id)
            if existed is not None:
                return DetectionGuidanceLogResponse.model_validate(existed)

        log = DetectionGuidanceLog(
            event_id=payload.event_id,
            user_id=payload.user_id,
            device_id=payload.device_id,
            detected_at=payload.detected_at,
            stream_type=payload.stream_type,
            detected_objects_json=payload.detected_objects_json,
            tts_text=payload.tts_text,
            frame_path=payload.frame_path,
            false_positive=payload.false_positive,
            latency_json=payload.latency_json,
            pipeline_debug_json=payload.pipeline_debug_json,
            event_source=payload.event_source,
            stt_transcript_text=payload.stt_transcript_text,
            stt_audio_path=payload.stt_audio_path,
            stt_audio_storage_status=payload.stt_audio_storage_status,
            stt_audio_format=payload.stt_audio_format,
            stt_audio_size_bytes=payload.stt_audio_size_bytes,
            stt_audio_duration_ms=payload.stt_audio_duration_ms,
            stt_audio_sha256=payload.stt_audio_sha256,
            stt_audio_error_code=payload.stt_audio_error_code,
            stt_audio_consent_at=payload.stt_audio_consent_at,
            stt_audio_expires_at=payload.stt_audio_expires_at,
            writer_instance_id=payload.writer_instance_id,
        )

        saved = await self.log_repo.create(log)
        return DetectionGuidanceLogResponse.model_validate(saved)

        # raise NotImplementedError("HARDCODE PART: create_log()를 직접 구현하세요.")

    async def list_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        stream_type: str = "all",
    ) -> list[DetectionGuidanceLogResponse]:
        """콘솔 이력 조회용 최신 로그 목록을 응답 DTO 리스트로 반환합니다."""
        rows = await self.log_repo.list_recent(
            limit=limit,
            offset=offset,
            stream_type=stream_type,
        )
        return [DetectionGuidanceLogResponse.model_validate(row) for row in rows]

    async def count_logs(self, stream_type: str = "all") -> int:
        """콘솔 페이지네이션용 전체 로그 건수."""
        return await self.log_repo.count_all(stream_type=stream_type)

    async def get_log_by_event_id(self, event_id: str) -> DetectionGuidanceLogResponse | None:
        """event_id로 단건 로그를 조회합니다. 프레임 이미지 서빙 검증에 사용합니다."""
        row = await self.log_repo.get_by_event_id(event_id)
        if row is None:
            return None
        return DetectionGuidanceLogResponse.model_validate(row)

    async def update_false_positive(
        self, log_id: int, false_positive: bool | None
    ) -> DetectionGuidanceLogResponse | None:
        # ==========================================
        # 🧠 HARDCODE PART - update_false_positive
        #
        # [기능 설명]
        # - log_repo.update_false_positive를 호출하여 오탐 여부를 업데이트합니다.
        # - 업데이트에 성공하면 DetectionGuidanceLogResponse DTO로 변환하여 반환합니다.
        # - 대상 로그가 없는 경우 None을 반환합니다.
        # ==========================================
        # 💡 [면접 대비 주석]: DB 레포지토리에 오탐 업데이트를 요청하고,
        # 반환된 ORM 객체를 API 계층용 Response DTO로 검증 및 매핑하여 변환합니다.
        updated = await self.log_repo.update_false_positive(log_id, false_positive)
        if updated is None:
            return None
        return DetectionGuidanceLogResponse.model_validate(updated)

    async def update_latency_json(
        self, log_id: int, latency_json: str
    ) -> DetectionGuidanceLogResponse | None:
        """db_save_ms를 합산한 latency_json으로 갱신한다 (persist_detection_guidance_log 전용)."""
        updated = await self.log_repo.update_latency_json(log_id, latency_json)
        if updated is None:
            return None
        return DetectionGuidanceLogResponse.model_validate(updated)


# ==========================================
# HARDCODE PART - build_detected_objects_json 설명 및 작성 조건
#
# [기능 설명]
# - YOLO 탐지 결과 리스트를 DB 저장용 JSON 문자열로 변환합니다.
# - detected_objects_json 컬럼은 MySQL JSON 타입이지만,
#   Python에서는 문자열로 직렬화해서 넘겨야 SQLAlchemy가 처리합니다.
#
# [파라미터 설명]
# - detections: list[dict]
#   예: [{"class_name": "car", "confidence": 0.91, "direction": "front"}]
#
# [작성 조건]
# - json.dumps()를 사용합니다.
# - ensure_ascii=False 옵션을 반드시 사용합니다.
#   이유: 한글 class_name 등이 \uXXXX 형태로 깨지지 않도록
# - 빈 리스트([])도 유효한 입력입니다.
# ==========================================
def build_detected_objects_json(detections: list[dict]) -> str:
    # HINT: return json.dumps(detections, ensure_ascii=False)

    # raise NotImplementedError("HARDCODE PART: build_detected_objects_json()을 직접 구현하세요.")

    return json.dumps(detections, ensure_ascii=False)


async def persist_detection_guidance_log(
    *,
    event_id: str | None,
    stream_type: StreamType | str,
    detections: list[dict],
    tts_text: str,
    user_id: int | None = None,
    device_id: int | None = None,
    frame_path: str | None = None,
    latency_stages: dict[str, float] | None = None,
    pipeline_debug: dict | None = None,
    event_source: str | None = None,
    stt_transcript_text: str | None = None,
    stt_audio_path: str | None = None,
    stt_audio_storage_status: str | None = None,
    stt_audio_format: str | None = None,
    stt_audio_size_bytes: int | None = None,
    stt_audio_duration_ms: int | None = None,
    stt_audio_sha256: str | None = None,
    stt_audio_error_code: str | None = None,
    stt_audio_consent_at: datetime | None = None,
    stt_audio_expires_at: datetime | None = None,
    writer_instance_id: str | None = None,
) -> DetectionGuidanceLogResponse:
    """FastAPI Depends(get_db) 요청 컨텍스트 밖(WS 컨슈머 등)에서 로그를 저장하는 헬퍼.

    async_sessionmaker_factory로 세션을 직접 열고 닫는다. 호출부(DetectionConsumer,
    ws_router)는 반사/인지 경로의 실시간 응답을 막지 않도록 이 호출을 background task로
    감싸고 예외를 흡수해야 한다(이 함수 자체는 예외를 그대로 전파한다).

    latency_stages: 호출부가 이미 측정해 둔 스테이지별 ms(decode/inference/rag/llm/tts/stt 등).
    이 함수는 INSERT 완료 후 자신의 쓰기 소요 시간(db_save_ms)을 여기에 합산해 한 번 더
    UPDATE한다 - 쓰기 시간은 쓰기가 끝나기 전에는 알 수 없기 때문이다.
    """
    stages = dict(latency_stages) if latency_stages else None
    db_save_start = time.perf_counter()
    from server.services.pipeline_debug_builder import serialize_pipeline_debug

    effective_event_source = event_source or (
        "stt" if event_id is not None and event_id.startswith("stt-") else "detection"
    )
    effective_audio_status = stt_audio_storage_status or (
        "not_saved" if effective_event_source == "stt" else "not_applicable"
    )
    effective_writer = (
        writer_instance_id or os.getenv("WRITER_INSTANCE_ID") or os.getenv("HOSTNAME")
    )
    payload = DetectionGuidanceLogCreate(
        event_id=event_id,
        user_id=user_id,
        device_id=device_id,
        detected_at=datetime.now(UTC),
        stream_type=stream_type,
        detected_objects_json=build_detected_objects_json(detections),
        tts_text=tts_text,
        frame_path=frame_path,
        latency_json=json.dumps(stages, ensure_ascii=False) if stages else None,
        pipeline_debug_json=serialize_pipeline_debug(pipeline_debug),
        event_source=effective_event_source,
        stt_transcript_text=stt_transcript_text,
        stt_audio_path=stt_audio_path,
        stt_audio_storage_status=effective_audio_status,
        stt_audio_format=stt_audio_format,
        stt_audio_size_bytes=stt_audio_size_bytes,
        stt_audio_duration_ms=stt_audio_duration_ms,
        stt_audio_sha256=stt_audio_sha256,
        stt_audio_error_code=stt_audio_error_code,
        stt_audio_consent_at=stt_audio_consent_at,
        stt_audio_expires_at=stt_audio_expires_at,
        writer_instance_id=effective_writer,
    )
    async with async_sessionmaker_factory() as session:
        service = DetectionGuidanceLogService(session)
        saved = await service.create_log(payload)

    if not stages:
        return saved

    stages["db_save_ms"] = round((time.perf_counter() - db_save_start) * 1000, 1)
    async with async_sessionmaker_factory() as session:
        service = DetectionGuidanceLogService(session)
        updated = await service.update_latency_json(
            saved.log_id, json.dumps(stages, ensure_ascii=False)
        )
    return updated or saved


# ==========================================
# VIBE PART - build_sample_payload 설명
#
# [이 함수가 하는 일]
# - 테스트용 샘플 payload를 만들어주는 헬퍼 함수입니다.
# - create_log()를 직접 호출해 저장 흐름을 테스트할 때 사용합니다.
#
# [detected_at 원칙]
# - 실제 사용 시에는 클라이언트 프레임 기준 탐지 시각을 넣어야 합니다.
# ==========================================
async def list_frequent_tts_texts(*, min_count: int = 2, limit: int = 30) -> list[str]:
    """서버 기동 시 TTS 캐시 프리워밍에 쓸 빈도 높은 안내 문장 목록을 반환한다.

    FastAPI 요청 컨텍스트 밖(lifespan 시작 단계)에서 호출되므로
    persist_detection_guidance_log와 동일하게 세션을 직접 열고 닫는다.
    """
    async with async_sessionmaker_factory() as session:
        repo = DetectionGuidanceLogRepository(session)
        return await repo.list_frequent_tts_texts(min_count=min_count, limit=limit)


def build_sample_payload() -> DetectionGuidanceLogCreate:
    return DetectionGuidanceLogCreate(
        event_id=None,
        user_id=None,
        device_id=None,
        detected_at=datetime.now(UTC),
        stream_type="unknown",
        detected_objects_json=json.dumps([], ensure_ascii=False),
        tts_text="전방 상황을 확인했습니다.",
    )
