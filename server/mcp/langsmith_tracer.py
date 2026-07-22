"""
LangSmith Trace MCP 모듈.
LANGCHAIN_API_KEY 및 LANGCHAIN_TRACING_V2 환경 변수 여부에 따라
LangGraph StateGraph의 노드 전이 및 실행 지연(Latency)을 시각적으로 추적할 수 있도록
LangSmith Trace 모니터링 세션을 비동기로 제어하고 에러 발생 시 가드레일 역할을 합니다.
"""

import contextlib
import logging
import os
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class LangSmithTracerMCP:
    """
    LangSmith 트레이싱 세션을 모니터링하고 제어하는 MCP 모듈.
    """

    def __init__(self):
        self.api_key = os.getenv("LANGCHAIN_API_KEY")
        self.tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "minchodan-orchestration")

    def is_available(self) -> bool:
        """
        LangSmith 연동 활성화 여부를 판단합니다.
        """
        return bool(self.api_key) and self.tracing_enabled

    def get_trace_config(self) -> dict:
        """
        현재 트레이서의 설정 상태를 반환합니다. (방어적 코딩 및 Mock 처리 지원)
        """
        if not self.is_available():
            return {
                "enabled": False,
                "project": self.project_name,
                "reason": "LANGCHAIN_API_KEY가 없거나 LANGCHAIN_TRACING_V2가 활성화되지 않았습니다.",
                "should_fallback": True,
            }

        return {
            "enabled": True,
            "project": self.project_name,
            "reason": "LangSmith 연동 활성화 완료",
            "should_fallback": False,
        }

    async def log_node_transition(self, from_node: str, to_node: str, latency_ms: float) -> bool:
        """
        LangGraph 노드 전이 로그를 시뮬레이션 및 로깅하여 지연을 모니터링합니다.
        """
        config = self.get_trace_config()
        payload = {
            "from_node": from_node,
            "to_node": to_node,
            "latency_ms": latency_ms,
            "project": self.project_name,
            "enabled": config["enabled"],
        }

        # 1. 로컬 모니터링 콘솔에 상태 전파 (Redis Streams 발행)
        from server.mcp.manager import mcp_manager

        await mcp_manager.publish_metric("langsmith_trace", payload)

        # 2. 실제 LangSmith 연결 상황 시뮬레이션 (API 키가 있을 때)
        if config["enabled"]:
            logger.info(
                f"[LANGSMITH TRACER] Node '{from_node}' -> '{to_node}' 전이 기록됨. "
                f"지연: {latency_ms:.1f}ms"
            )
            # 여기에 실제 langchain client SDK가 설치되어 있다면 log_run 등을 호출하는 커스텀 연동 추가 가능
            return True
        else:
            logger.debug(
                f"[LANGSMITH TRACER MOCK] Tracing disabled. Transition '{from_node}' -> '{to_node}' "
                f"({latency_ms:.1f}ms)"
            )
            return False


# 싱글톤 인스턴스 제공
langsmith_tracer = LangSmithTracerMCP()
