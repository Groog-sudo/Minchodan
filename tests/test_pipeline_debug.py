import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.services.pipeline_debug_builder import (
    build_cognitive_pipeline_debug,
    build_reflex_pipeline_debug,
    build_stt_pipeline_debug,
    serialize_pipeline_debug,
)


def test_build_stt_pipeline_debug_with_llm():
    debug = build_stt_pipeline_debug(
        stt_transcript="가까운 지하철역이 어디야",
        bridge_result={
            "guidance_text": "가장 가까운 지하철역은 서울역입니다.",
            "source": "question-llm",
            "used_fallback_llm": False,
        },
    )
    assert debug["path"] == "stt"
    assert debug["stt_transcript"] == "가까운 지하철역이 어디야"
    assert debug["bridge_source"] == "question-llm"
    assert debug["generation_mode"] == "llm_answer"
    assert debug["llm_text"] == "가장 가까운 지하철역은 서울역입니다."


def test_build_stt_pipeline_debug_navigation_template():
    debug = build_stt_pipeline_debug(
        stt_transcript="길댕아 길찾아줘",
        bridge_result={
            "guidance_text": "네비게이션 기능을 시작합니다.",
            "source": "navigation-setup-wakeup",
            "used_fallback_llm": True,
        },
    )
    assert debug["llm_text"] is None
    assert debug["generation_mode"] == "navigation_template"
    assert debug["template_text"] == "네비게이션 기능을 시작합니다."
    assert debug["bridge_source"] == "navigation-setup-wakeup"


def test_build_stt_pipeline_debug_echo_skipped():
    debug = build_stt_pipeline_debug(
        stt_transcript="길찾아줘 또는 물어볼게 중 하나로 다시 말씀해주세요",
        bridge_result={
            "guidance_text": "",
            "source": "stt-echo-detected",
            "used_fallback_llm": True,
        },
        response_skipped=True,
    )
    assert debug["generation_mode"] == "echo_skipped"
    assert debug["response_skipped"] is True
    assert debug["skip_reason"] == "stt_echo_detected"


def test_build_cognitive_fast_lane():
    debug = build_cognitive_pipeline_debug(
        guidance_text="11시 방향 차량 주의하세요",
        rag_query="car",
        rag_context="차량 접근 시 주의",
        orch_result={
            "used_fast_lane": True,
            "fast_lane_cache_key": "11시_차량_near_caution",
            "verified": True,
            "validation_errors": [],
            "retry_count": 0,
        },
        clock_direction="11시",
        distance_class="near",
        object_ko="차량",
        llm_provider="OLLAMA",
        risk_hint="high",
        inference_ms=42.5,
        detections=[
            {
                "class_name": "car",
                "confidence": 0.91,
                "hit_count": 4,
                "direction": "front",
                "bbox": {"x": 1, "y": 2, "w": 3, "h": 4},
            }
        ],
        surfaces=[{"class_name": "roadway", "centroid": [120.0, 340.0]}],
    )
    assert debug["generation_mode"] == "fast_lane_template"
    assert debug["llm_text"] is None
    assert debug["fast_lane_cache_key"] == "11시_차량_near_caution"
    assert debug["detections_summary"][0]["class_name"] == "car"
    assert debug["surfaces_summary"][0]["class_name"] == "roadway"
    assert debug["inference_ms"] == 42.5


def test_build_cognitive_l2_drafts():
    debug = build_cognitive_pipeline_debug(
        guidance_text="전방 주의, 천천히 멈추세요",
        rag_query="scooter",
        rag_context="주의",
        orch_result={
            "risk_level": "mid",
            "l2_drafts": ["너무 긴 안내문이 거절되었습니다"],
            "verified": False,
            "used_static_fallback": True,
            "validation_errors": ["길이 초과"],
            "retry_count": 2,
        },
        llm_provider="OLLAMA",
    )
    assert debug["l1_risk_level"] == "mid"
    assert debug["generation_mode"] == "static_fallback"
    assert debug["l2_drafts"] == ["너무 긴 안내문이 거절되었습니다"]


def test_build_reflex_pipeline_debug():
    debug = build_reflex_pipeline_debug(
        alert_id="high_obstacle",
        clip="reflex_clips/high_front.wav",
        class_name="car",
        risk_level="high",
        hit_count=3,
        track_id="t-1",
        inference_ms=18.2,
        route="reflex",
        effective_distance_zone="near",
        route_reason="zone_near",
    )
    assert debug["path"] == "reflex"
    assert debug["clip"] == "reflex_clips/high_front.wav"
    assert debug["hit_count"] == 3
    assert debug["generation_mode"] == "reflex_prebaked_clip"
    assert debug["route"] == "reflex"
    assert debug["effective_distance_zone"] == "near"
    assert debug["route_reason"] == "zone_near"


def test_build_cognitive_pipeline_debug_route_fields():
    debug = build_cognitive_pipeline_debug(
        guidance_text="전방 주의",
        rag_query="car",
        rag_context="주의",
        orch_result={"verified": True, "validation_errors": [], "retry_count": 0},
        distance_class="medium",
        route="cognitive",
        effective_distance_zone="medium",
        route_reason="zone_medium",
    )
    assert debug["route"] == "cognitive"
    assert debug["effective_distance_zone"] == "medium"
    assert debug["route_reason"] == "zone_medium"


def test_serialize_pipeline_debug_roundtrip():
    raw = serialize_pipeline_debug({"path": "stt", "stt_transcript": "테스트"})
    assert raw is not None
    assert "테스트" in raw
