"""
Fallback Node.
모든 시나리오 및 LLM 생성이 최종 실패했을 때 도달하는 최후의 안전망입니다.
가이드라인을 준수하는 고정 정지 메시지를 즉시 반환합니다.
"""

import contextlib
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

import asyncio

from server.mcp.slack_notifier import slack_notifier

FALLBACK_MESSAGE = "전방 주의, 천천히 멈추세요"

_background_tasks = set()


async def fallback_node(state: dict) -> dict:
    """
    LangGraph 폴백 노드 진입점.
    최후의 안전 안내 문자열을 주입하여 전체 파이프라인의 중단을 예방합니다.
    """
    # L3 가드레일 최종 실패 상황으로 간주하여 슬랙 경보 비동기 전송
    event_id = state.get("event", {}).get("event_id", "unknown_event")
    risk_level = state.get("risk_level", "unknown_risk")
    error_msg = (
        f"[MCP WARNING] LangGraph L3 가드레일 최종 실패 (Fallback 작동)\n"
        f"- 이벤트 ID: {event_id}\n"
        f"- 위험도 수준: {risk_level}\n"
        f"- 출력 안내문: {FALLBACK_MESSAGE}"
    )
    # 아웃오브밴드 비동기 실행 (0ms 블로킹 지향)
    task = asyncio.create_task(slack_notifier.send_notification(error_msg))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "guidance_text": FALLBACK_MESSAGE,
        "direction": "정지",
        "used_static_fallback": True,
        "verified": True,
    }
