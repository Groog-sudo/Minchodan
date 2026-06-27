# -*- coding: utf-8 -*-
"""
GPUMonitorMCP 및 LLMClientFactory 핫스왑 기능 테스트 파일.
"""

import os
import sys
import asyncio
import pytest

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Ensure server path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.mcp.gpu_monitor import GPUMonitorMCP
from server.orchestration.llm_client_factory import LLMClientFactory


@pytest.mark.asyncio
async def test_gpu_monitor_mock_fallback():
    """
    GPU 모니터의 가상/실제 상태 진단 및 Fallback 트리거 여부를 검증합니다.
    """
    monitor = GPUMonitorMCP(memory_threshold_mb=4000.0, usage_threshold_pct=80.0)
    status = await monitor.get_gpu_status()
    
    assert "gpu_usage_pct" in status
    assert "should_fallback" in status
    
    # 환경변수 모의 설정 후 트리거 확인
    os.environ["MOCK_GPU_USAGE_PCT"] = "90.0"
    trigger = await monitor.check_hotswap_trigger()
    assert trigger is True
    
    os.environ["MOCK_GPU_USAGE_PCT"] = "20.0"
    os.environ["MOCK_GPU_MEM_USED_MB"] = "1000.0"
    trigger = await monitor.check_hotswap_trigger()
    assert trigger is False


@pytest.mark.asyncio
async def test_client_factory_hotswap():
    """
    LLMClientFactory가 GPU 모니터 루프를 통해 자동으로 provider를 핫스왑하는지 테스트합니다.
    """
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OPENAI_API_KEY"] = "mock_key" # OpenAI 초기화 방어용
    
    # 감시 루프 시작 (빠른 확인을 위해 간격 0.1초 설정)
    LLMClientFactory.start_gpu_monitor(interval_seconds=0.1)
    
    # 초기 상태 검증
    client = LLMClientFactory.get_client()
    assert LLMClientFactory._current_provider == "ollama"
    
    # 강제 부하 상황 연출
    os.environ["MOCK_GPU_USAGE_PCT"] = "95.0"
    
    # 핫스왑 감시 루프가 감지할 수 있도록 짧은 대기
    await asyncio.sleep(0.3)
    
    assert LLMClientFactory._current_provider == "openai"
    
    # 부하 해제 상황 연출
    os.environ["MOCK_GPU_USAGE_PCT"] = "10.0"
    await asyncio.sleep(0.3)
    
    assert LLMClientFactory._current_provider == "ollama"
    
    # 백그라운드 태스크 정리
    if LLMClientFactory._monitor_task and not LLMClientFactory._monitor_task.done():
        LLMClientFactory._monitor_task.cancel()
