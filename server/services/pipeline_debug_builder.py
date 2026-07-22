"""관리자 콘솔용 파이프라인 디버그 JSON 빌더."""

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PREVIEW_MAX = 800
_RAG_RESULTS_MAX = 5


def _preview(text: str | None, max_len: int = _PREVIEW_MAX) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped
    return stripped[:max_len] + "..."


def _compact_detection(det: Any) -> dict[str, Any]:
    if hasattr(det, "model_dump"):
        data = det.model_dump()
    elif isinstance(det, dict):
        data = det
    else:
        return {"class_name": str(det)}
    bbox = data.get("bbox") or {}
    return {
        "class_name": data.get("class_name", ""),
        "confidence": round(float(data.get("confidence", 0.0)), 3),
        "direction": data.get("direction"),
        "hit_count": int(data.get("hit_count", 0)),
        "risk": data.get("risk"),
        "track_id": data.get("track_id"),
        "route": data.get("route"),
        "effective_distance_zone": data.get("effective_distance_zone"),
        "route_reason": data.get("route_reason"),
        "bbox": {
            "x": round(float(bbox.get("x", 0.0)), 1),
            "y": round(float(bbox.get("y", 0.0)), 1),
            "w": round(float(bbox.get("w", 0.0)), 1),
            "h": round(float(bbox.get("h", 0.0)), 1),
        }
        if bbox
        else None,
    }


def _compact_surface(surf: Any) -> dict[str, Any]:
    if hasattr(surf, "model_dump"):
        data = surf.model_dump()
    elif isinstance(surf, dict):
        data = surf
    else:
        return {"class_name": str(surf)}
    centroid = data.get("centroid") or []
    return {
        "class_name": data.get("class_name", ""),
        "centroid": [round(float(v), 1) for v in centroid[:2]] if centroid else [],
    }


def _preview_rag_results(rag_results: Any) -> list[dict[str, Any]] | None:
    if not rag_results:
        return None
    if not isinstance(rag_results, list):
        return None
    preview: list[dict[str, Any]] = []
    for item in rag_results[:_RAG_RESULTS_MAX]:
        if not isinstance(item, dict):
            preview.append({"raw": str(item)[:200]})
            continue
        preview.append(
            {
                "content": _preview(
                    str(item.get("content") or item.get("page_content") or ""), 200
                ),
                "metadata": item.get("metadata"),
                "score": item.get("score"),
            }
        )
    if len(rag_results) > _RAG_RESULTS_MAX:
        preview.append({"truncated": f"+{len(rag_results) - _RAG_RESULTS_MAX} more"})
    return preview


def _resolve_stt_generation_mode(source: str, *, response_skipped: bool = False) -> str:
    if response_skipped or source == "stt-echo-detected":
        return "echo_skipped"
    if source.startswith("navigation-"):
        return "navigation_template"
    if source == "question-convenience-rag":
        return "rag_answer"
    if "llm" in source:
        return "llm_answer"
    if source in ("stt-template", "stt-bridge"):
        return "orch_langgraph"
    if source.endswith("-empty") or source.endswith("-error"):
        return "static_fallback"
    return "template_or_static"


def _resolve_cognitive_generation_mode(orch_result: dict[str, Any]) -> str:
    if orch_result.get("used_fast_lane"):
        return "fast_lane_template"
    if orch_result.get("used_static_fallback"):
        return "static_fallback"
    return "langgraph_l2_l3"


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
    risk_level: str | None = None,
    hit_count: int | None = None,
    track_id: str | None = None,
    inference_ms: float | None = None,
    detections: list[Any] | None = None,
    route: str = "reflex",
    effective_distance_zone: str = "near",
    route_reason: str = "",
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    debug: dict[str, Any] = {
        "path": "reflex",
        "alert_id": alert_id,
        "clip": clip,
        "direction": direction,
        "class_name": class_name,
        "distance": distance,
        "generation_mode": "reflex_prebaked_clip",
        "route": route,
        "effective_distance_zone": effective_distance_zone,
    }
    if route_reason:
        debug["route_reason"] = route_reason
    if risk_level:
        debug["risk_level"] = risk_level
    if hit_count is not None:
        debug["hit_count"] = hit_count
    if track_id:
        debug["track_id"] = track_id
    if inference_ms is not None:
        debug["inference_ms"] = round(float(inference_ms), 1)
    if detections:
        debug["detections_summary"] = [_compact_detection(det) for det in detections[:8]]
    if observability:
        for key in (
            "surface_episode",
            "surface_zone",
            "reset_reason",
            "stt_gate_blocked",
            "reflex_suppressed_by",
        ):
            val = observability.get(key)
            if val:
                debug[key] = val
    return debug


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
    detections: list[Any] | None = None,
    surfaces: list[Any] | None = None,
    risk_hint: str = "",
    inference_ms: float | None = None,
    is_departing: bool = False,
    departure_confirmed: bool = False,
    braille_direction: str = "",
    navigation_guidance: str = "",
    detected_classes_ko: list[str] | None = None,
    route: str = "cognitive",
    effective_distance_zone: str = "",
    route_reason: str = "",
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generation_mode = _resolve_cognitive_generation_mode(orch_result)
    used_fast_lane = bool(orch_result.get("used_fast_lane"))
    l1_risk = orch_result.get("risk_level") or risk_hint or ""

    debug: dict[str, Any] = {
        "path": "cognitive",
        "rag_query": rag_query,
        "rag_context": _preview(rag_context),
        "clock_direction": clock_direction or orch_result.get("clock_direction") or "",
        "distance_class": distance_class or orch_result.get("distance") or "",
        "object_ko": object_ko or orch_result.get("object_ko") or "",
        "llm_provider": llm_provider,
        "route": route,
        "effective_distance_zone": effective_distance_zone or distance_class or "",
        "used_fast_lane": used_fast_lane,
        "fast_lane_cache_key": orch_result.get("fast_lane_cache_key") or "",
        "generation_mode": generation_mode,
        "l1_risk_level": l1_risk,
        "pipeline_risk_hint": risk_hint,
        "l3_verified": bool(orch_result.get("verified", False)),
        "validation_errors": list(orch_result.get("validation_errors") or []),
        "used_static_fallback": bool(orch_result.get("used_static_fallback", False)),
        "retry_count": int(orch_result.get("retry_count", 0)),
        "response_text": guidance_text,
        "is_departing": is_departing,
        "is_departing_confirmed": bool(
            departure_confirmed or orch_result.get("is_departing_confirmed", False)
        ),
        "braille_direction": braille_direction or orch_result.get("braille_direction") or "",
    }
    if route_reason:
        debug["route_reason"] = route_reason
    if observability:
        for key in (
            "surface_episode",
            "surface_zone",
            "reset_reason",
            "stt_gate_blocked",
            "reflex_suppressed_by",
        ):
            val = observability.get(key)
            if val:
                debug[key] = val
    if inference_ms is not None:
        debug["inference_ms"] = round(float(inference_ms), 1)
    if detected_classes_ko:
        debug["detected_classes_ko"] = detected_classes_ko
    elif orch_result.get("detected_classes"):
        debug["detected_classes_ko"] = list(orch_result.get("detected_classes") or [])
    if navigation_guidance:
        debug["navigation_guidance"] = _preview(navigation_guidance)
    elif orch_result.get("navigation_guidance"):
        debug["navigation_guidance"] = _preview(str(orch_result.get("navigation_guidance")))
    if detections:
        debug["detections_summary"] = [_compact_detection(det) for det in detections[:8]]
    if surfaces:
        debug["surfaces_summary"] = [_compact_surface(surf) for surf in surfaces[:6]]
    l2_drafts = orch_result.get("l2_drafts")
    if l2_drafts:
        debug["l2_drafts"] = list(l2_drafts)
    if used_fast_lane or generation_mode == "static_fallback":
        debug["llm_text"] = None
    else:
        debug["llm_text"] = guidance_text
    return debug


def build_stt_pipeline_debug(
    *,
    stt_transcript: str,
    bridge_result: dict[str, Any],
    response_skipped: bool = False,
) -> dict[str, Any]:
    source = str(bridge_result.get("source") or "")
    guidance_text = str(bridge_result.get("guidance_text") or "")
    generation_mode = _resolve_stt_generation_mode(source, response_skipped=response_skipped)

    debug: dict[str, Any] = {
        "path": "stt",
        "stt_transcript": stt_transcript.strip(),
        "bridge_source": source,
        "generation_mode": generation_mode,
        "response_text": guidance_text,
        "response_skipped": response_skipped,
    }
    rag_query = bridge_result.get("rag_query")
    if rag_query:
        debug["rag_query"] = rag_query
    rag_results = bridge_result.get("rag_results")
    rag_preview = _preview_rag_results(rag_results)
    if rag_preview:
        debug["rag_results"] = rag_preview
    if (
        generation_mode == "llm_answer"
        or generation_mode == "rag_answer"
        or generation_mode == "orch_langgraph"
    ):
        debug["llm_text"] = guidance_text if guidance_text else None
    else:
        debug["llm_text"] = None
    if (
        generation_mode in ("navigation_template", "template_or_static", "static_fallback")
        and guidance_text
    ):
        debug["template_text"] = guidance_text
    if bridge_result.get("used_fallback_llm") is not None:
        debug["used_fallback_llm"] = bool(bridge_result.get("used_fallback_llm"))
    if response_skipped:
        debug["skip_reason"] = "stt_echo_detected"
    return debug
