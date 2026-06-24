# SKILL 3 상세 구현 — YOLO 장애물 탐지 + ByteTrack + Risk Gate

이 문서는 `yolo-obstacle-detection` 스킬의 완전한 구현 코드와 알고리즘을 담고 있다.

---

## 1. 전체 파이프라인 흐름도

```
프레임 수신 (640×640 BGR)
    │
    ▼
[3-1] YOLO 모델 로딩 (싱글턴)
    │
    ▼
[3-3] 이미지 전처리 (패스스루)
    │
    ▼
[3-4] model.predict(frame, conf=0.4)
    │
    ▼
[3-5~3-8] 탐지 결과 파싱  Detection 리스트
    │
    ▼
[3-9~3-11] ByteTrack 추적  Track ID 부여
    │
    ▼
[3-12~3-13] Redis 컨텍스트 버퍼 업데이트 + 속도/방향 계산
    │
    ▼
[3-14~3-16] Risk Gate 위험도 분류
    │
    ├── high  즉시 TTS ("전방 차량 접근, 멈추세요")
    └── mid/low  Redis Streams "risk.events" 발행
    │
    ▼
[3-17] 최종 DetectionResult JSON 반환
```

---

## 2. 완전한 구현 코드

### 2.1 설정 파일 (`app/config.py`)

```python
from pydantic_settings import BaseSettings

class DetectionConfig(BaseSettings):
    # YOLO 설정
    YOLO_MODEL_PATH: str = "models/det_weights.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.4
    YOLO_DEVICE: str = "cuda:0"  # "cpu" 로 폴백 가능
    YOLO_HALF_PRECISION: bool = True  # FP16 (GPU 전용)

    # ByteTrack 설정
    BYTETRACK_TRACK_THRESH: float = 0.5
    BYTETRACK_TRACK_BUFFER: int = 30  # 프레임 수
    BYTETRACK_MATCH_THRESH: float = 0.8

    # Risk Gate 설정
    HIGH_RISK_CLASSES: list = ["car", "truck", "bus", "motorcycle"]
    MID_RISK_CLASSES: list = ["kickboard", "stair", "bollard", "bicycle"]
    HIGH_RISK_SPEED_THRESHOLD: float = 1.5  # px/frame 기준

    # Redis 설정
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CONTEXT_TTL_SECONDS: int = 30  # 컨텍스트 버퍼 TTL

    # 스트림 설정
    RISK_EVENTS_STREAM: str = "risk.events"
    TTS_URGENT_CHANNEL: str = "tts.urgent"

    class Config:
        env_prefix = "DETECT_"
```

### 2.2 Pydantic 스키마 (`app/detection/detection_models.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class RiskLevel(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"

class Direction(str, Enum):
    APPROACHING = "approaching"
    DEPARTING = "departing"
    UNKNOWN = "unknown"

class BBox(BaseModel):
    """바운딩 박스 (x, y는 좌상단 좌표, w/h는 너비/높이)"""
    x: float = Field(..., description="좌상단 x좌표 (px)")
    y: float = Field(..., description="좌상단 y좌표 (px)")
    w: float = Field(..., description="너비 (px)")
    h: float = Field(..., description="높이 (px)")

    @property
    def center(self) -> tuple:
        return (self.x + self.w / 2, self.y + self.h / 2)

    @property
    def area(self) -> float:
        return self.w * self.h

class Detection(BaseModel):
    """단일 탐지 결과"""
    class_name: str = Field(..., description="탐지된 클래스명 (예: kickboard)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 0~1")
    bbox: BBox
    track_id: Optional[str] = Field(None, description="ByteTrack ID (예: T-0023)")
    speed: Optional[float] = Field(None, ge=0.0, description="이동 속도 (px/s)")
    direction: Optional[Direction] = Direction.UNKNOWN
    risk: Optional[RiskLevel] = None

class DetectionResult(BaseModel):
    """프레임 단위 탐지 결과 전체"""
    frame_id: str
    timestamp: float
    detections: List[Detection]
    inference_ms: float = Field(..., description="YOLO 추론 소요 시간 (ms)")
    total_detections: int = 0

    def model_post_init(self, __context):
        self.total_detections = len(self.detections)
```

### 2.3 YOLO 탐지기 (`app/detection/yolo_detector.py`)

```python
"""
3-1 ~ 3-8: YOLO 모델 로딩, 추론 실행, 탐지 결과 파싱
"""
import time
import logging
from typing import List, Optional
import numpy as np

from ultralytics import YOLO
from server.api.config import DetectionConfig
from server.detection.detection_models import Detection, BBox, DetectionResult

logger = logging.getLogger(__name__)

class YOLODetector:
    """YOLO26 기반 장애물 탐지기 — 서버 수명 주기 동안 싱글턴"""

    _instance: Optional["YOLODetector"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: DetectionConfig = None):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.config = config or DetectionConfig()

        # [3-1] 모델 로딩 (서버 시작 시 1회)
        try:
            self.model = YOLO(self.config.YOLO_MODEL_PATH)
            logger.info(f"YOLO 모델 로딩 완료: {self.config.YOLO_MODEL_PATH}")
        except Exception as e:
            logger.warning(f"커스텀 모델 로딩 실패, 기본 모델 다운로드: {e}")
            self.model = YOLO("det_weights.pt")  # 자동 다운로드 폴백

        # [3-2] 커스텀 클래스 확인
        self.class_names = self.model.names
        logger.info(f"등록된 클래스 목록: {self.class_names}")

        # 커스텀 클래스 존재 여부 체크
        required_custom = ["kickboard", "bollard", "stair"]
        registered = set(self.class_names.values())
        for cls_name in required_custom:
            if cls_name not in registered:
                logger.warning(f"커스텀 클래스 '{cls_name}'이 모델에 없음 — 기본 COCO 클래스만 사용")

    def detect(self, frame: np.ndarray, frame_id: str = "") -> DetectionResult:
        """
        단일 프레임에 대해 YOLO 추론 수행

        Args:
            frame: 640×640 BGR numpy 배열
            frame_id: 프레임 고유 식별자

        Returns:
            DetectionResult: 탐지 결과 (detections 리스트 + 추론 시간)
        """
        # [3-3] 이미지 전처리: 2단계에서 수신한 frame 그대로 사용
        if frame is None:
            logger.warning("프레임이 None — 빈 결과 반환")
            return DetectionResult(
                frame_id=frame_id,
                timestamp=time.time(),
                detections=[],
                inference_ms=0.0
            )

        # [3-4] YOLO 추론 실행
        start_time = time.perf_counter()
        try:
            results = self.model.predict(
                source=frame,
                conf=self.config.YOLO_CONFIDENCE_THRESHOLD,
                verbose=False,
                half=self.config.YOLO_HALF_PRECISION,
                device=self.config.YOLO_DEVICE
            )
        except RuntimeError as e:
            # CUDA OOM  CPU 폴백
            if "out of memory" in str(e).lower() or "CUDA" in str(e):
                logger.warning(f"GPU 메모리 부족, CPU 폴백: {e}")
                results = self.model.predict(
                    source=frame,
                    conf=self.config.YOLO_CONFIDENCE_THRESHOLD,
                    verbose=False,
                    device="cpu"
                )
            else:
                raise

        inference_ms = (time.perf_counter() - start_time) * 1000

        # [3-5] 탐지 결과 파싱
        result = results[0]
        boxes = result.boxes

        # [3-6 ~ 3-8] 각 박스 정보 추출  Detection 객체 생성  리스트 조립
        detections: List[Detection] = []
        for box in boxes:
            cls_id = int(box.cls[0])
            class_name = self.class_names[cls_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detection = Detection(
                class_name=class_name,
                confidence=round(confidence, 3),
                bbox=BBox(
                    x=round(x1, 1),
                    y=round(y1, 1),
                    w=round(x2 - x1, 1),
                    h=round(y2 - y1, 1)
                )
            )
            detections.append(detection)

        return DetectionResult(
            frame_id=frame_id,
            timestamp=time.time(),
            detections=detections,
            inference_ms=round(inference_ms, 2)
        )
```

### 2.4 ByteTrack 래퍼 (`app/detection/byte_tracker.py`)

```python
"""
3-9 ~ 3-13: ByteTrack 객체 추적 + Redis 시계열 컨텍스트 버퍼
"""
import json
import math
import time
import logging
from typing import List, Optional

import numpy as np
import redis

from server.api.config import DetectionConfig
from server.detection.detection_models import Detection, BBox, Direction

logger = logging.getLogger(__name__)

class ObjectTracker:
    """ByteTrack 기반 멀티-객체 추적기 + Redis 컨텍스트 버퍼"""

    def __init__(self, config: DetectionConfig = None, redis_client: redis.Redis = None):
        self.config = config or DetectionConfig()
        self.redis_bus = redis_client

        # [3-9] ByteTrack 초기화 (서버 시작 시 1회)
        try:
            from bytetracker import ByteTracker
            self.tracker = ByteTracker(
                track_thresh=self.config.BYTETRACK_TRACK_THRESH,
                track_buffer=self.config.BYTETRACK_TRACK_BUFFER,
                match_thresh=self.config.BYTETRACK_MATCH_THRESH
            )
            self._tracking_enabled = True
            logger.info("ByteTrack 초기화 완료")
        except ImportError:
            logger.warning("bytetracker 패키지 미설치 — 추적 비활성화")
            self.tracker = None
            self._tracking_enabled = False

        self._prev_timestamp: Optional[float] = None

    def update(
        self,
        detections: List[Detection],
        frame: np.ndarray,
        current_time: Optional[float] = None
    ) -> List[Detection]:
        """
        탐지 결과에 Track ID를 부여하고, 속도/방향을 계산하여 반환

        Args:
            detections: YOLO 탐지 결과 리스트
            frame: 현재 프레임 (ByteTrack 내부 사용)
            current_time: 현재 타임스탬프 (None이면 time.time() 사용)

        Returns:
            Track ID, 속도, 방향이 추가된 Detection 리스트
        """
        if not detections:
            return detections

        ts = current_time or time.time()
        dt = (ts - self._prev_timestamp) if self._prev_timestamp else 0.033  # 기본 30fps
        self._prev_timestamp = ts

        if not self._tracking_enabled:
            return detections

        # [3-10] 추적 업데이트 — Track ID 부여
        try:
            # ByteTrack이 기대하는 형식으로 변환
            det_array = []
            for d in detections:
                x1 = d.bbox.x
                y1 = d.bbox.y
                x2 = d.bbox.x + d.bbox.w
                y2 = d.bbox.y + d.bbox.h
                det_array.append([x1, y1, x2, y2, d.confidence])

            tracks = self.tracker.update(
                np.array(det_array) if det_array else np.empty((0, 5)),
                frame
            )
        except Exception as e:
            logger.error(f"ByteTrack 업데이트 실패: {e}")
            return detections

        # [3-11] Track ID 매핑
        tracked_detections: List[Detection] = []
        for track in tracks:
            track_id = f"T-{int(track.track_id):04d}"
            x1, y1, x2, y2 = track.tlbr  # top-left, bottom-right

            # 기존 detection과 IoU 기반 매칭
            best_det = self._match_detection(detections, x1, y1, x2, y2)
            if best_det is None:
                continue

            # [3-12] Redis 시계열 컨텍스트 버퍼 업데이트
            current_bbox = BBox(
                x=round(x1, 1),
                y=round(y1, 1),
                w=round(x2 - x1, 1),
                h=round(y2 - y1, 1)
            )

            speed, direction = self._update_context(
                track_id=track_id,
                bbox=current_bbox,
                class_name=best_det.class_name,
                confidence=best_det.confidence,
                dt=dt
            )

            tracked_det = best_det.model_copy(update={
                "track_id": track_id,
                "bbox": current_bbox,
                "speed": speed,
                "direction": direction
            })
            tracked_detections.append(tracked_det)

        return tracked_detections

    def _update_context(
        self,
        track_id: str,
        bbox: BBox,
        class_name: str,
        confidence: float,
        dt: float
    ) -> tuple:
        """
        [3-12 ~ 3-13] Redis에 컨텍스트 저장 + 속도/방향 계산

        Returns:
            (speed, direction) 튜플
        """
        speed = 0.0
        direction = Direction.UNKNOWN

        if self.redis_bus:
            try:
                prev = self.redis_bus.hgetall(f"ctx:{track_id}")
                if prev and b"last_pos" in prev:
                    prev_bbox_json = prev[b"last_pos"].decode()
                    speed = self._calculate_speed(prev_bbox_json, bbox, dt)
                    direction = Direction.APPROACHING if speed > 0.5 else Direction.DEPARTING
                    first_seen = prev.get(b"first_seen", str(time.time()).encode()).decode()
                else:
                    first_seen = str(time.time())

                # Redis Hash 업데이트
                self.redis_bus.hset(f"ctx:{track_id}", mapping={
                    "last_pos": bbox.model_dump_json(),
                    "speed": str(speed),
                    "direction": direction.value,
                    "first_seen": first_seen,
                    "class_name": class_name,
                    "confidence": str(confidence)
                })
                self.redis_bus.expire(f"ctx:{track_id}", self.config.CONTEXT_TTL_SECONDS)
            except redis.ConnectionError:
                logger.warning("Redis 연결 실패 — 컨텍스트 버퍼 업데이트 스킵")

        return speed, direction

    @staticmethod
    def _calculate_speed(prev_bbox_json: str, curr_bbox: BBox, dt: float) -> float:
        """
        [3-13] 이전 프레임 bbox와 현재 bbox 차이로 속도(px/s) 산출
        """
        prev = json.loads(prev_bbox_json)
        prev_cx = prev['x'] + prev['w'] / 2
        prev_cy = prev['y'] + prev['h'] / 2
        curr_cx, curr_cy = curr_bbox.center

        dist_px = math.sqrt((curr_cx - prev_cx) ** 2 + (curr_cy - prev_cy) ** 2)
        speed_px_per_sec = dist_px / max(dt, 0.001)
        return round(speed_px_per_sec, 2)

    @staticmethod
    def _match_detection(
        detections: List[Detection],
        x1: float, y1: float, x2: float, y2: float
    ) -> Optional[Detection]:
        """IoU 기반으로 track bbox와 가장 잘 맞는 detection을 매칭"""
        best_iou = 0.0
        best_det = None

        for det in detections:
            dx1 = det.bbox.x
            dy1 = det.bbox.y
            dx2 = det.bbox.x + det.bbox.w
            dy2 = det.bbox.y + det.bbox.h

            inter_x1 = max(x1, dx1)
            inter_y1 = max(y1, dy1)
            inter_x2 = min(x2, dx2)
            inter_y2 = min(y2, dy2)

            inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
            union_area = (
                (x2 - x1) * (y2 - y1) +
                (dx2 - dx1) * (dy2 - dy1) -
                inter_area
            )

            iou = inter_area / max(union_area, 1e-6)
            if iou > best_iou:
                best_iou = iou
                best_det = det

        return best_det if best_iou > 0.3 else None
```

### 2.5 Risk Gate (`app/detection/risk_gate.py`)

```python
"""
3-14 ~ 3-17: 위험도 1차 분류 + Redis 발행 + 최종 JSON 생성
"""
import json
import time
import logging
from typing import List

import redis

from server.api.config import DetectionConfig
from server.detection.detection_models import Detection, RiskLevel

logger = logging.getLogger(__name__)

class RiskGate:
    """위험도 1차 분류 엔진"""

    def __init__(self, config: DetectionConfig = None, redis_client: redis.Redis = None):
        self.config = config or DetectionConfig()
        self.redis_bus = redis_client

    def classify_risk(self, detection: Detection) -> RiskLevel:
        """
        [3-14] 위험도 분류 룰

        - car/truck/bus + speed > 1.5  HIGH
        - kickboard/stair/bollard  MID
        - 그 외  LOW
        """
        class_name = detection.class_name.lower()
        speed = detection.speed or 0.0

        if class_name in self.config.HIGH_RISK_CLASSES and speed > self.config.HIGH_RISK_SPEED_THRESHOLD:
            return RiskLevel.HIGH
        elif class_name in self.config.MID_RISK_CLASSES:
            return RiskLevel.MID
        else:
            return RiskLevel.LOW

    def process_detections(self, detections: List[Detection]) -> List[Detection]:
        """
        전체 탐지 리스트에 위험도를 할당하고 적절한 채널로 발행

        Returns:
            위험도가 할당된 Detection 리스트
        """
        processed: List[Detection] = []

        for det in detections:
            risk = self.classify_risk(det)
            det_with_risk = det.model_copy(update={"risk": risk})

            # 위험도별 발행
            self._publish(det_with_risk, risk)
            processed.append(det_with_risk)

        return processed

    def _publish(self, detection: Detection, risk: RiskLevel):
        """
        [3-15 ~ 3-16] 위험도별 처리 분기

        - HIGH: LLM 거치지 않고 즉시 로컬 TTS 안내
        - MID/LOW: Redis Streams에 발행
        """
        if self.redis_bus is None:
            logger.warning("Redis 미연결 — 발행 스킵")
            return

        try:
            if risk == RiskLevel.HIGH:
                # [3-15] 즉시 TTS 경고
                tts_message = self._generate_urgent_message(detection)
                self.redis_bus.publish(
                    self.config.TTS_URGENT_CHANNEL,
                    json.dumps({
                        "message": tts_message,
                        "priority": "urgent",
                        "track_id": detection.track_id,
                        "timestamp": time.time()
                    }, ensure_ascii=False)
                )
                logger.warning(f" 긴급 TTS 발행: {tts_message}")

            else:
                # [3-16] mid/low  Redis Streams 발행
                self.redis_bus.xadd(
                    self.config.RISK_EVENTS_STREAM,
                    {
                        "track_id": detection.track_id or "unknown",
                        "class_name": detection.class_name,
                        "confidence": str(detection.confidence),
                        "bbox": detection.bbox.model_dump_json(),
                        "speed": str(detection.speed or 0),
                        "direction": (detection.direction.value
                                      if detection.direction else "unknown"),
                        "risk": risk.value,
                        "timestamp": str(time.time())
                    }
                )
                logger.info(f" risk.events 발행: {detection.class_name} [{risk.value}]")

        except redis.ConnectionError:
            logger.error("Redis 연결 실패 — 발행 불가")

    @staticmethod
    def _generate_urgent_message(detection: Detection) -> str:
        """긴급 TTS 메시지 생성 (한국어)"""
        class_name_kr = {
            "car": "차량",
            "truck": "트럭",
            "bus": "버스",
            "motorcycle": "오토바이"
        }.get(detection.class_name.lower(), detection.class_name)

        direction_kr = {
            "approaching": "접근 중",
            "departing": "멀어지는 중",
            "unknown": ""
        }.get(detection.direction.value if detection.direction else "unknown", "")

        return f"전방 {class_name_kr} {direction_kr}, 멈추세요"
```

### 2.6 통합 파이프라인 (`app/detection/__init__.py`)

```python
"""
3단계 통합 파이프라인: YOLO  ByteTrack  Risk Gate
"""
import time
import logging
from typing import Optional

import numpy as np
import redis

from server.api.config import DetectionConfig
from server.detection.yolo_detector import YOLODetector
from server.detection.byte_tracker import ObjectTracker
from server.detection.risk_gate import RiskGate
from server.detection.detection_models import DetectionResult

logger = logging.getLogger(__name__)

class DetectionPipeline:
    """3단계 전체 파이프라인 오케스트레이터"""

    def __init__(self, config: DetectionConfig = None, redis_client: redis.Redis = None):
        self.config = config or DetectionConfig()
        self.redis_bus = redis_client or self._connect_redis()

        self.detector = YOLODetector(self.config)
        self.tracker = ObjectTracker(self.config, self.redis_bus)
        self.risk_gate = RiskGate(self.config, self.redis_bus)

    def _connect_redis(self) -> Optional[redis.Redis]:
        try:
            client = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=False
            )
            client.ping()
            return client
        except redis.ConnectionError:
            logger.warning("Redis 연결 불가 — 컨텍스트/발행 기능 비활성화")
            return None

    def process_frame(self, frame: np.ndarray, frame_id: str = "") -> DetectionResult:
        """
        단일 프레임 처리: YOLO 탐지  ByteTrack 추적  Risk Gate 분류

        Args:
            frame: 640×640 BGR numpy 배열
            frame_id: 프레임 고유 식별자

        Returns:
            DetectionResult (위험도 포함)
        """
        # Step 1: YOLO 추론
        result = self.detector.detect(frame, frame_id)

        if not result.detections:
            return result

        # Step 2: ByteTrack 추적
        tracked = self.tracker.update(result.detections, frame)

        # Step 3: Risk Gate 위험도 분류
        classified = self.risk_gate.process_detections(tracked)

        # 최종 결과 업데이트
        result.detections = classified
        return result
```

---

## 3. FastAPI 라이프사이클 통합

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from server.detection import DetectionPipeline

pipeline: DetectionPipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    pipeline = DetectionPipeline()
    yield
    # 정리 작업
    if pipeline.redis_bus:
        pipeline.redis_bus.close()

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/detect")
async def ws_detect(websocket):
    await websocket.accept()
    frame_count = 0
    while True:
        data = await websocket.receive_bytes()
        frame = decode_frame(data)  # 2단계에서 정의된 함수
        frame_count += 1

        result = pipeline.process_frame(frame, frame_id=f"F-{frame_count:06d}")
        await websocket.send_json(result.model_dump())
```

---

## 4. 테스트 코드 (`tests/test_detection.py`)

```python
"""
3-18, 3-19: 탐지 정확도 및 Redis TTL 테스트
"""
import time
import json
import numpy as np
import pytest
import redis
import cv2

from server.detection import DetectionPipeline
from server.api.config import DetectionConfig

@pytest.fixture
def pipeline():
    config = DetectionConfig(YOLO_DEVICE="cpu", YOLO_HALF_PRECISION=False)
    return DetectionPipeline(config=config)

@pytest.fixture
def redis_client():
    return redis.Redis(host="localhost", port=6379, db=0)


class TestYOLODetection:
    """3-18: 킥보드 사진 추론 테스트"""

    def test_kickboard_detection(self, pipeline):
        # 테스트 이미지 로드
        frame = cv2.imread("tests/fixtures/kickboard.jpg")
        frame = cv2.resize(frame, (640, 640))

        result = pipeline.process_frame(frame, frame_id="TEST-001")

        # 탐지 결과 확인
        assert len(result.detections) > 0
        kickboard_det = next(
            (d for d in result.detections if d.class_name == "kickboard"),
            None
        )
        assert kickboard_det is not None
        assert kickboard_det.confidence >= 0.4
        assert kickboard_det.bbox.w > 0 and kickboard_det.bbox.h > 0

        # 성능 기준: 추론 < 80ms (GPU 기준)
        # CPU에서는 더 느릴 수 있으므로 200ms로 완화
        assert result.inference_ms < 200, f"추론 시간 초과: {result.inference_ms}ms"

    def test_empty_frame(self, pipeline):
        """빈 프레임(검은 이미지) 입력 시 빈 결과"""
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        result = pipeline.process_frame(frame, frame_id="TEST-EMPTY")
        assert isinstance(result.detections, list)

    def test_none_frame(self, pipeline):
        """None 프레임 입력 시 안전한 빈 결과"""
        result = pipeline.process_frame(None, frame_id="TEST-NONE")
        assert len(result.detections) == 0
        assert result.inference_ms == 0.0


class TestRedisContextTTL:
    """3-19: Redis 30초 TTL 자동 삭제 테스트"""

    def test_context_ttl_expiration(self, redis_client):
        track_id = "T-9999"
        key = f"ctx:{track_id}"

        # 컨텍스트 설정
        redis_client.hset(key, mapping={
            "last_pos": json.dumps({"x": 100, "y": 100, "w": 50, "h": 50}),
            "speed": "1.2",
            "direction": "approaching"
        })
        redis_client.expire(key, 2)  # 테스트용 2초 TTL

        # 즉시 확인 — 존재해야 함
        assert redis_client.exists(key) == 1

        # 3초 대기 후 확인 — 삭제되어야 함
        time.sleep(3)
        assert redis_client.exists(key) == 0


class TestRiskGate:
    """3-14 ~ 3-16: Risk Gate 분기 테스트"""

    def test_high_risk_car(self, pipeline):
        from server.detection.detection_models import Detection, BBox
        det = Detection(
            class_name="car",
            confidence=0.92,
            bbox=BBox(x=100, y=100, w=200, h=150),
            speed=2.0,
            direction="approaching"
        )
        risk = pipeline.risk_gate.classify_risk(det)
        assert risk.value == "high"

    def test_mid_risk_kickboard(self, pipeline):
        from server.detection.detection_models import Detection, BBox
        det = Detection(
            class_name="kickboard",
            confidence=0.85,
            bbox=BBox(x=142, y=89, w=168, h=391),
            speed=0.5
        )
        risk = pipeline.risk_gate.classify_risk(det)
        assert risk.value == "mid"

    def test_low_risk_bench(self, pipeline):
        from server.detection.detection_models import Detection, BBox
        det = Detection(
            class_name="bench",
            confidence=0.78,
            bbox=BBox(x=300, y=200, w=100, h=80),
            speed=0.0
        )
        risk = pipeline.risk_gate.classify_risk(det)
        assert risk.value == "low"
```

---

## 5. 커스텀 YOLO 모델 학습 참고 (선택)

시각장애인 보행에 특화된 클래스를 탐지하려면 커스텀 데이터셋으로 YOLO26을 파인튜닝할 수 있다.

```yaml
# data/custom_dataset.yaml
path: ./data/custom
train: images/train
val: images/val

names:
  0: person
  1: car
  2: truck
  3: bus
  4: motorcycle
  5: bicycle
  6: kickboard      # 커스텀
  7: bollard         # 커스텀
  8: stair           # 커스텀
  9: pothole         # 커스텀
  10: construction   # 커스텀
```

```python
# scripts/train_custom.py
from ultralytics import YOLO

model = YOLO("det_weights.pt")  # 사전학습 모델 기반
results = model.train(
    data="data/custom_dataset.yaml",
    epochs=100,
    imgsz=640,
    batch=16,
    name="blind_assist_v1"
)
# 결과: runs/detect/blind_assist_v1/weights/best.pt
```

---

## 6. 디버깅용 시각화 (개발 환경 전용)

```python
import cv2

def draw_detections(frame, detections):
    """탐지 결과를 프레임에 시각적으로 오버레이 (개발/디버깅용)"""
    color_map = {
        "high": (0, 0, 255),   # 빨강
        "mid": (0, 165, 255),  # 주황
        "low": (0, 255, 0)     # 초록
    }

    for det in detections:
        bbox = det.bbox
        color = color_map.get(det.risk.value if det.risk else "low", (255, 255, 255))

        # 바운딩 박스
        cv2.rectangle(
            frame,
            (int(bbox.x), int(bbox.y)),
            (int(bbox.x + bbox.w), int(bbox.y + bbox.h)),
            color, 2
        )

        # 라벨
        label = f"{det.class_name} {det.confidence:.2f}"
        if det.track_id:
            label = f"[{det.track_id}] {label}"
        if det.risk:
            label += f" ({det.risk.value})"

        cv2.putText(
            frame, label,
            (int(bbox.x), int(bbox.y) - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
        )

    return frame
```
