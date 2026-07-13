import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# STT 설정 파일
# ============================================================
# [바이브 코딩 부분]
# - 운영 STT에서 사용하는 설정값과 기본 정책 상수를 보관한다.
# - 실행 시 필요한 검증은 service/bridge 계층의 런타임 검증 모듈이 담당한다.
#
# [하드 코딩 부분]
# - 실제 Whisper 모델 정책, 디바이스 정책, 추론 옵션은 운영 환경 기준으로 직접 확정한다.
# - 현재 상수값은 SttService/get_model, _transcribe_production, SttToLlmBridge에서 직접 사용된다.


# ============================================================
# [하드 코딩 부분] 직접 확정 영역
# ============================================================
# 중요: 아래 값은 STT 실행 정책 자체이므로 담당자가 직접 확정한다.
# 직접 확정해야 하는 이유:
# 1) 발표/면접에서 "왜 이 정책인가"를 설명해야 하기 때문
# 2) 운영 서버 자원(CPU/GPU, RAM)과 지연 목표를 현장 기준으로 맞춰야 하기 때문
# 3) stt_runtime.validate_* 검증을 통과해야 서비스가 실행되기 때문
#
# 작성 조건(필수):
# - MODEL_NAME_MAP:
#   - key: 프론트에서 요청하는 모델명(예: faster-whisper-base)
#   - value: faster-whisper 내부 모델명(예: base)
#   - 최소 1개 이상 매핑 필요
#   - key 형식 권장: "faster-whisper-<size>" (예: tiny/base/small/medium)
#   - value 형식 권장: faster-whisper 공식 모델 별칭만 사용
# - DEFAULT_REQUEST_MODEL:
#   - MODEL_NAME_MAP key 중 하나여야 함
#   - 미매핑 요청이 들어오면 이 값으로 폴백
#   - 공백 금지, 대소문자 일치 필수
# - TRANSCRIBE_LANGUAGE:
#   - "ko" 또는 운영 정책에 맞는 언어 코드
#   - 자동 감지 미사용이면 고정 언어를 명시 (예: ko)
# - TRANSCRIBE_BEAM_SIZE:
#   - 1 이상의 정수
#   - 권장 범위: 1~5 (값이 커질수록 품질↑/지연↑)
# - TRANSCRIBE_VAD_FILTER:
#   - bool 값
#   - True 권장: 무음/배경잡음 구간 제거
# - WHISPER_DEVICE:
#   - "cpu" 또는 "cuda"
#   - Windows 개발 PC에서 GPU 미사용 시 "cpu" 고정
# - WHISPER_COMPUTE_TYPE:
#   - 예: "int8", "float16"
#   - cpu 사용 시 권장: int8
#   - cuda 사용 시 권장: float16 (환경 따라 int8_float16 고려)
# - STT_ORCH_RISK_HINT:
#   - STT 텍스트를 기존 오케스트레이션에 전달할 때 사용할 기본 위험도 힌트
#   - 허용값: low 또는 mid (high 금지: 반사 경로 비협상 원칙)
# - STT_ORCH_CLASS_NAME:
#   - STT 입력을 나타내는 가상 클래스명 (예: voice_command)
#   - 공백 없는 snake_case 권장
#   - 분석/로그 집계를 위해 일관된 단일 값 사용 권장
# - TRANSCRIBE_HOTWORDS:
#   - faster-whisper 1.2.1이 지원하는 도메인 어휘 바이어싱 문자열(공백 구분)
#   - "길댕아" 등 사전에 없는 신조어 웨이크워드 오인식 완화 목적
#   - 담당자가 직접 확정하는 값이다 - 아래는 stt_to_llm_bridge.py에 이미 정의된
#     실제 명령어 어휘(GILDAENG_ROOT, *_INTENT_KEYWORDS, POI_CATEGORY_KEYWORDS)에서
#     그대로 가져온 초안이며, 실사용 명령 패턴에 맞춰 조정해야 한다(2026-07-11 opus 제안,
#     실측 검증 전).

MODEL_NAME_MAP: dict[str, str] = {
    "faster-whisper-medium": "medium",
    "faster-whisper-small": "small",
    # WebSocket 경로에서 faster-whisper 접두사 없이 내부 별칭이 전달되는 경우를 허용한다.
    "medium": "medium",
    "small": "small",
}

# 2026-07-11 기본 모델 medium -> small 전환(실측 근거): macOS Docker CPU 폴백
# 환경에서 medium은 2초 발화 전사에 2.3초, 콜드스타트 로딩에 8~10초가 걸려
# STT 왕복 체감 지연의 주 병목이었다. 명령어 위주 짧은 발화 + hotwords 바이어싱
# 조합에서는 small로도 인식 품질이 유지되는지 실기기 검증 후, 회귀가 확인되면
# 이 값만 medium으로 되돌린다(GPU 서버 배포 시에도 재평가).
DEFAULT_REQUEST_MODEL = "faster-whisper-small"
TRANSCRIBE_LANGUAGE = "ko"
TRANSCRIBE_BEAM_SIZE = 3
TRANSCRIBE_VAD_FILTER = True
TRANSCRIBE_HOTWORDS = (
    "길댕이 길댕아 길찾아줘 네비게이션 길안내 시작 물어볼게 질문할게 "
    "가까운 근처 주변 지하철역 버스정류장 편의점 화장실 약국 병원 카페 은행 주차장"
)
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
STT_ORCH_RISK_HINT = "low"
STT_ORCH_CLASS_NAME = "speech_to_text"


def load_optional_stt_env() -> None:
    """
    [바이브 코딩 부분]
    server/stt는 테스트 모드를 포함하지 않는다.
    운영 환경에서만 필요한 값을 외부(.env 등)에서 주입받도록 확장 포인트를 둔다.
    """
    _ = os.getenv("STT_CONFIG_SOURCE", "")
