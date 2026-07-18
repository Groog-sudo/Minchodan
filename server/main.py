"""
Minchodan FastAPI GPU 추론 및 관제 서버 메인 엔트리 포인트.
FastAPI 앱을 초기화하고, WebSocket 게이트웨이 라우터 및 실시간 MCP 관제 모니터링 라우터를 마운트합니다.
Lifespan 이벤트를 통해 비동기 MCPManager의 생명주기를 자동으로 제어합니다.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, suppress

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# Ensure server path is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from server.api.admin_member_router import router as admin_member_router
from server.api.admin_router import router as admin_router
from server.api.config import settings
from server.api.detection_log_router import router as detection_log_router
from server.api.monitor import router as monitor_router
from server.api.stt_router import router as stt_router
from server.api.user_router import router as user_router
from server.api.ws_router import router as ws_router
from server.detection.consumer import get_default_consumer
from server.mcp.manager import mcp_manager
from server.navigation.server import app as navigation_app

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

logger = logging.getLogger(__name__)

# Load environment configuration (guide 3.4)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 어플리케이션의 시작 및 종료 시점에 실행되는 비동기 라이프사이클 이벤트.
    """
    logger.info("Minchodan API Server 시작 중...")

    # 0. LLM 핫스왑용 GPU 모니터링 태스크 기동 (6단계 RAG/LLM 핫스왑용)
    from server.orchestration.llm_client_factory import LLMClientFactory

    try:
        LLMClientFactory.start_gpu_monitor()
        logger.info("LLMClientFactory GPU 모니터링 시작 완료")
    except Exception as e:
        logger.error(f"LLMClientFactory GPU 모니터링 시작 실패: {e}")

    # 1. MCP 통합 관리용 Redis Stream Consumer 태스크 시작
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    await mcp_manager.start_consumer(redis_url=redis_url)

    # 2. DetectionConsumer 시작 (3단계: stream_splitter 큐 → pipeline → WS/Redis)
    consumer = get_default_consumer()
    try:
        await consumer.start()
        logger.info("DetectionConsumer 시작 완료")
    except Exception as e:
        logger.error(f"DetectionConsumer 시작 실패 (큐는 유지): {e}")

    # 3. Whisper 모델 프리로드 (2026-07-11 실측: 지연 로딩 상태에서 재시작 후 첫
    # STT 요청이 모델 로딩 8~10초를 그대로 떠안아 사용자 체감 지연이 컸다).
    # 이벤트 루프를 막지 않도록 스레드로 위임하고, 실패해도 기존 지연 로딩으로
    # 동작하므로 서버 기동은 막지 않는다.
    from server.stt.stt_config import DEFAULT_REQUEST_MODEL
    from server.stt.stt_service import SttService

    def _preload_whisper() -> None:
        try:
            SttService.get_model(DEFAULT_REQUEST_MODEL)
            logger.info(f"Whisper 모델 프리로드 완료: {DEFAULT_REQUEST_MODEL}")
        except Exception as e:
            logger.error(f"Whisper 모델 프리로드 실패 (지연 로딩으로 폴백): {e}")

    stt_preload_task = asyncio.create_task(asyncio.to_thread(_preload_whisper))

    # 4. 이벤트 프레임 보존 기간 초과분 정리 (콘솔 오탐 검증용 이미지, 기본 7일)
    # 디스크 IO이므로 스레드로 위임하고 실패해도 기동은 막지 않는다.
    from server.services.event_frame_store import cleanup_expired_frames

    def _cleanup_event_frames() -> None:
        try:
            cleanup_expired_frames()
        except Exception as e:
            logger.error(f"이벤트 프레임 보존 정리 실패: {e}")

    frame_cleanup_task = asyncio.create_task(asyncio.to_thread(_cleanup_event_frames))

    # 5. TTS 캐시 프리워밍: DB 이력에서 빈도 높은 안내 문장을 뽑아 서버 기동 중
    # 미리 합성해둔다(실시간 합성 캐시는 콜드 상태로 시작하면 첫 재생마다
    # 1.4~1.9초 지연이 있었다 - RealtimeTTS.CACHE_MAX_ENTRIES 주석 참조).
    # DB 조회 실패(신규 배포 등으로 로그 없음 포함)해도 서버 기동은 막지 않는다.
    from server.services.detection_guidance_log_service import list_frequent_tts_texts
    from server.tts.realtime_tts import realtime_tts

    async def _prewarm_tts_cache() -> None:
        try:
            limit = int(os.getenv("TTS_PREWARM_LIMIT", "30"))
            min_count = int(os.getenv("TTS_PREWARM_MIN_COUNT", "2"))
            texts = await list_frequent_tts_texts(min_count=min_count, limit=limit)
            warmed = await realtime_tts.prewarm(texts)
            logger.info(f"TTS 캐시 프리워밍 완료: {warmed}/{len(texts)}건")
        except Exception as e:
            logger.error(f"TTS 캐시 프리워밍 실패 (콜드 캐시로 폴백): {e}")

    tts_prewarm_task = asyncio.create_task(_prewarm_tts_cache())

    # 6. Redis Cache Monitor MCP 시작
    from server.mcp.cache_monitor import cache_monitor

    try:
        cache_monitor.start_monitoring()
        logger.info("Redis Cache Monitor MCP 시작 완료")
    except Exception as e:
        logger.error(f"Redis Cache Monitor MCP 시작 실패: {e}")

    # 7. Raspberry Pi 중앙 저장 API 공유 httpx.AsyncClient 생성 (2026-07-17, P1).
    # 매 요청 새 클라이언트를 생성하던 패턴에서 커넥션 풀 재사용(keep-alive)으로 전환.
    # remote_storage_client가 비활성(local backend)이면 no-op에 가깝다.
    from server.services.remote_storage_client import (
        close_shared_client,
        create_shared_client,
    )

    try:
        await create_shared_client()
        logger.info("중앙 저장소 공유 httpx.AsyncClient 생성 완료")
    except Exception as e:
        logger.error(f"중앙 저장소 공유 httpx.AsyncClient 생성 실패 (요청별 폴백): {e}")

    yield

    frame_cleanup_task.cancel()

    stt_preload_task.cancel()

    tts_prewarm_task.cancel()

    # Redis Cache Monitor MCP 중지
    cache_monitor.stop_monitoring()

    # 중앙 저장소 공유 httpx.AsyncClient 종료
    with suppress(Exception):
        await close_shared_client()

    logger.info("Minchodan API Server 종료 중...")
    # 3. DetectionConsumer 중지
    await consumer.stop()
    # 4. Redis Stream Consumer 및 리소스 정리
    await mcp_manager.stop_consumer()


# OpenAPI 태그 메타데이터 정의 (Swagger UI 섹션 안내)
openapi_tags = [
    {
        "name": "WebSocket Gateway",
        "description": (
            "**WebSocket** `ws://{host}/ws/detect?device_id={id}` — "
            "단말(React Native) ↔ GPU 서버 간 실시간 양방향 통신 채널.\n\n"
            "WebSocket은 OAS 3.1 자동 렌더링 미지원이므로 Swagger UI에 개별 항목으로 표시되지 않습니다. "
            "전체 프로토콜 명세는 `docs/design/api_specification.md` 를 참조하십시오.\n\n"
            "**핸드셰이크 순서**: `accept` → `welcome` → `hello` → `auth_ok` → heartbeat 루프\n\n"
            "**수신 메시지 타입**: `hello` · `detection` · `heartbeat_ack`\n\n"
            "**송신 메시지 타입**: `welcome` · `auth_ok` · `ack` · `reflex_alert` · `guide` · `heartbeat` · `error`"
        ),
    },
    {
        "name": "Monitor",
        "description": (
            "운영자 관제 콘솔용 **SSE(Server-Sent Events)** 실시간 스트리밍 API.\n\n"
            "MCP 메트릭 및 탐지 이벤트를 콘솔 프론트엔드로 브로드캐스트합니다."
        ),
    },
    {
        "name": "STT",
        "description": (
            "음성 파일 업로드 기반 **Speech-to-Text** API.\n\n"
            "- `POST /api/v1/stt/transcribe`: 음성 파일을 텍스트로 전사\n"
            "- `POST /api/v1/stt/transcribe-and-guide`: 전사 후 기존 오케스트레이션으로 안내문 생성"
        ),
    },
    {
        "name": "default",
        "description": "헬스체크 및 기타 관리 API.",
    },
]

# FastAPI App 인스턴스 생성
app = FastAPI(
    title="Minchodan GPU Inference Server",
    description=(
        "시각장애인 보행 보조 스마트 가이드독 AI 플랫폼 GPU 추론 및 관제 API 서버.\n\n"
        "- **WebSocket** `/ws/detect`: 단말 실시간 프레임 수신 및 반사/인지 경보 송신\n"
        "- **SSE** `/api/v1/monitor/stream`: 관제 콘솔 실시간 메트릭 스트리밍\n"
        "- **REST** `/health`: 서버 헬스체크\n\n"
        "> WebSocket 전체 명세: `docs/design/api_specification.md` v0.3.0"
    ),
    version="v1.0.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# CORS 미들웨어 추가: 운영자 콘솔(React) 연동용. 허용 출처는 settings.CORS_ORIGINS
# (.env의 CORS_ORIGINS, 기본값은 로컬 개발 콘솔 포트)로 제어한다.
# 2026-07-09 정정: 이전에는 allow_origins=["*"]로 고정돼 있어 배포 환경에서도 모든
# 출처를 허용하는 상태였다(allow_credentials=True와 결합 시 보안상 특히 부적절).
# 2026-07-18 정정: allow_origin_regex="https?://.*"를 제거한다. Starlette
# CORSMiddleware는 allow_origins 또는 allow_origin_regex 중 하나만 매치돼도
# 요청을 허용하므로, regex가 화이트리스트를 무력화했고 allow_credentials=True와
# 결합 시 임의 출처 자격증명 요청이 허용되는 위험이 있었다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # X-Total-Count: 콘솔 Detection Guidance Log 페이지네이션이 전체 건수를 읽으려면
    # 브라우저 fetch()가 이 커스텀 헤더를 볼 수 있어야 한다(CORS 기본값은 표준
    # 헤더만 노출하고 커스텀 헤더는 명시적으로 허용해야 함, 2026-07-12).
    expose_headers=["X-Total-Count"],
)

# 모니터링 라우터 마운트
app.include_router(monitor_router, prefix="/api/v1")

# WebSocket 게이트웨이 라우터 마운트
app.include_router(ws_router, prefix="")

# 사용자 및 관리자 API 라우터 마운트
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(admin_member_router)
app.include_router(detection_log_router)
app.include_router(stt_router)

# 네비게이션 서브앱 마운트
app.mount("/navigation", navigation_app)


@app.get("/")
async def root():
    return {
        "service": "Minchodan GPU Inference Server",
        "status": "running",
        "health": "/health",
        "docs": "/docs",
        "websocket": "/ws/detect",
    }


@app.get("/health")
async def health_check():
    """
    서버 및 Redis 상태를 점검하는 헬스체크 API.
    """
    consumer = get_default_consumer()
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "runtime": {
            "detector_type": os.getenv("DETECTOR_TYPE", "mock"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "chroma_collection": os.getenv("CHROMA_COLLECTION", "safety_guidelines"),
            "detection_consumer": consumer.get_runtime_status(),
        },
    }
