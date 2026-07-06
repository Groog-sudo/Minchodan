# -*- coding: utf-8 -*-
import sys
from typing import Literal, TypedDict

from server.detection.gates.reflex_gate import HIGH_RISK_CLASSES
from server.detection.schemas import Detection, ReflexAlert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


MessageHintId = Literal["OBSTACLE", "STAIR_DOWN", "ROAD", "RED_LIGHT", "CURB", "STOP"]
MessageHintType = Literal["REFLEX", "COGNITIVE"]
RiskLevel = Literal["high", "medium", "low"]


class MessageHint(TypedDict):
    id: MessageHintId
    type: MessageHintType
    text: str


CLASS_TO_HINT_ID: dict[str, MessageHintId] = {
    "stair": "STAIR_DOWN",
    "stairs": "STAIR_DOWN",
    "stair_down": "STAIR_DOWN",
    "road": "ROAD",
    "roadway": "ROAD",
    "red_light": "RED_LIGHT",
    "traffic_light_red": "RED_LIGHT",
    "curb": "CURB",
    "bollard": "CURB",
    "stop": "STOP",
    "stop_sign": "STOP",
}

DANGER_CLASSES = {
    "kickboard",
    "scooter",
    "bicycle",
    "motorcycle",
    "car",
    "truck",
    "bus",
    "bollard",
    "pole",
    "traffic_cone",
    "obstacle",
    "stairs",
    "stair",
    "construction",
    "movable_signage",
    "barricade",
}

DIRECTION_TEXT = {
    "left": "왼쪽",
    "front-left": "왼쪽 앞",
    "front": "정면",
    "center": "정면",
    "right": "오른쪽",
    "front-right": "오른쪽 앞",
    "stop": "정지",
    "unknown": "정면",
}

CLASS_TEXT = {
    "kickboard": "킥보드",
    "bicycle": "자전거",
    "motorcycle": "오토바이",
    "car": "차량",
    "truck": "트럭",
    "bus": "버스",
    "person": "보행자",
    "bollard": "볼라드",
    "pole": "기둥",
    "traffic_cone": "콘",
    "obstacle": "장애물",
    "stair": "계단",
    "stairs": "계단",
    "stair_down": "내려가는 계단",
    "road": "차도",
    "roadway": "차도",
    "red_light": "빨간불",
    "traffic_light_red": "빨간불",
    "curb": "연석",
    "stop": "정지",
    "stop_sign": "정지 표지",
}


def build_message_hint(
    detection: Detection,
    direction: str,
    distance: str,
    risk_level: str,
) -> MessageHint | None:
    """기존 Detection 위에 단말 TTS용 message_hint 계약을 얹는다."""
    hint_id = _hint_id_for_class(detection.class_name)
    hint_type: MessageHintType = _hint_type_for_risk(detection.class_name, risk_level)
    
    # Reflex Path 규칙: 측면이거나 멀리 있는 객체는 Reflex 침묵 (Cognitive 위임)
    if hint_type == "REFLEX":
        if distance == "far" or direction != "front":
            return None
            
        if distance == "near" and direction == "front":
            text = "정지, 전방 장애물"
            if hint_id == "STAIR_DOWN":
                text = "정지, 전방 계단"
            elif hint_id == "ROAD":
                text = "정지, 전방 차도"
            elif hint_id == "RED_LIGHT":
                text = "정지, 빨간불"
            elif hint_id == "CURB":
                text = "정지, 전방 연석"
            return {"id": "STOP", "type": "REFLEX", "text": text}
            
        if distance in ("near", "medium") and direction == "front":
            text = build_message_text(detection.class_name, direction, hint_id)
            return {"id": hint_id, "type": "REFLEX", "text": text}
            
        return None

    text = build_message_text(detection.class_name, direction, hint_id)
    return {"id": hint_id, "type": hint_type, "text": text}


def estimate_risk_level(class_name: str, direction: str, distance: str) -> RiskLevel:
    """데모용 문장 생성 전에 사용할 결정적 위험도 규칙."""
    normalized = class_name.strip().lower()
    
    # 측면 객체는 Reflex 발동을 막기 위해 위험도 하향
    if direction != "front":
        return "low"
        
    if distance == "near" and normalized in DANGER_CLASSES:
        return "high"
    if distance == "medium" and normalized in DANGER_CLASSES:
        return "medium"
    if normalized in HIGH_RISK_CLASSES:
        return "medium"
    return "low"


def build_reflex_message_hint(alert: ReflexAlert) -> MessageHint:
    """ReflexAlert를 단말 TTS용 message_hint로 변환한다."""
    hint_id = _hint_id_for_alert(alert)
    direction = alert.direction or "front"
    if hint_id == "STOP":
        text = "정지하세요"
    else:
        text = build_message_text("obstacle", direction, hint_id)
    return {"id": hint_id, "type": "REFLEX", "text": text}


def build_message_text(class_name: str, direction: str, hint_id: MessageHintId) -> str:
    direction_text = DIRECTION_TEXT.get(direction, "정면")
    if hint_id == "STAIR_DOWN":
        return f"{direction_text} 계단 주의"
    if hint_id == "ROAD":
        return f"{direction_text} 차도 주의"
    if hint_id == "RED_LIGHT":
        return "빨간불 정지"
    if hint_id == "CURB":
        return f"{direction_text} 연석 주의"
    if hint_id == "STOP":
        return "정지하세요"

    object_text = CLASS_TEXT.get(class_name, "장애물")
    return f"{direction_text} {object_text} 주의"


def _hint_id_for_class(class_name: str) -> MessageHintId:
    return CLASS_TO_HINT_ID.get(class_name, "OBSTACLE")


def _hint_type_for_risk(class_name: str, risk_level: str) -> MessageHintType:
    if risk_level == "high" or class_name in HIGH_RISK_CLASSES:
        return "REFLEX"
    return "COGNITIVE"


def _hint_id_for_alert(alert: ReflexAlert) -> MessageHintId:
    if alert.alert_id == "high_stop" or alert.direction == "stop":
        return "STOP"
    if "stair" in alert.alert_id:
        return "STAIR_DOWN"
    if "road" in alert.alert_id:
        return "ROAD"
    if "curb" in alert.alert_id:
        return "CURB"
    return "OBSTACLE"
