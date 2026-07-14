import sys

if hasattr(sys.stdout, "reconfigure"):  # 한글 깨짐을 방지하기 위한 방어적 인코딩 설정
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
import base64
import io
import logging
import os
import time
import wave

from dotenv import load_dotenv

from server.tts.tts_service import extract_llm_text, get_tts_service

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))

# 인지 경로 기본 발화 속도. Supertonic/Piper/pyttsx3 공통.
# 0.85: 시각장애인 안내 가독성(너무 빠른 기계음 체감 완화). Piper 단독 보정은
# PIPER_DEFAULT_LENGTH_SCALE로 덮어쓸 수 있다.
DEFAULT_SPEED = float(
    os.getenv("TTS_DEFAULT_SPEED", os.getenv("PIPER_DEFAULT_LENGTH_SCALE", "0.85"))
)

_background_tasks = set()


def _wav_duration_ms(audio_bytes: bytes) -> float:
    """WAV 바이트에서 재생 길이(ms)를 계산한다. 서버 쿨다운을 실제 오디오 길이에
    동적으로 맞추기 위한 용도(고정 쿨다운과 실제 합성 길이의 불일치로 인한
    안내 음성 짤림 방지). 파싱 실패 시 0.0을 반환하고 호출측 고정 하한값에 맡긴다.
    """
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return 0.0
            return (frames / rate) * 1000.0
    except (wave.Error, EOFError) as e:
        logger.warning(f"[TTS] WAV 길이 계산 실패, 0으로 처리합니다: {e}")
        return 0.0


class RealtimeTTS:
    """
    실시간 음성 합성 클래스
    인지 경로에서 생성된 문장을 음성으로 변환하는 역할을 담당한다
    """

    DEFAULT_TTL = 60

    # 2026-07-11 합성 결과 캐시 상한. 안내문 대부분이 고정 문구(웨이크업/재시도/
    # 빈입력 등)라 동일 텍스트 재합성이 반복되는데, CPU 폴백 환경에서 합성이
    # 1.4~1.9초를 차지해 STT 왕복 체감 지연의 주요인이었다(실기기 실측).
    CACHE_MAX_ENTRIES = 64

    def __init__(self, tts_service=None):
        # 전달받은 유효시간을 인스턴스 변수에 저장
        # 기본값은 클래스 상수인 60초를 사용
        self.tts = tts_service or get_tts_service()
        # (text, voice, speed) -> (b64_audio, duration_ms). 삽입 순서 유지되는
        # dict를 FIFO로 운용해 상한 초과 시 가장 오래된 항목부터 제거한다.
        self._cache: dict[tuple[str, str, float], tuple[str, float]] = {}

    async def synthesize(self, text, voice="ko", speed=DEFAULT_SPEED):
        """
        전달받은 문장을 음성으로 합성한다

        text: 합성할 한국어 문장
        voice: 사용할 음성 스타일
        speed: 말하기 속도

        반환값: (베이스64로 인코딩된 오디오 문자열 | None, 재생 길이 ms)
        합성에 실패하거나 타임아웃을 초과하면 (None, 0.0)을 반환하여
        단말 내장 TTS 폴백 작동을 유도한다. 길이 값은 호출측(consumer)이
        다음 안내 전송까지의 쿨다운을 실제 오디오 길이에 맞춰 동적으로
        정하는 데 사용한다(고정 쿨다운으로 인한 짤림 방지).

        [타임아웃 근거] PiperTTSService는 최초 1회 모델을 상주 로드한 뒤
        재사용하므로 콜드스타트 비용은 초기화 시 1회만 발생한다. 3.0초는
        상주 로드 이후 순수 합성 시간에 대한 여유 가드레일이다.
        """

        # 빈 문자열이나 공백만 있는 경우 합성을 시도하지 않는다
        if not text or not text.strip():
            logger.warning("음성 합성할 텍스트가 비어 있습니다.")
            return None, 0.0

        # 동일 문구 재합성 회피: 고정 안내문은 첫 합성 결과를 재사용한다.
        cache_key = (text, voice, float(speed))
        cached = self._cache.get(cache_key)
        if cached is not None:
            # 캐시 적중 시에도 관제 콘솔 업데이트를 위해 비동기 검증 이벤트 전송 (0ms 지연)
            try:
                b64_audio, _ = cached
                audio_bytes = base64.b64decode(b64_audio.encode("utf-8"))
                from server.mcp.accessibility_simulator import accessibility_simulator
                from server.mcp.audio_validator import audio_validator

                # 캐시이므로 TTFB는 0ms로 인지
                task1 = asyncio.create_task(
                    audio_validator.validate_and_broadcast(audio_bytes, 0.0, text)
                )
                task2 = asyncio.create_task(
                    accessibility_simulator.simulate_and_broadcast(text, text)
                )
                _background_tasks.add(task1)
                _background_tasks.add(task2)
                task1.add_done_callback(_background_tasks.discard)
                task2.add_done_callback(_background_tasks.discard)
            except Exception as e:
                logger.warning(f"[TTS] 캐시 히트 검증 백그라운드 태스크 실패: {e}")
            return cached

        try:
            start_time = time.perf_counter()
            audio_bytes = await asyncio.wait_for(
                self.tts.generate(text=text, voice=voice, speed=speed), timeout=15.0
            )
            ttfb_ms = (time.perf_counter() - start_time) * 1000.0

            # 음성 데이터가 정상적으로 생성된 경우
            if audio_bytes:
                # Audio Validator MCP 비동기 실행 (0ms 지연 가드레일)
                from server.mcp.audio_validator import audio_validator

                task1 = asyncio.create_task(
                    audio_validator.validate_and_broadcast(audio_bytes, ttfb_ms, text)
                )

                # Accessibility Simulator MCP 비동기 실행 (0ms 지연 가드레일)
                from server.mcp.accessibility_simulator import accessibility_simulator

                task2 = asyncio.create_task(
                    accessibility_simulator.simulate_and_broadcast(text, text)
                )
                _background_tasks.add(task1)
                _background_tasks.add(task2)
                task1.add_done_callback(_background_tasks.discard)
                task2.add_done_callback(_background_tasks.discard)

                # 바이트 데이터를 베이스64 문자열로 변환
                # 웹소켓 전송을 위해 문자열 형태로 만들어야 함
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                duration_ms = _wav_duration_ms(audio_bytes)
                if len(self._cache) >= self.CACHE_MAX_ENTRIES:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[cache_key] = (b64_audio, duration_ms)
                return b64_audio, duration_ms
            else:
                # 음성 데이터가 비어있는 경우 None 반환
                return None, 0.0

        except TimeoutError:
            logger.warning(
                f"[TTS] 음성 합성 시간 초과(3.0s 경과). 단말 내장 TTS 우회 폴백을 가동합니다: '{text}'"
            )
            return None, 0.0
        except Exception as e:
            # 합성 과정에서 예외가 발생한 경우 에러 로그를 남기고 None 반환
            logger.error(f"음성 합성 중 오류 발생: {e}")
            return None, 0.0

    async def synthesize_from_llm(self, llm_output, voice="ko", speed=DEFAULT_SPEED):
        """LLM 결과(dict/string)에서 문장을 추출해 TTS 합성을 수행한다."""
        text = extract_llm_text(llm_output)
        if not text:
            logger.warning("LLM 출력에서 합성 가능한 guidance_text를 찾지 못했습니다.")
            return None, 0.0
        return await self.synthesize(text=text, voice=voice, speed=speed)

    async def prewarm(self, texts: list[str], voice: str = "ko", speed=DEFAULT_SPEED) -> int:
        """서버 기동 시 DB 이력에서 뽑은 빈도 높은 문장을 미리 합성해 캐시를 채운다.

        문장 하나가 실패해도 나머지는 계속 진행한다(프리워밍은 부가 기능이라
        실패가 서버 기동이나 이후 실시간 합성을 막으면 안 된다). texts 길이가
        CACHE_MAX_ENTRIES를 넘으면 FIFO 축출로 앞쪽 항목이 밀려나 프리워밍
        효과가 사라지므로 상한을 넘지 않도록 호출측(list_frequent_tts_texts의
        limit)에서 미리 제한해야 한다.

        반환값: 실제로 캐시에 채워진(합성 성공한) 문장 수.
        """
        if len(texts) > self.CACHE_MAX_ENTRIES:
            logger.warning(
                f"[TTS] 프리워밍 대상({len(texts)}건)이 캐시 상한"
                f"({self.CACHE_MAX_ENTRIES})을 초과해 앞쪽 항목이 밀려날 수 있습니다."
            )

        warmed = 0
        for text in texts:
            if not text or not text.strip():
                continue
            try:
                b64_audio, _ = await self.synthesize(text=text, voice=voice, speed=speed)
            except Exception as e:
                logger.warning(f"[TTS] 프리워밍 합성 실패, 건너뜁니다: '{text}' ({e})")
                continue
            if b64_audio is not None:
                warmed += 1
        return warmed


# 전역에서 사용할 수 있는 기본 인스턴스 생성
realtime_tts = RealtimeTTS()
