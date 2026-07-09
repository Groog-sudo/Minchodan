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

from server.api.admin_router import router as admin_router
from server.api.config import settings
from server.api.monitor import router as monitor_router
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

    yield

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모니터링 라우터 마운트
app.include_router(monitor_router, prefix="/api/v1")

# WebSocket 게이트웨이 라우터 마운트
app.include_router(ws_router, prefix="")

# 사용자 및 관리자 API 라우터 마운트
app.include_router(user_router)
app.include_router(admin_router)

# 네비게이션 서브앱 마운트
app.mount("/navigation", navigation_app)


@app.get("/health")
async def health_check():
    """
    서버 및 Redis 상태를 점검하는 헬스체크 API.
    """
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}
