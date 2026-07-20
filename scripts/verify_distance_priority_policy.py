#!/usr/bin/env python3
"""Near/Medium/Far 우선순위 정책 통합 스모크 (Docker/로컬 FastAPI 환경).

실행:
  python scripts/verify_distance_priority_policy.py
"""

import asyncio
import logging
import os
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" ({detail})" if detail else ""
    logger.info("[%s] %s%s", status, name, suffix)
    return ok


async def main() -> int:
    from server.detection.config import get_detector
    from server.detection.consumer import DetectionConsumer
    from server.detection.distance_policy import evaluate_distance
    from server.detection.gates.reflex_gate import reflex_gate
    from server.detection.schemas import BBox, Detection, DetectionResult

    results: list[bool] = []
    frame_h, frame_w = 480.0, 640.0

    near_bbox = BBox(x=200.0, y=120.0, w=240.0, h=180.0)
    medium_bbox = BBox(x=220.0, y=160.0, w=200.0, h=120.0)
    far_bbox = BBox(x=300.0, y=200.0, w=40.0, h=40.0)

    for label, bbox in (("near", near_bbox), ("medium", medium_bbox), ("far", far_bbox)):
        pol = evaluate_distance(bbox, frame_w, frame_h)
        results.append(
            _check(
                f"policy zone={label}",
                pol.effective_distance_zone == label,
                f"route={pol.route}, reason={pol.route_reason}",
            )
        )

    def _det(bbox: BBox) -> Detection:
        pol = evaluate_distance(bbox, frame_w, frame_h)
        return Detection(
            class_name="car",
            confidence=0.9,
            bbox=bbox,
            track_id="T-0001",
            hit_count=4,
            direction="approaching",
            area_ratio=pol.area_ratio,
            bottom_ratio=pol.bottom_ratio,
            raw_distance_zone=pol.raw_distance_zone,
            effective_distance_zone=pol.effective_distance_zone,
            heuristic_distance_m=pol.heuristic_distance_m,
            distance_source=pol.distance_source,
            route=pol.route,
            route_reason=pol.route_reason,
            policy_version=pol.policy_version,
        )

    results.append(
        _check(
            "reflex_gate near",
            reflex_gate(_det(near_bbox), frame_height=frame_h, frame_width=frame_w) is not None,
        )
    )
    results.append(
        _check(
            "reflex_gate medium blocked",
            reflex_gate(_det(medium_bbox), frame_height=frame_h, frame_width=frame_w) is None,
        )
    )
    results.append(
        _check(
            "reflex_gate far blocked",
            reflex_gate(_det(far_bbox), frame_height=frame_h, frame_width=frame_w) is None,
        )
    )

    consumer = DetectionConsumer()
    frame = np.zeros((int(frame_h), int(frame_w), 3), dtype=np.uint8)
    results.append(
        _check(
            "consumer speech near blocked",
            not consumer._is_speech_worthy(_det(near_bbox), frame, "near", "low", False),
        )
    )
    results.append(
        _check(
            "consumer speech medium allowed",
            consumer._is_speech_worthy(_det(medium_bbox), frame, "medium", "low", False),
        )
    )
    results.append(
        _check(
            "consumer speech far blocked",
            not consumer._is_speech_worthy(_det(far_bbox), frame, "far", "low", False),
        )
    )

    logger.info("[RUN] YOLO live inference (track + synthetic frame)...")
    detector = get_detector()
    if not detector.load():
        results.append(_check("yolo model load", False, "weights missing"))
    else:
        results.append(_check("yolo model load", True, type(detector).__name__))
        white = np.zeros((480, 640, 3), dtype=np.uint8)
        white[150:400, 180:460] = 255
        t0 = time.perf_counter()
        dets = detector.predict(white)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        results.append(
            _check(
                "yolo predict completes",
                isinstance(dets, list),
                f"{len(dets)} detections, {elapsed_ms:.1f}ms",
            )
        )

    logger.info("[RUN] cognitive E2E gate (orchestrator mock)...")
    from unittest.mock import AsyncMock, MagicMock, patch

    import server.detection.consumer as consumer_module

    orch_calls: list[dict] = []

    async def _orch_capture(payload):
        orch_calls.append(payload)
        return {"guidance_text": "ok", "verified": True, "retry_count": 0}

    with (
        patch.object(consumer_module, "run_orchestrator", AsyncMock(side_effect=_orch_capture)),
        patch.object(consumer_module, "get_default_retriever", lambda: None),
        patch.object(
            consumer_module.realtime_tts,
            "synthesize_from_llm",
            AsyncMock(return_value=("dGVzdA==", 100.0)),
        ),
        patch.object(consumer_module.manager, "is_stt_active", lambda _d: False),
        patch.object(consumer_module.manager, "send_json", AsyncMock(return_value=True)),
        patch.object(consumer_module.manager, "send_bytes", AsyncMock(return_value=True)),
        patch.object(consumer_module.DetectionConsumer, "_broadcast_latency_event", AsyncMock()),
        patch.object(consumer_module.DetectionConsumer, "_schedule_log_persist", MagicMock()),
    ):
        medium_result = DetectionResult(
            event_id="smoke-medium",
            detections=[_det(medium_bbox)],
            surface=[],
            risk_hint="low",
            inference_ms=1.0,
        )
        near_result = DetectionResult(
            event_id="smoke-near",
            detections=[_det(near_bbox)],
            surface=[],
            risk_hint="low",
            inference_ms=1.0,
        )
        await consumer._send_cognitive_guide("smoke-dev", near_result, frame=frame)
        near_calls = len(orch_calls)
        await consumer._send_cognitive_guide("smoke-dev", medium_result, frame=frame)

    results.append(_check("cognitive E2E near skipped", near_calls == 0))
    results.append(_check("cognitive E2E medium invoked", len(orch_calls) == 1))

    passed = sum(results)
    total = len(results)
    logger.info("=" * 50)
    logger.info("SUMMARY: %d/%d checks passed", passed, total)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
