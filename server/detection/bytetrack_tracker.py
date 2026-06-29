import json
import logging
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.bus.redis_client import RedisBus
from server.detection.schemas import BBox, Detection

logger = logging.getLogger(__name__)

SPEED_THRESHOLD = 0.5


class ByteTrackTracker:
    """ByteTrack 기반 track_id 부여 및 속도/방향 계산 래퍼.

    실제 track_id는 ultralytics YOLO `model.track()`이 부여하며,
    본 클래스는 Redis 컨텍스트를 활용해 접근/이탈 속도를 산출한다.
    """

    async def update(
        self,
        detections: list[Detection],
        redis_bus: RedisBus,
    ) -> list[Detection]:
        updated: list[Detection] = []
        for det in detections:
            try:
                if det.track_id is None:
                    updated.append(det.model_copy(update={"speed": 0.0, "direction": "unknown"}))
                    continue

                prev = await redis_bus.get_track_context(det.track_id)
                speed, direction = self._compute_motion(prev, det.bbox)

                await redis_bus.set_track_context(
                    det.track_id,
                    {
                        "last_pos": json.dumps(det.bbox.model_dump()),
                        "speed": str(speed),
                        "direction": direction,
                        "class_name": det.class_name,
                        "updated_at": str(time.time()),
                    },
                )
                updated.append(det.model_copy(update={"speed": speed, "direction": direction}))
            except Exception as e:
                logger.warning(f"[ByteTrackTracker] track 업데이트 실패: {e}")
                updated.append(det.model_copy(update={"speed": 0.0, "direction": "unknown"}))
        return updated

    @staticmethod
    def _compute_motion(prev: dict, bbox: BBox) -> tuple[float, str]:
        if not prev or "last_pos" not in prev:
            return 0.0, "unknown"

        try:
            last = json.loads(prev["last_pos"])
            last_bottom = last["y"] + last["h"]
            current_bottom = bbox.y + bbox.h
            dt = 1.0
            if "updated_at" in prev:
                dt = max(time.time() - float(prev["updated_at"]), 0.001)
            speed = (current_bottom - last_bottom) / dt
            if speed > SPEED_THRESHOLD:
                direction = "approaching"
            elif speed < -SPEED_THRESHOLD:
                direction = "departing"
            else:
                direction = "unknown"
            return speed, direction
        except Exception as e:
            logger.warning(f"[ByteTrackTracker] motion 계산 실패: {e}")
            return 0.0, "unknown"
