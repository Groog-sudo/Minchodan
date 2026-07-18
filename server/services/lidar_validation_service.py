import json
import sys

from server.db.connection import async_sessionmaker_factory
from server.db.models import LidarDistanceValidationSample, LidarFixedPointSample
from server.db.repositories import LidarDistanceValidationRepository, LidarFixedPointRepository
from server.detection import distance_policy
from server.detection.direction import bbox_area_ratio, estimate_distance
from server.detection.schemas import DistanceProbeReport, FixedPointProbeReport

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
        # 2026-07-19 (거리 정책 SSOT 2단계, 온디맨드 유지 결정): LiDAR 실측이 있으면
        # 자문용 구역도 함께 계산해 저장한다. 실시간 반사/인지 라우팅에는 관여하지
        # 않고(distance_policy.zone_from_lidar_meters docstring 참조), 캘리브레이션
        # 비교(scripts/analyze_lidar_validation.py 구역 혼동 행렬)에만 쓰인다.
        lidar_zone = (
            distance_policy.zone_from_lidar_meters(sample.lidar_meters)
            if sample.lidar_meters is not None
            else None
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
                lidar_distance_zone=lidar_zone,
            )
        )

    async with async_sessionmaker_factory() as session:
        repo = LidarDistanceValidationRepository(session)
        return await repo.create_many(rows)


async def persist_fixed_point_samples(
    report: FixedPointProbeReport, device_id: int | None
) -> list[LidarFixedPointSample]:
    """거리측정 모드 고정 3지점(중앙/전방 하단/발밑) 캡처 1건(지점 여러 개)을 저장한다.

    persist_distance_probe_samples와 달리 YOLO 탐지 객체·휴리스틱 비교가 필요 없으므로
    클라이언트가 이미 보유한 probeDepth() 결과를 그대로 저장한다.
    """
    rows = [
        LidarFixedPointSample(
            event_id=report.event_id,
            device_id=device_id,
            point_label=sample.point_label,
            x=sample.x,
            y=sample.y,
            lidar_meters=sample.lidar_meters,
            axial_meters=sample.axial_meters,
            lidar_sample_count=sample.lidar_sample_count,
            lidar_accuracy=sample.lidar_accuracy,
            lidar_quality=sample.lidar_quality,
            lidar_calibrated=sample.lidar_calibrated,
        )
        for sample in report.samples
    ]

    async with async_sessionmaker_factory() as session:
        repo = LidarFixedPointRepository(session)
        return await repo.create_many(rows)
