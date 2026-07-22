"""Near/Medium/Far 우선순위 정책 통합 검증 (단위+E2E+파이프라인 연동)."""

import sys
from unittest.mock import AsyncMock, MagicMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pytest

from server.detection import BBox, Detection, DetectionResult, YoloDetector
from server.detection.consumer import DetectionConsumer
from server.detection.distance_policy import evaluate_distance
from server.detection.gates.reflex_gate import reflex_gate
from server.services.pipeline_debug_builder import build_reflex_pipeline_debug


def _policy_detection(
    bbox: BBox,
    *,
    frame_width: float = 640.0,
    frame_height: float = 480.0,
    confidence: float = 0.9,
    hit_count: int = 4,
    direction: str = "approaching",
    track_id: str = "T-0001",
) -> Detection:
    """distance_policy SSOT 필드를 부착한 Detection (tracker 경로와 동일)."""
    policy = evaluate_distance(bbox, frame_width, frame_height)
    return Detection(
        class_name="car",
        confidence=confidence,
        bbox=bbox,
        track_id=track_id,
        hit_count=hit_count,
        direction=direction,
        area_ratio=policy.area_ratio,
        bottom_ratio=policy.bottom_ratio,
        raw_distance_zone=policy.raw_distance_zone,
        effective_distance_zone=policy.effective_distance_zone,
        heuristic_distance_m=policy.heuristic_distance_m,
        distance_source=policy.distance_source,
        route=policy.route,
        route_reason=policy.route_reason,
        policy_version=policy.policy_version,
    )


class TestYoloTrackFallback:
    """YoloDetector track() 실패 시 predict() 폴백."""

    def test_track_fallback_predicate(self):
        assert YoloDetector._track_fallback_to_predict(Exception("lap module not found"))
        assert YoloDetector._track_fallback_to_predict(
            AttributeError("'Conv' object has no attribute 'bn'")
        )
        assert not YoloDetector._track_fallback_to_predict(RuntimeError("unexpected"))

    def test_conv_bn_error_falls_back_to_predict(self):
        det = YoloDetector(weights_path="server/models/yolo26n/object_detection.pt")
        mock_result = MagicMock()
        mock_result.boxes = None

        mock_model = MagicMock()
        mock_model.track.side_effect = AttributeError("'Conv' object has no attribute 'bn'")
        mock_model.predict.return_value = [mock_result]
        det.model = mock_model

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        assert det.predict(frame) == []
        mock_model.track.assert_called_once()
        mock_model.predict.assert_called_once()

    def test_lap_error_falls_back_to_predict(self):
        det = YoloDetector(weights_path="server/models/yolo26n/object_detection.pt")
        mock_result = MagicMock()
        mock_result.boxes = None

        mock_model = MagicMock()
        mock_model.track.side_effect = RuntimeError("No module named 'lap'")
        mock_model.predict.return_value = [mock_result]
        det.model = mock_model

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        assert det.predict(frame) == []
        mock_model.predict.assert_called_once()


class TestDistancePolicyReflexGateChain:
    """distance_policy -> reflex_gate 불변식."""

    def test_near_triggers_reflex_medium_far_do_not(self):
        frame_w, frame_h = 640.0, 480.0
        near_bbox = BBox(x=200.0, y=120.0, w=240.0, h=180.0)
        medium_bbox = BBox(x=220.0, y=160.0, w=200.0, h=120.0)
        far_bbox = BBox(x=300.0, y=200.0, w=40.0, h=40.0)

        near_det = _policy_detection(near_bbox, frame_width=frame_w, frame_height=frame_h)
        medium_det = _policy_detection(medium_bbox, frame_width=frame_w, frame_height=frame_h)
        far_det = _policy_detection(far_bbox, frame_width=frame_w, frame_height=frame_h)

        assert near_det.effective_distance_zone == "near"
        assert near_det.route == "reflex"
        assert medium_det.effective_distance_zone == "medium"
        assert medium_det.route == "cognitive"
        assert far_det.effective_distance_zone == "far"

        assert reflex_gate(near_det, frame_height=frame_h, frame_width=frame_w) is not None
        assert reflex_gate(medium_det, frame_height=frame_h, frame_width=frame_w) is None
        assert reflex_gate(far_det, frame_height=frame_h, frame_width=frame_w) is None


class TestCognitiveGuideDistancePriorityE2E:
    """DetectionConsumer._send_cognitive_guide E2E (near 차단 / medium 허용 / far 차단)."""

    @staticmethod
    def _front_medium_bbox() -> BBox:
        return BBox(x=220.0, y=160.0, w=200.0, h=120.0)

    @staticmethod
    def _front_near_bbox() -> BBox:
        return BBox(x=200.0, y=120.0, w=240.0, h=180.0)

    @pytest.mark.asyncio
    async def test_near_skips_orchestrator_and_tts(self, monkeypatch):
        import server.detection.consumer as consumer_module

        orch_mock = AsyncMock(return_value={"guidance_text": "should-not-run"})
        tts_mock = AsyncMock(return_value=("audio", 1000.0))
        monkeypatch.setattr(consumer_module, "run_orchestrator", orch_mock)
        monkeypatch.setattr(consumer_module.realtime_tts, "synthesize_from_llm", tts_mock)
        monkeypatch.setattr(consumer_module.manager, "is_stt_active", lambda _device_id: False)

        consumer = DetectionConsumer()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        det = _policy_detection(self._front_near_bbox(), direction="approaching")
        result = DetectionResult(
            event_id="evt-near",
            detections=[det],
            surface=[],
            risk_hint="low",
            inference_ms=1.0,
        )

        await consumer._send_cognitive_guide("dev-near", result, frame=frame)

        orch_mock.assert_not_awaited()
        tts_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_medium_front_approaching_reaches_orchestrator(self, monkeypatch):
        import server.detection.consumer as consumer_module

        orch_mock = AsyncMock(
            return_value={
                "guidance_text": "전방 주의",
                "verified": True,
                "retry_count": 0,
                "used_fast_lane": False,
            }
        )
        tts_mock = AsyncMock(return_value=("dGVzdA==", 500.0))
        send_mock = AsyncMock(return_value=True)
        broadcast_mock = AsyncMock()
        log_mock = MagicMock()
        monkeypatch.setattr(consumer_module, "run_orchestrator", orch_mock)
        monkeypatch.setattr(consumer_module, "get_default_retriever", lambda: None)
        monkeypatch.setattr(consumer_module.realtime_tts, "synthesize_from_llm", tts_mock)
        monkeypatch.setattr(consumer_module.manager, "is_stt_active", lambda _device_id: False)
        monkeypatch.setattr(consumer_module.manager, "send_json", send_mock)
        monkeypatch.setattr(consumer_module.manager, "send_bytes", AsyncMock(return_value=True))
        monkeypatch.setattr(
            consumer_module.DetectionConsumer, "_broadcast_latency_event", broadcast_mock
        )
        monkeypatch.setattr(consumer_module.DetectionConsumer, "_schedule_log_persist", log_mock)

        consumer = DetectionConsumer()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        det = _policy_detection(self._front_medium_bbox(), direction="approaching")
        result = DetectionResult(
            event_id="evt-medium",
            detections=[det],
            surface=[],
            risk_hint="low",
            inference_ms=1.0,
        )

        await consumer._send_cognitive_guide("dev-medium", result, frame=frame)

        orch_mock.assert_awaited_once()
        tts_mock.assert_awaited_once()
        send_mock.assert_awaited()

    @pytest.mark.asyncio
    async def test_far_skips_orchestrator_even_when_approaching(self, monkeypatch):
        import server.detection.consumer as consumer_module

        orch_mock = AsyncMock(return_value={"guidance_text": "should-not-run"})
        monkeypatch.setattr(consumer_module, "run_orchestrator", orch_mock)
        monkeypatch.setattr(consumer_module.manager, "is_stt_active", lambda _device_id: False)

        consumer = DetectionConsumer()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        det = _policy_detection(BBox(x=300.0, y=200.0, w=40.0, h=40.0), direction="approaching")
        result = DetectionResult(
            event_id="evt-far",
            detections=[det],
            surface=[],
            risk_hint="low",
            inference_ms=1.0,
        )

        await consumer._send_cognitive_guide("dev-far", result, frame=frame)

        orch_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reflex_debug_includes_route_fields(self, monkeypatch):
        import server.detection.consumer as consumer_module

        send_mock = AsyncMock(return_value=True)
        should_emit_mock = AsyncMock(return_value=True)
        mark_reflex_mock = AsyncMock()
        log_mock = MagicMock()
        monkeypatch.setattr(consumer_module.manager, "send_json", send_mock)
        monkeypatch.setattr(
            consumer_module.Alert_suppressor, "should_emit_reflex", should_emit_mock
        )
        monkeypatch.setattr(consumer_module.Alert_suppressor, "mark_reflex_sent", mark_reflex_mock)
        monkeypatch.setattr(consumer_module.DetectionConsumer, "_schedule_log_persist", log_mock)

        consumer = DetectionConsumer()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        det = _policy_detection(BBox(x=200.0, y=120.0, w=240.0, h=180.0))
        from server.detection.schemas import ReflexAlert

        alert = ReflexAlert(
            event_id="evt-reflex",
            alert_id="high_obstacle",
            direction="front",
            clip="reflex_clips/high_front.wav",
            ts=0.0,
            track_id=det.track_id,
            class_name="car",
            hit_count=4,
            distance_band="near",
        )
        await consumer._send_reflex_alert("dev-reflex", alert, detections=[det], frame=frame)

        assert log_mock.called
        pipeline_debug = log_mock.call_args.kwargs["pipeline_debug"]
        assert pipeline_debug["route"] == "reflex"
        assert pipeline_debug["effective_distance_zone"] == "near"
        assert pipeline_debug.get("route_reason")


def test_build_reflex_pipeline_debug_route_contract():
    debug = build_reflex_pipeline_debug(
        alert_id="high_obstacle",
        clip="reflex_clips/high_front.wav",
        route="reflex",
        effective_distance_zone="near",
        route_reason="zone_near",
    )
    assert debug["route"] == "reflex"
    assert debug["effective_distance_zone"] == "near"
    assert debug["route_reason"] == "zone_near"
