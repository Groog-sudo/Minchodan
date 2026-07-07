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


# =========================================================================
# 👨‍💻 HARD CODE 영역 시작 (위험도 및 한글 텍스트 매핑 테이블) 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 29종(AI Hub) 도심 보행 데이터 클래스별로 어떻게 위험도(High/Medium/Low)와 음성 안내 텍스트를 분류했나요?
# 답변: 1. 단말기(TTS)에서 재생될 한글 명칭은 직관적이고 짧게(예: '전력제어기' -> '제어기') 매핑하여 지연을 줄였습니다.
#       2. 시각장애인 보행에 직접적인 충돌/걸림돌 위험이 큰 객체(차량, 자전거, 킥보드, 볼라드, 바리케이드 등)를 DANGER_CLASSES로 묶어 거리에 따라 즉각적인 Reflex 발동이 가능하도록 설계했습니다.
# 💡 [추가 면접 꿀팁]
# 질문: 왜 고양이나 강아지 같은 동물은 DANGER_CLASSES에 넣지 않았나요?
# 답변: 동물은 스스로 사람을 피하는 동적 객체이고 물리적 충돌로 인한 중상 위험도가 낮기 때문에, 잦은 경보로 인한 사용자의 피로도를 낮추고자 일반 장애물(인지 경로)로 분류했습니다.
# =========================================================================

# 담당자님, 여기에 AI Hub 29종 클래스에 맞추어 아래 3개의 딕셔너리를 직접 채워주세요!
# CLASS_NAMES = ["barricade", "bench", "bicycle", "bollard", "bus", "car", "carrier", "cat", "chair", "dog", "fire_hydrant", "kiosk", "motorcycle", "movable_signage", "parking_meter", "person", "pole", "potted_plant", "power_controller", "scooter", "stop", "stroller", "table", "traffic_light", "traffic_light_controller", "traffic_sign", "tree_trunk", "truck", "wheelchair"]

CLASS_TO_HINT_ID: dict[str, MessageHintId] = {
    # 예: "stop": "STOP"
    "stop": "STOP",         # 정지 표지판은 즉각 정지 명령
    "barricade": "STOP",    # 바리케이드는 집입 불가이므로 정지 명령
    "bollard": "CURB"       # 볼라드는 보통 보도블록 끝(연석)에 있으므로 연석으로 취급가능 (선택사항)
}

DANGER_CLASSES = {
    # 예: "car", "motorcycle", "scooter", "bollard", "barricade" 등 위험 객체 문자열
    "car" , "truck" , "bus",                # 대형 / 고속 차량류
    "motorcycle", "scooter", "bicycle",     # 갑자기 튀어나오는 이륜차류
    "bollard", "pole",                      # 정강이나 머리를 부딪치기 쉬운 기동류
    "barricade", "movable_signage"          # 길을 갑자기 막고 있 구조물
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
    # 예: "scooter": "킥보드", "car": "차량" 등 29종의 한글 이름
    "barricade": "바리케이드",
    "bench": "벤치",
    "bicycle": "자전거",
    "bollard": "볼라드",
    "bus": "버스",
    "car": "차량",
    "carrier": "운반구",
    "cat": "고양이",
    "chair": "의자",
    "dog": "개",
    "fire_hydrant": "소화전",
    "kiosk": "키오스크",
    "motorcycle": "오토바이",
    "movable_signage": "이동형 표지판",
    "parking_meter": "주차 미터기",
    "person": "사람",
    "pole": "기둥",
    "potted_plant": "화분",
    "power_controller": "전력 제어기",
    "scooter": "전동 킥보드",
    "stop": "정지 표지판",
    "stroller": "유모차",
    "table": "테이블",
    "traffic_light": "신호등",
    "traffic_light_controller": "신호등 제어기",
    "traffic_sign": "교통 표지판",
    "tree_trunk": "나무 줄기",
    "truck": "트럭",
    "wheelchair": "휠체어",
}

# =========================================================================
# 👨‍💻 HARD CODE 영역 끝
# =========================================================================


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
    text = "정지하세요" if hint_id == "STOP" else build_message_text("obstacle", direction, hint_id)
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
