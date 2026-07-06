import sys

if hasattr(sys.stdout, "reconfigure"):  # 한글 깨짐을 방지하기 위한 방어적 인코딩 설정
    sys.stdout.reconfigure(encoding="utf-8")

import base64
import logging

from server.tts.tts_service import extract_llm_text, get_tts_service

logger = logging.getLogger(__name__)


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

    async def synthesize(self, text, voice="ko", speed=1.0):
        """
        전달받은 문장을 음성으로 합성한다

        text: 합성할 한국어 문장
        voice: 사용할 음성 스타일
        speed: 말하기 속도

        반환값: 베이스64로 인코딩된 오디오 문자열
        합성에 실패하면 None을 반환한다
        """

        # 빈 문자열이나 공백만 있는 경우 합성을 시도하지 않는다
        if not text or not text.strip():
            logger.warning("음성 합성할 텍스트가 비어 있습니다.")
            return None

        try:
            audio_bytes = await self.tts.generate(text=text, voice=voice, speed=speed)
            # 음성 데이터가 정상적으로 생성된 경우
            if audio_bytes:
                # 바이트 데이터를 베이스64 문자열로 변환
                # 웹소켓 전송을 위해 문자열 형태로 만들어야 함
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                return b64_audio
            else:
                # 음성 데이터가 비어있는 경우 None 반환
                return None

        except Exception as e:
            # 합성 과정에서 예외가 발생한 경우 에러 로그를 남기고 None 반환
            logger.error(f"음성 합성 중 오류 발생: {e}")
            return None

    async def synthesize_from_llm(self, llm_output, voice="ko", speed=1.0):
        """LLM 결과(dict/string)에서 문장을 추출해 TTS 합성을 수행한다."""
        text = extract_llm_text(llm_output)
        if not text:
            logger.warning("LLM 출력에서 합성 가능한 guidance_text를 찾지 못했습니다.")
            return None
        return await self.synthesize(text=text, voice=voice, speed=speed)


# 전역에서 사용할 수 있는 기본 인스턴스 생성
realtime_tts = RealtimeTTS()
