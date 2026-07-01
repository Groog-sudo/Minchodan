import logging
import os
import sys
import json
from abc import ABC, abstractmethod
from typing import Optional, TypedDict, Annotated, List

from dotenv import load_dotenv

# ============================================================
# [모듈 헤더]
# - UTF-8 인코딩 설정 (한글 로그/출력 깨짐 방지)
# - 프로젝트 표준 패턴 (course_codebase_guide.md 3.1)
# ============================================================
# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# ============================================================
# [파트 1] 경로 계산 및 환경 변수 로드
# - __file__ 기반으로 실행 위치에 상관없이 동작하도록 설계
# - .env 파일에서 TTS_ENGINE 등 설정을 로드
# - course_codebase_guide.md 3.3, 3.4 패턴 준수
# ============================================================

# 현재 파일의 디렉토리 절대경로 계산
current_dir = os.path.dirname(os.path.abspath(__file__))

# 프로젝트 루트 디렉토리 계산 (tts/ → server/ → root/)
root_dir = os.path.dirname(os.path.dirname(current_dir))

# .env 파일 전체 경로 조합
env_path = os.path.join(root_dir, ".env")

# .env 파일이 존재할 경우 로드 (없으면 기본값 사용)
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)


# ============================================================
# [파트 2] TTSService 추상 클래스
# - 인지 경로(Cognitive Path)에서만 사용하는 실시간 TTS 인터페이스
# - 반사 경로(Reflex Path)는 절대 이 클래스를 사용하지 않음
# - 실제 구현체(KokoroTTS, CoquiTTS)는 별도 파일에 존재
# - 추상화를 통해 나중에 다른 TTS 엔진으로 교체 가능 (핫스왑 대비)
# ============================================================

class TTSService(ABC):
    """
    음성 합성 기능을 추상화한 기본 클래스.
    실제 어떤 방식으로 음성을 만들든 상관없이 동일한 형태로 사용할 수 있게 한다.
    인지 경로 실시간 TTS 전용 (반사 경로는 사전합성 클립 사용).
    """

    @abstractmethod
    async def generate(self, text: str, voice: str, speed: float = 1.0) -> Optional[bytes]:
        """
        텍스트를 받아서 음성 데이터로 만들어 반환한다.

        [파라미터 설명]
        - text   : 합성할 한국어 문장 (L3에서 생성된 guidance_text)
        - voice  : 음성 종류 (예: "ko" - 한국어)
        - speed  : 말하는 속도 (기본 1.0)

        [반환값]
        - bytes  : 음성 데이터 (MP3/WAV 권장)
        - None   : 합성 실패 시 반환 (호출 측에서 처리)
        """
        pass


# ============================================================
# [파트 3] get_tts_service() 팩토리 함수
# - 환경 변수에 따라 어떤 TTS 구현체를 사용할지 결정
# - 현재 지원: kokoro (기본), coqui
# - 클라이언트(react-native-tts) 사용 시에도 이 팩토리는 유지될 수 있음
#   (단, 이 경우 실제 audio bytes 생성은 클라이언트가 담당)
# ============================================================

def get_tts_service() -> TTSService:
    """
    현재 설정에 맞는 음성 합성 서비스 객체를 만들어서 돌려준다.
    환경 변수 TTS_ENGINE (kokoro | coqui, 기본 kokoro)에 따라 결정.
    docs/environment_variables.md, pipeline_stage_design.md, architecture.md 준수.
    """

    # ------------------------------------------------------------
    # [변수] engine : 사용할 TTS 엔진 종류 결정
    # - os.getenv로 환경 변수 읽기 (기본값 "kokoro")
    # - .lower().strip()으로 대소문자/공백 정규화
    # ------------------------------------------------------------
    engine = os.getenv("TTS_ENGINE", "kokoro").lower().strip()

    # ------------------------------------------------------------
    # [분기 1] engine == "kokoro" 인 경우
    # - Kokoro-82M 모델 사용 (서버 측 실시간 TTS)
    # - .kokoro_tts 모듈에서 KokoroTTS 클래스 임포트
    # - 실패 시 예외를 그대로 전파 (상위에서 처리)
    # ------------------------------------------------------------
    if engine == "kokoro":
        try:
            from .kokoro_tts import KokoroTTS
            return KokoroTTS()
        except Exception as e:
            logger.error(f"[TTS] KokoroTTS 로드 실패: {e}")
            raise

    # ------------------------------------------------------------
    # [분기 2] engine == "coqui" 인 경우
    # - Coqui TTS 모델 사용
    # - .coqui_tts 모듈에서 CoquiTTS 클래스 임포트
    # ------------------------------------------------------------
    elif engine == "coqui":
        try:
            from .coqui_tts import CoquiTTS
            return CoquiTTS()
        except Exception as e:
            logger.error(f"[TTS] CoquiTTS 로드 실패: {e}")
            raise

    # ------------------------------------------------------------
    # [분기 3] 지원하지 않는 엔진 값인 경우 (fallback)
    # - 경고 로그 출력 후 기본값(kokoro)으로 시도
    # - 그래도 실패하면 예외 발생
    # ------------------------------------------------------------
    else:
        logger.warning(
            f"[TTS] 지원하지 않는 TTS_ENGINE='{engine}'. 기본값(kokoro) 사용."
        )
        try:
            from .kokoro_tts import KokoroTTS
            return KokoroTTS()
        except Exception as e:
            logger.error(f"[TTS] 기본 KokoroTTS 로드 실패: {e}")
            raise
