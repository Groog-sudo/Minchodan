"""
Audio Validator MCP 모듈.
생성된 실시간 음성 안내(WAV) 오디오의 포맷 정합성, TTFB 및 무음 구간을 검증합니다.
"""

import contextlib
import io
import logging
import sys
import wave

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class AudioValidatorMCP:
    """
    TTS 엔진이 생성한 오디오 데이터를 실시간으로 검증하는 MCP 모듈.
    """

    def __init__(self, target_sample_rate: int = 22050, max_ttfb_ms: float = 2000.0):
        self.target_sample_rate = target_sample_rate
        self.max_ttfb_ms = max_ttfb_ms

    def validate_wav_bytes(
        self, wav_bytes: bytes, ttfb_ms: float, alert_id: str = "cognitive_guidance"
    ) -> dict:
        """
        WAV 바이너리 바이트를 파싱하고 검증 결과를 딕셔너리로 반환합니다.
        """
        is_valid = True
        error_reasons = []
        sample_rate = 0
        channels = 0
        duration_sec = 0.0
        frame_count = 0

        # 바이너리가 비어있거나 너무 작은 경우
        if not wav_bytes or len(wav_bytes) < 44:
            is_valid = False
            error_reasons.append("WAV 파일의 크기가 너무 작거나 비어있습니다 (최소 44바이트 필요).")
            return {
                "alert_id": alert_id,
                "is_valid": is_valid,
                "error_reasons": error_reasons,
                "ttfb_ms": ttfb_ms,
                "sample_rate": sample_rate,
                "channels": channels,
                "duration_sec": duration_sec,
                "byte_size": len(wav_bytes) if wav_bytes else 0,
            }

        try:
            # WAV 헤더 검증
            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                frame_count = wav_file.getnframes()
                if sample_rate > 0:
                    duration_sec = frame_count / float(sample_rate)

            # 1. 샘플 레이트 검증 (Supertonic/Piper 기본 22050Hz 등)
            if sample_rate != self.target_sample_rate and sample_rate not in (
                16000,
                22050,
                24000,
                32000,
                44100,
                48000,
            ):
                is_valid = False
                error_reasons.append(f"지원되지 않는 비표준 샘플 레이트 감지: {sample_rate}Hz")

            # 2. 채널 수 검증 (시각장애인 단말 재생은 모노/스테레오 표준 준수)
            if channels not in (1, 2):
                is_valid = False
                error_reasons.append(f"비표준 오디오 채널 수: {channels}")

            # 3. 무음 검증 (프레임 크기가 0이거나 재생 시간이 극단적으로 짧은 경우)
            if duration_sec < 0.1:
                is_valid = False
                error_reasons.append(f"오디오 재생 시간이 너무 짧습니다: {duration_sec:.3f}초")

            # 4. TTFB 지연 가드레일 검증
            if ttfb_ms > self.max_ttfb_ms:
                is_valid = False
                error_reasons.append(
                    f"TTS 지연 시간 임계치 초과: {ttfb_ms:.1f}ms (최대 {self.max_ttfb_ms}ms)"
                )

        except Exception as e:
            is_valid = False
            error_reasons.append(f"WAV 헤더 파싱 중 예외 발생: {e!s}")

        return {
            "alert_id": alert_id,
            "is_valid": is_valid,
            "error_reasons": error_reasons,
            "ttfb_ms": ttfb_ms,
            "sample_rate": sample_rate,
            "channels": channels,
            "duration_sec": duration_sec,
            "byte_size": len(wav_bytes),
        }

    async def validate_and_broadcast(
        self, wav_bytes: bytes, ttfb_ms: float, alert_id: str = "cognitive_guidance"
    ):
        """
        오디오 검증을 실행하고 그 결과를 관제 프론트엔드로 브로드캐스트합니다.
        """
        result = self.validate_wav_bytes(wav_bytes, ttfb_ms, alert_id)
        if not result["is_valid"]:
            logger.warning(
                f"[AUDIO VALIDATOR] 오디오 검증 실패: {result['error_reasons']} "
                f"(alert_id={alert_id}, ttfb={ttfb_ms:.1f}ms)"
            )
        else:
            logger.info(
                f"[AUDIO VALIDATOR] 오디오 검증 성공: {result['sample_rate']}Hz, "
                f"{result['duration_sec']:.2f}초 (ttfb={ttfb_ms:.1f}ms)"
            )

        # 관제 모니터링 SSE 채널로 전송 (Redis Streams 발행)
        from server.mcp.manager import mcp_manager

        await mcp_manager.publish_metric("audio_validation", result)


# 싱글톤 인스턴스 제공
audio_validator = AudioValidatorMCP()
