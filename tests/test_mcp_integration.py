"""
FastAPI SSE 모니터링 엔드포인트 통합 테스트 파일.
"""

import contextlib
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# Ensure server path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.api.monitor import monitor_stream
from server.mcp.manager import mcp_manager


@pytest.mark.asyncio
async def test_sse_generator_direct():
    """
    HTTP 스트림 대기 교착 상태를 예방하기 위해, monitor_stream 제네레이터 함수를
    직접 호출하여 이벤트 발행 및 SSE 메시지 규격을 검증합니다.
    """
    mock_request = MagicMock()

    async def mock_is_disconnected():
        return False

    mock_request.is_disconnected = mock_is_disconnected

    mock_gpu_status = AsyncMock(
        return_value={
            "gpu_usage_pct": 12.5,
            "memory_used_mb": 1024.0,
        }
    )

    with patch("server.api.monitor.GPUMonitorMCP") as mock_gpu_cls:
        mock_gpu_cls.return_value.get_gpu_status = mock_gpu_status

        response = await monitor_stream(mock_request)
        generator = response.body_iterator

        first_event = await generator.__anext__()
        assert first_event.startswith("data: ")
        conn_data = json.loads(first_event[6:].strip())
        assert conn_data["event_type"] == "connection_established"
        assert conn_data["status"] == "ok"

        second_event = await generator.__anext__()
        assert second_event.startswith("data: ")
        metrics_data = json.loads(second_event[6:].strip())
        assert metrics_data["event_type"] == "system_metrics"
        assert "gpu_usage_pct" in metrics_data["payload"]
        assert "current_provider" in metrics_data["payload"]

        test_payload = {
            "gpu_usage_pct": 88.8,
            "memory_used_mb": 2048,
            "current_provider": "ollama",
        }
        await mcp_manager.broadcast_event("gpu_status", test_payload)

        third_event = await generator.__anext__()
        assert third_event.startswith("data: ")
        event_data = json.loads(third_event[6:].strip())

        assert event_data["event_type"] == "gpu_status"
        assert event_data["payload"]["gpu_usage_pct"] == 88.8
        assert event_data["payload"]["current_provider"] == "ollama"
