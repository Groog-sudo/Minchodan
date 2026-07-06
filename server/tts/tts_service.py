import asyncio
import json
import logging
import os
import subprocess  # nosec B404
import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

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
# - 실제 구현체(PiperTTSService)는 본 파일에 정의
# - 추상화를 통해 나중에 다른 TTS 엔진으로 교체 가능 (핫스왑 대비)
# ============================================================


class TTSService(ABC):
    """
    음성 합성 기능을 추상화한 기본 클래스.
    실제 어떤 방식으로 음성을 만들든 상관없이 동일한 형태로 사용할 수 있게 한다.
    인지 경로 실시간 TTS 전용 (반사 경로는 사전합성 클립 사용).
    """

    @abstractmethod
    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
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


class NullTTSService(TTSService):
    """외부 TTS 구현이 없을 때 사용하는 안전한 폴백 서비스."""

    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
        logger.warning("[TTS] 사용 가능한 TTS 엔진이 없어 합성을 건너뜁니다.")
        return None


class PiperTTSService(TTSService):
    """Piper ONNX 모델 기반 한국어 TTS 서비스."""

    def __init__(self) -> None:
        project_root = Path(root_dir)
        self.model_path = Path(
            os.getenv(
                "PIPER_MODEL_PATH",
                str(project_root / "server" / "models" / "piper" / "piper-kss-korean.onnx"),
            )
        )
        self.config_path = Path(
            os.getenv(
                "PIPER_CONFIG_PATH",
                str(project_root / "server" / "models" / "piper" / "piper-kss-korean.onnx.json"),
            )
        )
        self.binary_path = os.getenv("PIPER_BINARY_PATH", "piper").strip()
        self.length_scale_min = float(os.getenv("PIPER_LENGTH_SCALE_MIN", "0.5"))
        self.length_scale_max = float(os.getenv("PIPER_LENGTH_SCALE_MAX", "2.0"))
        self._compat_config_path: Path | None = None

    def _build_compat_config(self) -> Path:
        """pygoruut 표기를 piper 런타임 호환 포맷으로 보정한다."""
        if self._compat_config_path and self._compat_config_path.exists():
            return self._compat_config_path

        if not self.config_path.exists():
            raise FileNotFoundError(f"Piper 설정 파일이 없습니다: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8-sig") as fp:
            config_data = json.load(fp)

        if config_data.get("phoneme_type") == "pygoruut":
            config_data["phoneme_type"] = "espeak"

        compat_path = self.config_path.with_name(f"{self.model_path.stem}.runtime.compat.json")
        with compat_path.open("w", encoding="utf-8") as fp:
            json.dump(config_data, fp, ensure_ascii=False)

        self._compat_config_path = compat_path
        return compat_path

    def _resolve_binary(self) -> str:
        if Path(self.binary_path).exists():
            return self.binary_path
        return self.binary_path

    def _run_piper_sync(self, text: str, length_scale: float, compat_config: Path) -> bytes | None:
        """블로킹 Piper 프로세스 실행을 동기 함수로 분리한다."""
        binary = self._resolve_binary()
        output_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                output_path = Path(temp_wav.name)

            command = [
                binary,
                "--model",
                str(self.model_path),
                "--config",
                str(compat_config),
                "--output_file",
                str(output_path),
                "--length_scale",
                str(length_scale),
            ]

            result = subprocess.run(  # nosec B603 # noqa: S603
                command,
                input=text,
                text=True,
                capture_output=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    f"[PiperTTS] 합성 실패: code={result.returncode}, stderr={result.stderr.strip()}"
                )
                return None

            if not output_path.exists() or output_path.stat().st_size == 0:
                logger.error("[PiperTTS] 출력 WAV 파일이 비어 있습니다.")
                return None

            return output_path.read_bytes()
        finally:
            if output_path is not None and output_path.exists():
                output_path.unlink(missing_ok=True)

    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
        if not text or not text.strip():
            logger.warning("[PiperTTS] 빈 텍스트는 합성하지 않습니다.")
            return None

        if not self.model_path.exists():
            logger.error(f"[PiperTTS] 모델 파일이 없습니다: {self.model_path}")
            return None

        try:
            compat_config = self._build_compat_config()
            length_scale = max(self.length_scale_min, min(self.length_scale_max, speed))

            # asyncio 이벤트 루프 블로킹 방지를 위해 동기 실행을 스레드로 위임한다.
            return await asyncio.to_thread(
                self._run_piper_sync,
                text,
                length_scale,
                compat_config,
            )
        except Exception as e:
            logger.error(f"[PiperTTS] 합성 중 오류 발생: {e}")
            return None


# ============================================================
# [파트 3] get_tts_service() 팩토리 함수
# - 환경 변수에 따라 어떤 TTS 구현체를 사용할지 결정
# - 현재 지원: piper (기본)
# - 클라이언트(react-native-tts) 사용 시에도 이 팩토리는 유지될 수 있음
#   (단, 이 경우 실제 audio bytes 생성은 클라이언트가 담당)
# ============================================================


def get_tts_service() -> TTSService:
    """
    현재 설정에 맞는 음성 합성 서비스 객체를 만들어서 돌려준다.
    환경 변수 TTS_ENGINE (piper, 기본 piper)에 따라 결정.
    docs/environment_variables.md, pipeline_stage_design.md, architecture.md 준수.
    """

    # ------------------------------------------------------------
    # [변수] engine : 사용할 TTS 엔진 종류 결정
    # - os.getenv로 환경 변수 읽기 (기본값 "piper")
    # - .lower().strip()으로 대소문자/공백 정규화
    # ------------------------------------------------------------
    engine = os.getenv("TTS_ENGINE", "piper").lower().strip()

    if engine not in {"", "default", "piper"}:
        logger.warning(f"[TTS] 지원하지 않는 TTS_ENGINE='{engine}'. 기본값(piper) 사용.")

    try:
        return PiperTTSService()
    except Exception as e:
        logger.error(f"[TTS] PiperTTSService 초기화 실패: {e}")
        return NullTTSService()


def extract_llm_text(llm_output: dict | str | None) -> str:
    """오케스트레이션 LLM 결과에서 TTS 입력 문장을 추출한다."""
    if isinstance(llm_output, str):
        return llm_output.strip()

    if isinstance(llm_output, dict):
        for key in ("guidance_text", "answer", "text", "content"):
            value = llm_output.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""
