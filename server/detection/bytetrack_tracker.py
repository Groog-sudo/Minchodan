import json
import logging
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.bus.redis_client import RedisBus
from server.detection import distance_policy
from server.detection.schemas import BBox, Detection

logger = logging.getLogger(__name__)

SPEED_THRESHOLD = 0.5

# P0-3 (2026-07-17): Approach-Lost 윈도우. 동일 track_id가 이 시간(초) 이내에 재탐지되면
# 이전 hit_count가 MIN_HIT_COUNT를 충족했던 객체로 복원해 즉시 재발화 (S4 해소).
# 보행 속도 1m/s 기준 1초면 가려짐/순간 누락 후 재등장을 잡기 충분.
APPROACH_LOST_WINDOW_S = float(os.getenv("APPROACH_LOST_WINDOW_S", "1.0"))
# Approach-Lot 판정에 필요한 직전 hit_count 하한 (reflex_gate MIN_HIT_COUNT와 SSOT).
APPROACH_LOST_MIN_PREV_HIT = int(os.getenv("APPROACH_LOST_MIN_PREV_HIT", "3"))


class ByteTrackTracker:
    """ByteTrack 기반 track_id 부여 및 속도/방향 계산 래퍼.

    실제 track_id는 ultralytics YOLO `model.track()`이 부여하며,
    본 클래스는 Redis 컨텍스트를 활용해 접근/이탈 속도를 산출한다.

    P0-3 (2026-07-17): Approach-Lost 보정 추가. 동일 track_id가 1초 이내 재탐지되고
    이전 hit_count가 MIN_HIT_COUNT를 충족했으면 reacquired=True로 복원해 reflex_gate가
    MIN_HIT_COUNT 재충족 대기 없이 즉시 발동하도록 한다.
    """

    async def update(
        self,
        detections: list[Detection],
        redis_bus: RedisBus,
        frame_width: float = 0.0,
        frame_height: float = 0.0,
    ) -> list[Detection]:
        """탐지 목록에 track_id 연속성 정보와 거리 정책 SSOT 평가 결과를 부착한다.

        2026-07-18: 거리 정책 SSOT(distance_policy.py) 도입 - track별 이전 구역
        (effective_zone)을 Redis 트랙 컨텍스트에 함께 저장해 히스테리시스를 적용한다.
        frame_width/frame_height가 0이면(호출부가 아직 넘기지 않는 레거시 경로) 거리
        평가를 건너뛰고 Detection의 기본값(far/cognitive)을 그대로 둔다.
        """
        updated: list[Detection] = []
        for det in detections:
            try:
                if det.track_id is None:
                    # track_id가 없으면(Mock 등) 연속성을 확인할 수 없으므로 단발성(hit_count=1)으로 취급
                    policy_update = self._evaluate_policy(det, frame_width, frame_height, None)
                    updated.append(
                        det.model_copy(
                            update={
                                "speed": 0.0,
                                "direction": "unknown",
                                "hit_count": 1,
                                **policy_update,
                            }
                        )
                    )
                    continue

                prev = await redis_bus.get_track_context(det.track_id)
                speed, direction = self._compute_motion(prev, det.bbox)
                hit_count, reacquired = self._compute_hit_count_with_reacquire(prev)
                prev_zone = prev.get("effective_zone") if prev else None
                policy_update = self._evaluate_policy(det, frame_width, frame_height, prev_zone)

                await redis_bus.set_track_context(
                    det.track_id,
                    {
                        "last_pos": json.dumps(det.bbox.model_dump()),
                        "speed": str(speed),
                        "direction": direction,
                        "class_name": det.class_name,
                        "updated_at": str(time.time()),
                        "hit_count": str(hit_count),
                        "effective_zone": policy_update.get("effective_distance_zone", "far"),
                    },
                )
                updated.append(
                    det.model_copy(
                        update={
                            "speed": speed,
                            "direction": direction,
                            "hit_count": hit_count,
                            "reacquired": reacquired,
                            **policy_update,
                        }
                    )
                )
            except Exception as e:
                logger.warning(f"[ByteTrackTracker] track 업데이트 실패: {e}")
                updated.append(
                    det.model_copy(update={"speed": 0.0, "direction": "unknown", "hit_count": 1})
                )
        return updated

    @staticmethod
    def _evaluate_policy(
        det: Detection,
        frame_width: float,
        frame_height: float,
        prev_zone: str | None,
    ) -> dict:
        """distance_policy.evaluate_distance()를 실행해 Detection 갱신용 dict를 만든다.

        frame_width/height가 없으면(0 이하) 평가할 수 없으므로 빈 dict를 반환해
        Detection의 기본값을 그대로 유지한다(방어적 코딩).
        """
        if frame_width <= 0 or frame_height <= 0:
            return {}
        valid_prev_zone = prev_zone if prev_zone in ("near", "medium", "far") else None
        result = distance_policy.evaluate_distance(
            det.bbox, frame_width, frame_height, prev_zone=valid_prev_zone
        )
        return {
            "area_ratio": result.area_ratio,
            "bottom_ratio": result.bottom_ratio,
            "raw_distance_zone": result.raw_distance_zone,
            "effective_distance_zone": result.effective_distance_zone,
            "heuristic_distance_m": result.heuristic_distance_m,
            "distance_source": result.distance_source,
            "route": result.route,
            "route_reason": result.route_reason,
            "policy_version": result.policy_version,
        }

    @staticmethod
    def _compute_hit_count(prev: dict) -> int:
        """동일 track_id가 이전 컨텍스트에도 존재했다면 +1, 아니면(신규 track) 1부터 시작한다."""
        if not prev or "hit_count" not in prev:
            return 1
        try:
            return int(prev["hit_count"]) + 1
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _compute_hit_count_with_reacquire(prev: dict) -> tuple[int, bool]:
        """P0-3: hit_count 계산 + Approach-Lost 재획득 판정.

        # [면접 대비 주석]
        # Approach-Lost 정책의 핵심: "접근 중이던 객체가 1초 이내 가려짐/누락 후 재등장하면
        # MIN_HIT_COUNT(3) 재충족을 기다리지 않고 즉시 반사 경보".
        # 설계 의유: 보행 중 짧은 가려짐(지나가는行人·표지판)으로 track이 끊기면 hit_count가
        # 1부터 재시작해 3프레임(약 0.3s)을 다시 기다려야 하는데, 이 0.3초가 1m/s 보행에서
        # 30cm 추가 접근을 의미해 안전 마진을 깎음. 직전 hit_count가 이미 3 이상이었으면
        # reacquired=True로 복원해 지연을 제거.
        # 반환: (hit_count, reacquired). reacquired=True면 reflex_gate가 MIN_HIT_COUNT 검사 건너뜀.
        """
        if not prev or "hit_count" not in prev:
            return 1, False
        try:
            prev_hit = int(prev["hit_count"])
        except (TypeError, ValueError):
            return 1, False

        hit_count = prev_hit + 1
        reacquired = False
        # Approach-Lot: 직전 hit_count가 MIN 이상이고, 마지막 관측이 윈도우 이내
        if prev_hit >= APPROACH_LOST_MIN_PREV_HIT and "updated_at" in prev:
            try:
                last_seen = float(prev["updated_at"])
                gap = time.time() - last_seen
                if 0.0 < gap <= APPROACH_LOST_WINDOW_S:
                    reacquired = True
                    # hit_count는 이미 충족 상태이므로 정상 누적 유지 (감소시키지 않음)
            except (TypeError, ValueError):
                pass
        return hit_count, reacquired

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
