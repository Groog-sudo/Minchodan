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

from server.detection.risk_rules import class_name_to_ko
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

    detected_classes = state.get("detected_classes", [])
    clock_direction = state.get("clock_direction", "")

    # [2026-07-14] 장애물이 탐지되었을 때는 정적 정지 명령 대신 동적 설명+방향 멘트로 폴백
    if detected_classes:
        primary_obj = detected_classes[0]
        kor_name = class_name_to_ko(primary_obj)
        dir_str = f"{clock_direction} 방향" if clock_direction else "전방"
        fallback_msg = f"{dir_str} {kor_name} 주의하세요"
    else:
        fallback_msg = FALLBACK_MESSAGE

    return {
        "guidance_text": fallback_msg,
        "direction": "우회" if clock_direction else "정지",
        "used_static_fallback": True,
        "verified": True,
    }
