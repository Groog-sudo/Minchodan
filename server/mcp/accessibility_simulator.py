"""
Accessibility Simulator MCP 모듈.
시각장애인용 announceForAccessibility 텍스트와 실제 재생을 위해 합성된 음성 가이드 간의
의미/텍스트 정합성을 검증하여 접근성 준수 여부를 진단합니다.
"""

import contextlib
import logging
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class AccessibilitySimulatorMCP:
    """
    안내 텍스트와 실제 합성용 텍스트의 정합성 및 방향 키워드 일치 여부를 대조하는 MCP 검증 모듈.
    """

    def __init__(self, match_threshold: float = 0.9):
        self.match_threshold = match_threshold
        # 필수 보행 방향 제어 키워드
        self.direction_keywords = ["좌", "우", "직진", "정지", "멈춤", "앞", "뒤"]

    def analyze_accessibility_alignment(self, guidance_text: str, synth_text: str) -> dict:
        """
        두 텍스트 간의 정합성 분석 및 접근성 경고 검출.
        """
        if not guidance_text or not synth_text:
            return {
                "is_aligned": False,
                "similarity_score": 0.0,
                "missing_directions": [],
                "warnings": ["입력 텍스트가 비어 있어 분석을 진행할 수 없습니다."],
            }

        # 1. 간단한 글자 정합 분석 (자카드 유사도 방식)
        words_guidance = set(guidance_text.split())
        words_synth = set(synth_text.split())

        intersection = words_guidance.intersection(words_synth)
        union = words_guidance.union(words_synth)

        similarity = len(intersection) / len(union) if union else 0.0
        is_aligned = similarity >= self.match_threshold

        # 2. 방향 키워드 대조 (접근성에서 방향 지시는 치명적이므로 상호 누락 체크)
        warnings = []
        missing_directions = []

        for kw in self.direction_keywords:
            in_guidance = kw in guidance_text
            in_synth = kw in synth_text

            if in_guidance != in_synth:
                is_aligned = False
                missing_directions.append(kw)
                warnings.append(
                    f"방향성 키워드 '{kw}' 불일치 감지 (가이드텍스트: {in_guidance}, 합성텍스트: {in_synth})"
                )

        # 3. 길이 및 빈 텍스트 경고
        if len(guidance_text) > 40:
            warnings.append("접근성 가이드 텍스트가 시각장애인 속독 한계(40자)를 초과했습니다.")

        return {
            "guidance_text": guidance_text,
            "synthesized_text": synth_text,
            "similarity_score": round(similarity, 3),
            "is_aligned": is_aligned,
            "missing_directions": missing_directions,
            "warnings": warnings,
        }

    async def simulate_and_broadcast(self, guidance_text: str, synth_text: str):
        """
        두 텍스트 간의 접근성 정합성 시뮬레이션 결과를 분석하고 브로드캐스트합니다.
        """
        result = self.analyze_accessibility_alignment(guidance_text, synth_text)

        if not result["is_aligned"]:
            logger.warning(
                f"[ACCESSIBILITY SIMULATOR] 접근성 비정합 감지: {result['warnings']} "
                f"(가이드: '{guidance_text}', 합성: '{synth_text}')"
            )
        else:
            logger.info(
                f"[ACCESSIBILITY SIMULATOR] 접근성 정합성 검증 통과 (유사도: {result['similarity_score']})"
            )

        # 관제 모니터링 SSE 채널로 전송 (Redis Streams 발행)
        payload = {
            "alert_id": "accessibility",
            "is_valid": result["is_aligned"],
            "similarity_score": result["similarity_score"],
            "warnings": result["warnings"],
            "details": result,
        }
        from server.mcp.manager import mcp_manager

        await mcp_manager.publish_metric("accessibility_validation", payload)


# 싱글톤 인스턴스 제공
accessibility_simulator = AccessibilitySimulatorMCP()
