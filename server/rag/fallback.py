import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.shared.labels import (
    BOLLARD,
    BRAILLE_DAMAGED,
    CROSSWALK,
    GRATING,
    KICKBOARD,
    MANHOLE,
    STAIRS,
)

load_dotenv()


# [DUMMY DATA] 설명: MVP 검증용 룰 기반 수칙 딕셔너리 / 주의: 키 이름은 shared/labels.py에서 import한 상수를 사용해야 함
FALLBACK_RULES = {
    KICKBOARD: "전방에 방치된 전동 킥보드가 있습니다. 부딪히지 않도록 서행하며 우회하거나 멈추어 안전거리를 확보하세요.",
    BOLLARD: "인도 중간에 볼라드가 설치되어 있습니다. 무릎 충돌이 우려되니 보폭을 좁히고 장애물의 옆으로 돌아가세요.",
    BRAILLE_DAMAGED: "점자블록이 파손되거나 끊어진 구간입니다. 짚고 가시는 지팡이 신호에 의지해 천천히 발을 옮기세요.",
    STAIRS: "전방에 계단 진입로가 있습니다. 낙상에 주의하며 난간 혹은 발끝의 높낮이를 확인하고 한 계단씩 진입하세요.",
    CROSSWALK: "전방에 횡단보도가 보입니다. 횡단 차도와 인접해 있으니 보행 신호에 유의하며 일시 정지 후 안전을 확인하세요.",
    MANHOLE: "노면에 맨홀 뚜껑이 있으니 미끄러짐이나 발빠짐에 주의하여 조심해서 지나가세요.",
    GRATING: "배수구 철제 그레이팅 덮개가 있습니다. 지팡이가 틈새에 끼일 수 있으니 주의하여 우회 보행하세요.",
}


def get_fallback_guidance(class_name: str) -> str:
    """
    RAG 검색이 실패하거나 데이터가 적중하지 않았을 경우, 탐지 클래스 라벨(SSOT)에 맞추어
    사전에 준비된 하드코딩 룰 기반 안전 가이드를 반환합니다.

    Args:
        class_name: 탐지 사물 명칭 (labels.py 기준)

    Returns:
        상황별 지정된 즉시 대처 수칙 가이드 문자열 (없을 시 전방 주의 문구 반환)
    """
    if not class_name:
        return "전방에 장애물이 있으니 걸음을 멈추거나 서행하며 주의하세요."

    class_name = class_name.lower().strip()

    # 딕셔너리 안전 접근 (비협상 가드)
    guidance = FALLBACK_RULES.get(class_name)
    if not guidance:
        # TODO(human-decision): 새로운 YOLO 탐지 사물 추가 시 FALLBACK_RULES 매핑 필요
        guidance = f"전방에 {class_name}이(가) 있습니다. 안전 사고에 유의하여 서행하십시오."

    return guidance


if __name__ == "__main__":
    print("fallback.py 스모크 테스트 실행")

    # 1. 킥보드 룰 검증
    res_kick = get_fallback_guidance(KICKBOARD)
    print(f"[{KICKBOARD}] 가이드: {res_kick}")

    # 2. 볼라드 룰 검증
    res_boll = get_fallback_guidance(BOLLARD)
    print(f"[{BOLLARD}] 가이드: {res_boll}")

    # 3. 존재하지 않는 라벨 폴백 검증
    res_unknown = get_fallback_guidance("unknown_obstacle")
    print(f"[unknown_obstacle] 가이드: {res_unknown}")
