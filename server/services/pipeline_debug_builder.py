"""관리자 콘솔용 파이프라인 디버그 JSON 빌더."""

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PREVIEW_MAX = 800


def _preview(text: str | None, max_len: int = _PREVIEW_MAX) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped
    return stripped[:max_len] + "..."


def serialize_pipeline_debug(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    return json.dumps(payload, ensure_ascii=False)


def build_reflex_pipeline_debug(
    *,
    alert_id: str,
    clip: str,
    direction: str | None = None,
    class_name: str | None = None,
    distance: str | None = None,
) -> dict[str, Any]:
    return {
        "path": "reflex",
        "alert_id": alert_id,
        "clip": clip,
        "direction": direction,
        "class_name": class_name,
        "distance": distance,
    }


def build_cognitive_pipeline_debug(
    *,
    guidance_text: str,
    rag_query: str,
    rag_context: str,
    orch_result: dict[str, Any],
    clock_direction: str = "",
    distance_class: str = "",
    object_ko: str = "",
    llm_provider: str = "",
) -> dict[str, Any]:
    used_fast_lane = bool(orch_result.get("used_fast_lane"))
    debug: dict[str, Any] = {
        "path": "cognitive",
        "rag_query": rag_query,
        "rag_context": _preview(rag_context),
        "clock_direction": clock_direction or orch_result.get("clock_direction") or "",
        "distance_class": distance_class or orch_result.get("distance") or "",
        "object_ko": object_ko or orch_result.get("object_ko") or "",
        "llm_provider": llm_provider,
        "used_fast_lane": used_fast_lane,
        "fast_lane_cache_key": orch_result.get("fast_lane_cache_key") or "",
        "l3_verified": bool(orch_result.get("verified", False)),
        "validation_errors": list(orch_result.get("validation_errors") or []),
        "used_static_fallback": bool(orch_result.get("used_static_fallback", False)),
        "retry_count": int(orch_result.get("retry_count", 0)),
        "response_text": guidance_text,
    }
    if used_fast_lane:
        debug["llm_text"] = None
        debug["generation_mode"] = "fast_lane_template"
    else:
        debug["llm_text"] = guidance_text
        debug["generation_mode"] = "langgraph_l2_l3"
    return debug


def build_stt_pipeline_debug(
    *,
    stt_transcript: str,
    bridge_result: dict[str, Any],
) -> dict[str, Any]:
    source = str(bridge_result.get("source") or "")
    guidance_text = str(bridge_result.get("guidance_text") or "")
    debug: dict[str, Any] = {
        "path": "stt",
        "stt_transcript": stt_transcript.strip(),
        "bridge_source": source,
        "response_text": guidance_text,
    }
    rag_query = bridge_result.get("rag_query")
    if rag_query:
        debug["rag_query"] = rag_query
    rag_results = bridge_result.get("rag_results")
    if rag_results:
        debug["rag_results"] = rag_results
    if "llm" in source or source.endswith("-rag"):
        debug["llm_text"] = guidance_text
    else:
        debug["llm_text"] = None
    if bridge_result.get("used_fallback_llm") is not None:
        debug["used_fallback_llm"] = bool(bridge_result.get("used_fallback_llm"))
    return debug
