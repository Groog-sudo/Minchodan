# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.orchestration import run_orchestrator
from .stt_config import STT_ORCH_CLASS_NAME, STT_ORCH_RISK_HINT
from .stt_runtime import validate_stt_bridge_config
from .stt_schema import SttTranscribeResult


# ============================================================
# STT -> 기존 LLM 브리지
# ============================================================
# [바이브 코딩 부분]
# - STT 텍스트를 기존 오케스트레이션 입력 형식으로 감싸는 어댑터.
# - LLM 신규 구현 없이 기존 server/orchestration 경로를 재사용.
#
# [하드 코딩 부분]
# - 어떤 위험도 기본값을 쓸지, STT 전용 프롬프트 힌트 규칙은 담당자가 직접 정의.


class SttToLlmBridge:
    @staticmethod
    def build_orch_input(stt_result: SttTranscribeResult) -> dict:
        """
        [바이브 코딩 부분]
        STT 결과를 기존 run_orchestrator(state) 입력 형태로 변환한다.
        """
        validate_stt_bridge_config()

        return {
            "event": {
                "event_id": f"stt-{stt_result.saved_file}",
                "risk_hint": STT_ORCH_RISK_HINT,
                "source": "stt",
            },
            "detected_classes": [STT_ORCH_CLASS_NAME],
            "positions": [""],
            "risk_level": STT_ORCH_RISK_HINT,
            "rag_context": stt_result.text,
            "retry_count": 0,
            "verified": False,
            "validation_errors": [],
        }

    async def invoke_existing_llm(self, stt_result: SttTranscribeResult) -> dict:
        """
        [하드 코딩 부분]
        STT 텍스트를 기존 오케스트레이션으로 전달하고 결과를 표준 응답 dict로 매핑한다.
        빈 입력은 stt-bridge-empty 폴백, 실행 예외는 stt-bridge-error 폴백으로 처리한다.
        원문 텍스트 대신 길이/모델명/파일명 메타 정보만 내부 처리에 사용한다.
        """
        validate_stt_bridge_config()

        normalized_text = (stt_result.text or "").strip()
        if not normalized_text:
            return {
                "guidance_text": "입력이 없어 정지하세요",
                "used_fallback_llm": True,
                "source": "stt-bridge-empty",
            }

        # 원문 텍스트는 기록하지 않고 메타 정보만 보존한다.
        _text_len = len(normalized_text)
        _model_name = stt_result.model_name
        _saved_file = stt_result.saved_file

        try:
            orch_input = self.build_orch_input(stt_result)
            orch_result = await run_orchestrator(orch_input)
            return {
                "guidance_text": orch_result.get("guidance_text", ""),
                "used_fallback_llm": orch_result.get("used_fallback_llm", False),
                "source": "stt-bridge",
            }
        except Exception:
            _ = (_text_len, _model_name, _saved_file)
            return {
                "guidance_text": "안전을 위해 잠시 멈추고 주변을 확인하세요",
                "used_fallback_llm": True,
                "source": "stt-bridge-error",
            }

    async def invoke_existing_llm_template(self, stt_result: SttTranscribeResult) -> dict:
        """
        [바이브 코딩 부분]
        최소 템플릿 실행 경로.
        실제 운영에서는 invoke_existing_llm()을 직접 작성해서 사용한다.
        """
        if not stt_result.has_input:
            return {
                "guidance_text": "입력이 없어 정지하세요",
                "used_fallback_llm": True,
                "source": "stt-template",
            }

        orch_input = self.build_orch_input(stt_result)
        orch_result = await run_orchestrator(orch_input)
        return {
            "guidance_text": orch_result.get("guidance_text", ""),
            "used_fallback_llm": orch_result.get("used_fallback_llm", False),
            "source": "stt-template",
        }
