from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
import tempfile
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from piper import PiperVoice
    from supertonic import TTS as SupertonicTTS
    from supertonic import Style as SupertonicStyle

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
    """Piper ONNX 모델 기반 한국어 TTS 서비스.

    [상주 프로세스화, 2026-07-09] 과거에는 호출마다 piper CLI 서브프로세스를 새로
    기동해 ONNX 모델을 매번 로드했다(실측 콜드스타트 약 1.6~1.9초). PiperVoice.load()를
    최초 1회만 수행해 세션을 인스턴스에 상주시키고, 이후 호출은 in-process
    session.run()만 재사용한다. onnxruntime InferenceSession.run()은 스레드-안전(공식
    지원 시나리오)이므로 합성 자체는 별도 락 없이 asyncio.to_thread로 동시 처리 가능하다.
    """

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
        self.use_cuda = os.getenv("PIPER_USE_CUDA", "false").strip().lower() == "true"
        # [속도 보정] 과거 phoneme_type을 espeak로 강제 대체했을 때는 모델의 duration
        # predictor가 학습 시 분절(pygoruut)과 달라 실측 약 2.5~3배 느리게 합성됐으나,
        # 아래 pygoruut 사전 음소화 도입 이후 정상 속도로 복원됨(2026-07-08 실측:
        # 20음절 문장 기준 length_scale=0.9에서 약 5s, 정상 범위).
        self.length_scale_min = float(os.getenv("PIPER_LENGTH_SCALE_MIN", "0.5"))
        self.length_scale_max = float(os.getenv("PIPER_LENGTH_SCALE_MAX", "2.0"))
        self.default_length_scale = float(os.getenv("PIPER_DEFAULT_LENGTH_SCALE", "0.9"))
        self._compat_config_path: Path | None = None
        self._valid_phonemes: set[str] | None = None
        self._pygoruut = None
        self._voice: PiperVoice | None = None
        self._voice_load_lock = asyncio.Lock()

    def _build_compat_config(self) -> Path:
        """phoneme_type을 text로 보정한 piper 런타임 호환 설정 파일 경로를 반환한다.

        원본 설정은 phoneme_type="pygoruut"이지만 piper-tts==1.4.2에는 pygoruut
        지원이 없다(PhonemeType enum: espeak/text/pinyin만 존재). 대신 pygoruut
        패키지로 이 프로세스에서 직접 음소화한 뒤 phoneme_type="text"로 그 결과를
        피처(문자 단위 매핑)로 그대로 흘려보낸다(espeak 대체 시 학습 분절과 달라
        속도가 비정상적으로 느려지는 문제가 있었음, 2026-07-08 실측 확인).

        라이브러리 함수 PiperVoice.load()는 config_path를 정상적으로 받아들이므로
        (기존 CLI 래퍼만 이 인자를 파싱 후 버리는 결함이 있었다), 모델 파일을 별도
        심볼릭 링크로 복제할 필요 없이 보정된 config만 만들어 넘기면 된다.
        """
        if self._compat_config_path and self._compat_config_path.exists():
            return self._compat_config_path

        if not self.config_path.exists():
            raise FileNotFoundError(f"Piper 설정 파일이 없습니다: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8-sig") as fp:
            config_data = json.load(fp)

        self._valid_phonemes = set(config_data.get("phoneme_id_map", {}).keys())
        if config_data.get("phoneme_type") == "pygoruut":
            config_data["phoneme_type"] = "text"

        compat_dir = Path(tempfile.gettempdir()) / "piper_runtime_compat"
        compat_dir.mkdir(parents=True, exist_ok=True)
        compat_config_path = compat_dir / f"{self.model_path.name}.json"

        with compat_config_path.open("w", encoding="utf-8") as fp:
            json.dump(config_data, fp, ensure_ascii=False)

        self._compat_config_path = compat_config_path
        return compat_config_path

    def _phonemize(self, text: str) -> str:
        """pygoruut로 한국어 텍스트를 IPA 음소열로 변환하고, 모델이 지원하지 않는
        결합 발음기호(예: 무파열음/경음/후설화 표시)는 제거해 phoneme_id_map과 맞춘다.

        [2026-07-09 실측 수정] Pygoruut()를 인자 없이 호출하면 내부적으로
        writeable_bin_dir=None -> tempfile.TemporaryDirectory()로 매번 새 임시
        디렉터리를 만들고 생성자가 끝나자마자 그 디렉터리를 삭제한다(pygoruut/pygoruut.py
        참조). 그 안에 받는 96MB 네이티브 바이너리(goruut-darwin-arm64 등)가 영구
        캐시되지 못해, 호출마다(같은 프로세스 내에서도) 재다운로드되고 3초 TTS
        타임아웃을 거의 항상 초과하는 것을 실제 서버 구동으로 확인했다.
        writeable_bin_dir=""를 넘기면 라이브러리가 자체적으로 ~/.goruut(홈 디렉터리
        하위 고정 경로)를 만들어 재사용하므로 최초 1회만 다운로드하면 된다.
        """
        if self._pygoruut is None:
            from pygoruut.pygoruut import Pygoruut

            self._pygoruut = Pygoruut(writeable_bin_dir="")

        raw = str(self._pygoruut.phonemize(language="Korean", sentence=text))

        # [2026-07-09 실측 수정] pygoruut(goruut 0.8.1 포함)의 한국어 사전이
        # 불완전해 흔한 음절('측', '직', '걸', '볼', '밑' 등)을 구두점(PrePunct)으로
        # 오분류하고 발음에서 통째로 누락시킨다. 예: '우측으로 돌아가세요' ->
        # '측uɯɾo toɾagasɛjo' (IPA 표기, 측 발음 소실 -> 재생 시 "우으로"로 들려 사용자가  # noqa: RUF003
        # 음성 짤림으로 체감). 결과 문자열에 한글이 남아 있으면 누락이 발생한
        # 것이므로, 표준 발음법 기반 규칙 변환기(korean_g2p)로 문장 전체를 대체
        # 변환한다. 정상 변환된 문장은 모델 학습 분포(pygoruut 출력)를 그대로 쓴다.
        if any("가" <= c <= "힣" for c in raw):
            from server.tts.korean_g2p import phonemize_korean

            fallback = phonemize_korean(text)
            logger.warning(
                f"[PiperTTS] pygoruut 음절 누락 감지 -> 규칙 기반 G2P 대체: "
                f"text={text!r}, pygoruut={raw!r}, g2p={fallback!r}"
            )
            raw = fallback

        valid = self._valid_phonemes or set()
        return "".join(c for c in raw if c in valid or c == " ")

    def _load_voice_sync(self) -> PiperVoice:
        """블로킹 ONNX 세션 로드를 동기 함수로 분리한다(최초 1회만 호출됨)."""
        from piper import PiperVoice

        compat_config = self._build_compat_config()
        voice = PiperVoice.load(self.model_path, config_path=compat_config, use_cuda=self.use_cuda)
        logger.info(f"[PiperTTS] 상주 ONNX 세션 로드 완료 (use_cuda={self.use_cuda})")
        return voice

    async def _ensure_voice(self) -> PiperVoice:
        if self._voice is not None:
            return self._voice
        async with self._voice_load_lock:
            if self._voice is None:
                self._voice = await asyncio.to_thread(self._load_voice_sync)
        return self._voice

    def _synthesize_sync(
        self, voice: PiperVoice, phonemes: str, length_scale: float
    ) -> bytes | None:
        """블로킹 합성 실행을 동기 함수로 분리한다."""
        from piper.config import SynthesisConfig

        syn_config = SynthesisConfig(length_scale=length_scale)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(phonemes, wav_file, syn_config=syn_config)

        audio_bytes = buffer.getvalue()
        if not audio_bytes:
            logger.error("[PiperTTS] 합성 결과 오디오가 비어 있습니다.")
            return None
        return audio_bytes

    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
        if not text or not text.strip():
            logger.warning("[PiperTTS] 빈 텍스트는 합성하지 않습니다.")
            return None

        if not self.model_path.exists():
            logger.error(f"[PiperTTS] 모델 파일이 없습니다: {self.model_path}")
            return None

        try:
            voice_obj = await self._ensure_voice()
            length_scale = max(self.length_scale_min, min(self.length_scale_max, speed))

            # asyncio 이벤트 루프 블로킹 방지를 위해 동기 실행을 스레드로 위임한다.
            phonemes = await asyncio.to_thread(self._phonemize, text)
            return await asyncio.to_thread(
                self._synthesize_sync,
                voice_obj,
                phonemes,
                length_scale,
            )
        except Exception as e:
            logger.error(f"[PiperTTS] 합성 중 오류 발생: {e}")
            return None


class SupertonicTTSService(TTSService):
    """Supertonic(supertone-inc) ONNX 기반 한국어 TTS 서비스.

    [도입 경위, 2026-07-09] PiperTTSService(piper-kss-korean 모델)는 pygoruut/자체
    규칙 기반 G2P/espeak 등 어떤 음소화 경로를 쓰더라도 실기기 청취 검증에서
    부자연스러운 발음이 확인됐다(문장 중간 음절 누락 및 조음 이상, 모델 자체
    품질 한계로 판단). Supertonic 3(99M 파라미터, MIT 라이선스, 31개 언어,
    ONNX Runtime 기반)으로 교체 검증한 결과 동일 문장에서 자연스러운 한국어
    발음이 확인되어(사용자 청취 승인, 2026-07-09) 신규 엔진으로 추가한다.
    PiperTTSService는 TTSService 추상화의 핫스왑 설계 의도대로 코드에 남겨두고
    TTS_ENGINE 환경 변수로 선택한다.

    [모델 캐시 경로 주의] 모델 자산(~380MB)을 server/models/ 하위에 두면
    docker-compose.yml의 `../server:/app/server` 볼륨 마운트가 컨테이너 시작 시
    빌드 타임에 받아둔 내용을 호스트 쪽 내용으로 덮어써 버려(pygoruut 사례와 동일
    문제), 빌드 타임 사전 다운로드가 무의미해진다. 라이브러리 기본 캐시 경로
    (~/.cache/supertonic3, /app 바깥)를 그대로 사용해 이 문제를 피한다.
    """

    def __init__(self) -> None:
        model_dir_env = os.getenv("SUPERTONIC_MODEL_DIR", "").strip()
        self.model_dir = model_dir_env or None
        self.voice_name = os.getenv("SUPERTONIC_VOICE", "F1")
        self.total_steps = int(os.getenv("SUPERTONIC_TOTAL_STEPS", "8"))
        self.speed_min = float(os.getenv("SUPERTONIC_SPEED_MIN", "0.7"))
        self.speed_max = float(os.getenv("SUPERTONIC_SPEED_MAX", "2.0"))
        self._tts: SupertonicTTS | None = None
        self._style: SupertonicStyle | None = None
        self._load_lock = asyncio.Lock()
        # [2026-07-09 실측 수정] tts.synthesize()가 스레드 안전하다는 보장이 없어(Piper의
        # onnxruntime InferenceSession.run()과 달리 공식 문서화된 바 없음), 인지 경로
        # 연속 안내 요청이 asyncio.to_thread로 겹쳐 실행될 때 서로 다른 문장인데도
        # b64len/duration이 완전히 동일한 오디오가 나오는 결함이 실기기 청취 검증으로
        # 확인됐다(내부 파이프라인 버퍼 경합으로 추정). 합성 호출 자체를 직렬화한다.
        self._synthesize_lock = asyncio.Lock()

    def _load_sync(self) -> tuple[SupertonicTTS, SupertonicStyle]:
        """블로킹 ONNX 세션 로드 및 보이스 스타일 로드를 동기 함수로 분리한다."""
        from supertonic import TTS

        tts = TTS(model_dir=self.model_dir, auto_download=True)
        style = tts.get_voice_style(voice_name=self.voice_name)
        logger.info(f"[SupertonicTTS] 모델 로드 완료 (voice={self.voice_name})")
        return tts, style

    async def _ensure_loaded(self) -> tuple[SupertonicTTS, SupertonicStyle]:
        if self._tts is not None and self._style is not None:
            return self._tts, self._style
        async with self._load_lock:
            if self._tts is None:
                self._tts, self._style = await asyncio.to_thread(self._load_sync)
        return self._tts, self._style

    def _synthesize_sync(
        self, tts: SupertonicTTS, style: SupertonicStyle, text: str, speed: float
    ) -> bytes | None:
        """블로킹 합성 실행 및 float32 파형 -> 16bit PCM WAV 변환을 동기 함수로 분리한다."""
        import numpy as np

        wav, _duration = tts.synthesize(
            text=text,
            lang="ko",
            voice_style=style,
            total_steps=self.total_steps,
            speed=speed,
        )
        samples = np.clip(np.asarray(wav).squeeze(), -1.0, 1.0)
        # [2026-07-09] 페이로드 크기(44.1kHz vs 22.05kHz 데시메이션) 축소 테스트로는
        # 실기기 절단 현상이 재현/해소되지 않아 크기 자체는 원인이 아님을 확인했다.
        # base64 전송을 WS 바이너리 프레임으로 전환하는 것으로 원인을 좁히는 중이라,
        # 품질 저하 없는 원본 44.1kHz로 되돌린다.
        pcm16 = (samples * 32767.0).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            wav_file.writeframes(pcm16.tobytes())

        audio_bytes = buffer.getvalue()
        if not audio_bytes:
            logger.error("[SupertonicTTS] 합성 결과 오디오가 비어 있습니다.")
            return None
        return audio_bytes

    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
        if not text or not text.strip():
            logger.warning("[SupertonicTTS] 빈 텍스트는 합성하지 않습니다.")
            return None

        try:
            tts, style = await self._ensure_loaded()
            clamped_speed = max(self.speed_min, min(self.speed_max, speed))

            # asyncio 이벤트 루프 블로킹 방지를 위해 동기 실행을 스레드로 위임하되,
            # 합성 자체는 _synthesize_lock으로 직렬화해 겹쳐 실행되지 않게 한다.
            async with self._synthesize_lock:
                return await asyncio.to_thread(
                    self._synthesize_sync, tts, style, text, clamped_speed
                )
        except Exception as e:
            logger.error(f"[SupertonicTTS] 합성 중 오류 발생: {e}")
            return None


# ============================================================
# [파트 3] Pyttsx3TTSService 클래스
# - pyttsx3 기반 OS 내장형 한글 TTS 엔진 구현체
# ============================================================


class Pyttsx3TTSService(TTSService):
    """
    pyttsx3 기반 한국어 TTS 서비스.
    임시 파일에 음성을 WAV 포맷으로 저장한 뒤, 파일 바이트 데이터를 읽어 반환합니다.
    """

    def __init__(self) -> None:
        logger.info("[Pyttsx3TTS] pyttsx3 서비스가 준비되었습니다.")

    def _synthesize_sync(self, text: str, output_path: str, speed: float) -> bytes | None:
        import pyttsx3

        is_windows = sys.platform == "win32"
        if is_windows:
            import pythoncom

            pythoncom.CoInitialize()

        try:
            # 호출 단위로 독립된 pyttsx3 엔진 생성
            engine = pyttsx3.init()

            # 발화 속도 설정 (기본 속도에 배율 적용)
            rate = engine.getProperty("rate")
            engine.setProperty("rate", int(rate * speed))

            # 한국어 목소리 설정 시도
            voices = engine.getProperty("voices")
            for voice in voices:
                name_lower = voice.name.lower()
                languages = getattr(voice, "languages", [])
                langs_lower = [str(lang).lower() for lang in languages]

                is_korean = (
                    "korean" in name_lower
                    or "ko" in name_lower
                    or any("ko" in lang for lang in langs_lower)
                )
                if is_korean:
                    engine.setProperty("voice", voice.id)
                    break

            # 파일로 저장 후 대기
            engine.save_to_file(text, output_path)
            engine.runAndWait()

            # 생성된 음성 파일 로드
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, "rb") as f:
                    return f.read()
            else:
                logger.error(f"[Pyttsx3TTS] 음성 파일 저장 실패 또는 크기가 0입니다: {output_path}")
                return None
        except Exception as e:
            logger.error(f"[Pyttsx3TTS] 동기 합성 중 에러 발생: {e}")
            return None
        finally:
            if is_windows:
                pythoncom.CoUninitialize()

    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
        if not text or not text.strip():
            logger.warning("[Pyttsx3TTS] 빈 텍스트는 합성하지 않습니다.")
            return None

        # 임시 파일 경로를 생성하고, 합성이 완료되면 바이트를 반환 후 삭제
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # asyncio 이벤트 루프의 블로킹 방지를 위해 비동기 스레드 실행
            audio_data = await asyncio.to_thread(self._synthesize_sync, text, temp_path, speed)
            return audio_data
        except Exception as e:
            logger.error(f"[Pyttsx3TTS] generate 에러 발생: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"[Pyttsx3TTS] 임시 파일 삭제 실패: {e}")


# ============================================================
# [파트 4] get_tts_service() 팩토리 함수
# - 환경 변수에 따라 어떤 TTS 구현체를 사용할지 결정
# - 현재 지원: supertonic (기본), piper, pyttsx3
# - 클라이언트(react-native-tts) 사용 시에도 이 팩토리는 유지될 수 있음
#   (단, 이 경우 실제 audio bytes 생성은 클라이언트가 담당)
# ============================================================


def get_tts_service() -> TTSService:
    """
    현재 설정에 맞는 음성 합성 서비스 객체를 만들어서 돌려준다.
    환경 변수 TTS_ENGINE (supertonic, piper, pyttsx3. 기본 supertonic)에 따라 결정.
    docs/environment_variables.md, pipeline_stage_design.md, architecture.md 준수.

    supertonic이 기본값인 이유는 2026-07-09 실기기 청취 검증 결과 발음 품질이
    가장 우수했기 때문이다(CLAUDE.md §2). pyttsx3는 GPU/네트워크 없이 로컬
    개발 환경(특히 Windows)에서 즉시 구동 가능한 저사양 대체 옵션으로 보존한다.
    """
    engine = os.getenv("TTS_ENGINE", "supertonic").lower().strip()

    if engine not in {"", "default", "supertonic", "piper", "pyttsx3"}:
        logger.warning(f"[TTS] 지원하지 않는 TTS_ENGINE='{engine}'. 기본값(supertonic) 사용.")

    try:
        if engine == "piper":
            return PiperTTSService()
        if engine == "pyttsx3":
            return Pyttsx3TTSService()
        return SupertonicTTSService()
    except Exception as e:
        logger.error(f"[TTS] TTS 서비스 초기화 실패 (engine={engine}): {e}")
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
