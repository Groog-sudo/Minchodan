import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import Detection, ReflexAlert
from server.detection.direction import estimate_direction

HIGH_RISK_CLASSES = {"car", "truck", "bus", "motorcycle"}
PROXIMITY_THRESHOLD = 0.15


def reflex_gate(
    detection: Detection,
    frame_height: float,
    frame_width: float,
) -> ReflexAlert | None:
    # =========================================================================
    # 👨‍💻 담당자 직접 코딩 영역 시작 (45% 비중) 👨‍💻
    # 1. detection.class_name 이 HIGH_RISK_CLASSES 에 없으면 None을 반환(return)하세요.
    # 2. 바운딩 박스(detection.bbox)의 하단 Y좌표(y + h)를 계산하여 bottom_y 에 넣으세요.
    # 3. bottom_y 가 프레임 하단 15%(즉, frame_height * (1 - PROXIMITY_THRESHOLD)) 보다
    #    위에 있으면(작거나 같으면) 안전한 것으로 간주하여 None을 반환하세요.
    # 4. 여기까지 통과했다면 위험 상황입니다! 
    #    estimate_direction(detection.bbox, frame_width, distance_class="near") 를 호출해 방향을 구하세요.
    # 5. f"high_{direction}" 문자열을 alert_id 로 만드세요.
    # 6. ReflexAlert 객체를 생성하여 반환하세요.
    #    - event_id: "" (임시 빈문자열)
    #    - alert_id: 위에서 만든 alert_id
    #    - direction: 위에서 구한 direction
    #    - clip: f"reflex_clips/{alert_id}.mp3"
    #    - haptic: True
    #    - ts: 0.0
    # =========================================================================
    
    return None

    # =========================================================================
    # 👨‍💻 담당자 직접 코딩 영역 끝 👨‍💻
    # =========================================================================
