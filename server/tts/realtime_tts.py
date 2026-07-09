import sys

if hasattr(sys.stdout, "reconfigure"):  # 한글 깨짐을 방지하기 위한 방어적 인코딩 설정
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
import base64
import io
import logging
import os
import wave

from server.tts.tts_service import extract_llm_text, get_tts_service

logger = logging.getLogger(__name__)

# [속도 보정] PiperTTSService 참고: espeak 대체 음소화로 인해 length_scale=1.0(기본)이
# 실측 약 2.5~3배 느리게 합성되어 기본 합성 속도를 낮춰 보정한다.
DEFAULT_SPEED = float(os.getenv("PIPER_DEFAULT_LENGTH_SCALE", "0.9"))


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

    def __init__(self, tts_service=None):
        # 전달받은 유효시간을 인스턴스 변수에 저장
        # 기본값은 클래스 상수인 60초를 사용
        self.tts = tts_service or get_tts_service()

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

        try:
            audio_bytes = await asyncio.wait_for(
                self.tts.generate(text=text, voice=voice, speed=speed), timeout=15.0
            )
            # 음성 데이터가 정상적으로 생성된 경우
            if audio_bytes:
                # 바이트 데이터를 베이스64 문자열로 변환
                # 웹소켓 전송을 위해 문자열 형태로 만들어야 함
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                return b64_audio, _wav_duration_ms(audio_bytes)
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


# 전역에서 사용할 수 있는 기본 인스턴스 생성
realtime_tts = RealtimeTTS()
