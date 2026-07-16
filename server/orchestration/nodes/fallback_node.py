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

    detected_classes = state.get("detected_classes", [])
    clock_direction = state.get("clock_direction", "")

    # [2026-07-14] 장애물이 탐지되었을 때는 정적 정지 명령 대신 동적 설명+방향 멘트로 폴백
    if detected_classes:
        primary_obj = detected_classes[0]
        korean_names = {
            "car": "차량",
            "bus": "버스",
            "truck": "트럭",
            "motorcycle": "오토바이",
            "scooter": "킥보드",
            "bicycle": "자전거",
            "person": "보행자",
            "bollard": "볼라드",
            "pole": "기둥",
            "bench": "벤치",
            "chair": "의자",
            "carrier": "캐리어",
            "dog": "개",
            "cat": "고양이",
            "stroller": "유모차",
            "wheelchair": "휠체어",
            "barricade": "바리케이트",
            "fire_hydrant": "소화전",
            "kiosk": "키오스크",
            "movable_signage": "이동식 표지판",
            "parking_meter": "주차요금기",
            "potted_plant": "화분",
            "power_controller": "배전반",
            "table": "테이블",
            "traffic_light": "신호등",
            "traffic_light_controller": "제어기",
            "traffic_sign": "표지판",
            "tree_trunk": "나무",
            "stop": "정지선",
        }
        kor_name = korean_names.get(primary_obj, primary_obj)
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
