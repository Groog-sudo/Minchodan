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
    assert debug["bridge_source"] == "navigation-setup-wakeup"


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
    )
    assert debug["generation_mode"] == "fast_lane_template"
    assert debug["llm_text"] is None
    assert debug["fast_lane_cache_key"] == "11시_차량_near_caution"


def test_build_reflex_pipeline_debug():
    debug = build_reflex_pipeline_debug(
        alert_id="high_obstacle",
        clip="reflex_clips/high_front.wav",
        class_name="car",
    )
    assert debug["path"] == "reflex"
    assert debug["clip"] == "reflex_clips/high_front.wav"


def test_serialize_pipeline_debug_roundtrip():
    raw = serialize_pipeline_debug({"path": "stt", "stt_transcript": "테스트"})
    assert raw is not None
    assert "테스트" in raw
