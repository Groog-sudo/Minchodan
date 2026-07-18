import json
import sys

from server.db.connection import async_sessionmaker_factory
from server.db.models import LidarDistanceValidationSample
from server.db.repositories import LidarDistanceValidationRepository
from server.detection.direction import bbox_area_ratio, estimate_distance
from server.detection.schemas import DistanceProbeReport

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 클라이언트 depthProbe.ts의 makePreviewUri()가 640x640 정사각형으로 고정 인코딩한
# 정지 프레임을 서버가 그대로 디코딩하므로, 이 검증 경로에서는 실제 frame.shape 대신
# 고정값을 쓴다(일반 탐지 경로의 estimate_distance(frame.shape[1], frame.shape[0], ...)
# 호출과 달리, 여기서는 원본 프레임에 접근하지 않고 클라이언트가 되돌려 받은 bbox
# 좌표만으로 휴리스틱을 재계산하기 때문).
_PROBE_FRAME_SIZE = 640.0


async def persist_distance_probe_samples(
    report: DistanceProbeReport, device_id: int | None
) -> list[LidarDistanceValidationSample]:
    """LiDAR 검증 캡처 1건(bbox 여러 개)을 저장한다.

    FastAPI Depends(get_db) 요청 컨텍스트 밖(ws_router의 background task)에서 호출되므로
    persist_detection_guidance_log와 동일하게 세션을 직접 열고 닫는다. 반사/인지 경로의
    실시간 응답을 막지 않도록 호출부가 background task로 감싸고 예외를 흡수해야 한다.
    """
    rows: list[LidarDistanceValidationSample] = []
    for sample in report.samples:
        area_ratio = bbox_area_ratio(sample.bbox, _PROBE_FRAME_SIZE, _PROBE_FRAME_SIZE)
        distance_class = estimate_distance(
            sample.bbox, _PROBE_FRAME_SIZE, _PROBE_FRAME_SIZE, sample.class_name
        )
        rows.append(
            LidarDistanceValidationSample(
                event_id=report.event_id,
                device_id=device_id,
                class_name=sample.class_name,
                confidence=sample.confidence,
                bbox_json=json.dumps(sample.bbox.model_dump(), ensure_ascii=False),
                lidar_meters=sample.lidar_meters,
                lidar_sample_count=sample.lidar_sample_count,
                lidar_accuracy=sample.lidar_accuracy,
                lidar_quality=sample.lidar_quality,
                lidar_calibrated=sample.lidar_calibrated,
                heuristic_distance_class=distance_class,
                heuristic_area_ratio=area_ratio,
            )
        )

    async with async_sessionmaker_factory() as session:
        repo = LidarDistanceValidationRepository(session)
        return await repo.create_many(rows)
