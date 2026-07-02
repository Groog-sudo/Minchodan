import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
import os
import json
from typing import TypedDict, Annotated, List, Optional

import logging
from server.detection.schemas import ReflexAlert
from server.tts.suppressor import Alert_suppressor
import time

logger = logging.getLogger(__name__) # logger 객체 생성

# ============================================================
# 모듈 레벨 상수 (기본 틀)
# ============================================================
DEFAULT_TTL = 60


# ============================================================
# BASIC SKELETON: ReflexClipSender 기본 틀
# - 이 파일의 목적: 반사 경로에서 alert_id 기반 사전합성 클립을
#   WS로 고우선 전송하는 역할
# - 절대 real-time TTS 호출 금지 (반사 경로는 사전합성만)
# ============================================================

async def send_reflex_clip(
    device_id: str,
    alert_id: str,
    clip: str,
    direction: str,
    event_id: str = "",
    haptic: bool = True,
) -> bool:
    """
    반사 경로 사전합성 클립을 클라이언트로 고우선 전송한다.

    [호출 시점]
    - DetectionPipeline에서 ReflexAlert가 생성되면 호출됨
    - Surface Gate에서도 동일하게 사용 가능

    [주의]
    - 이 함수 내부에서는 절대 TTS 합성을 하지 말 것
    - 중복 전송 방지를 위해 suppressor를 반드시 사용
    """

    # ============================================================
    # BASIC SKELETON: 1단계 - 입력 검증 (기초 틀)
    # ============================================================
    if not device_id or not alert_id or not clip:
        logger.warning("[ReflexClipSender] 필수 파라미터 누락")
        return False

    # ============================================================
    # CORE: 2단계 - 중복 억제 체크 (핵심 로직 영역)
    # - 이미 최근에 보냈다면 전송하지 않음
    # - 사용자(당신)가 실제 구현할 핵심 부분
    # ============================================================
    # TODO: 사용자 구현 영역
    if await Alert_suppressor.should_supperss(device_id, alert_id):
        logger.info(f"[ReflexClipSender] 중복 억제 : {ReflexAlert}")
        return False

    # ============================================================
    # BASIC SKELETON: 3단계 - 전송 페이로드 조립 (기초 틀)
    # - api_specification.md 의 alert_reflex 형식과 일치해야 함
    # ============================================================
    payload = {
        "type": "alert_reflex",
        "event_id": event_id,
        "alert_id": alert_id,
        "direction": direction,
        "risk_level": "high",
        "clip": clip,
        "haptic": haptic,
        "ts": 0.0,   # 실제로는 time.time() 또는 alert 객체에서 가져옴 (기초 틀에서는 placeholder)
    }

    # ============================================================
    # CORE: 4단계 - 고우선 WS 전송 (핵심 로직 영역)
    # - 여기서 실제 WebSocket으로 device_id에게 전송
    # - 반사 경로는 인지 경로보다 우선순위가 높아야 함 (선점)
    # - 사용자(당신)가 WS 매니저/연결 객체를 이용해 구현할 부분
    # ============================================================
    # TODO: 사용자 구현 영역
    try:
        await _send_high_proiority(device_id, payload)
    except Exception as e:
        logger.info(f"[ReflexClipSender] 우선순위 : {e}")
        return False
    return True

    # ============================================================
    # CORE: 5단계 - 전송 완료 마킹 (핵심 로직 영역)
    # - 성공적으로 보냈으면 suppressor에 기록
    # - TTL 동안 같은 alert_id는 재전송 방지
    # ============================================================
    # TODO: 사용자 구현 영역
    # await Alert_suppressor.mark_as_sent(device_id, alert_id)

    # ============================================================
    # BASIC SKELETON: 반환 (기초 틀)
    # ============================================================
    return True


# ============================================================
# BASIC SKELETON: 내부 헬퍼 함수 영역 (필요시 확장)
# ============================================================
# async def _send_high_priority(device_id: str, payload: dict) -> None:
#     """실제 WS 고우선 전송 로직 (사용자가 구현)"""
#     # TODO: WS connection manager를 통해 device_id에게 payload 전송
#     # 예: await connection_manager.send_to_device(device_id, payload, priority="high")
#     pass


# ============================================================
# 사용 예시 (주석으로만 표시, 실제 호출은 detection_pipeline 등 상위에서)
# ============================================================
# from server.detection.schemas import ReflexAlert
#
# async def handle_reflex(device_id: str, alert: ReflexAlert):
#     success = await send_reflex_clip(
#         device_id=device_id,
#         alert_id=alert.alert_id,
#         clip=alert.clip,
#         direction=alert.direction,
#         event_id=alert.event_id,
#         haptic=alert.haptic,
#     )
#     return success
