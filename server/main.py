# -*- coding: utf-8 -*-
"""
Minchodan FastAPI GPU 추론 및 관제 서버 메인 엔트리 포인트.
FastAPI 앱을 초기화하고, WebSocket 게이트웨이 라우터 및 실시간 MCP 관제 모니터링 라우터를 마운트합니다.
Lifespan 이벤트를 통해 비동기 MCPManager의 생명주기를 자동으로 제어합니다.
"""

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Ensure server path is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from server.mcp.manager import mcp_manager
from server.api.monitor import router as monitor_router

logger = logging.getLogger(__name__)

# Load environment configuration (guide 3.4)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 어플리케이션의 시작 및 종료 시점에 실행되는 비동기 라이프사이클 이벤트.
    """
    logger.info("Minchodan API Server 시작 중...")
    
    # 1. MCP 통합 관리용 Redis Stream Consumer 태스크 시작
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    await mcp_manager.start_consumer(redis_url=redis_url)
    
    yield
    
    logger.info("Minchodan API Server 종료 중...")
    # 2. Redis Stream Consumer 및 리소스 정리
    await mcp_manager.stop_consumer()


# FastAPI App 인스턴스 생성
app = FastAPI(
    title="Minchodan GPU Inference Server",
    description="시각장애인 보행 보조 스마트 가이드독 AI 플랫폼 GPU 추론 및 관제 API 서버",
    version="v1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가 (추후 프론트엔드 연동 지원용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모니터링 라우터 마운트
app.include_router(monitor_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """
    서버 및 Redis 상태를 점검하는 헬스체크 API.
    """
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time()
    }
