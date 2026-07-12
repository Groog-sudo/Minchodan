import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.shared.labels import BOLLARD, CAUTION, ROADWAY, SCOOTER

load_dotenv()


# TH HARD CODE AREA:
# 현재는 RAG 실데이터 전면 정리 전 단계라서 실제 탐지 taxonomy에 맞는 최소 문구만 우선 고정합니다.
# 발표/면접 포인트: 모델 내부 라벨은 scooter로 통합하되, 사용자 발화는 한국 보행 맥락에 맞춰
# "전동 킥보드 또는 스쿠터"로 풀어 말합니다. 내부 taxonomy와 사용자 안내 문구를 분리한 설계입니다.
FALLBACK_RULES = {
    SCOOTER: "전방에 전동 킥보드 또는 스쿠터가 있습니다. 좌우로 비껴 천천히 지나가세요.",
    BOLLARD: "전방에 볼라드가 있습니다. 충돌하지 않도록 옆으로 돌아가세요.",
    CAUTION: "전방 바닥 위험 구간입니다. 발끝을 확인하며 천천히 이동하세요.",
    ROADWAY: "차도 방향으로 치우쳤습니다. 보도 안쪽으로 이동하세요.",
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

    res_scooter = get_fallback_guidance(SCOOTER)
    print(f"[{SCOOTER}] 가이드: {res_scooter}")

    res_bollard = get_fallback_guidance(BOLLARD)
    print(f"[{BOLLARD}] 가이드: {res_bollard}")

    res_unknown = get_fallback_guidance("unknown_obstacle")
    print(f"[unknown_obstacle] 가이드: {res_unknown}")
