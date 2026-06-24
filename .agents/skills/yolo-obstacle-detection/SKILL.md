---
name: yolo-obstacle-detection
description: |
  서버에 전송된 실시간 카메라 프레임에서 Yolo 26N - Object Detection으로 킥보드·볼라드·계단 등 시각장애인 위험 사물을 탐지하고,
  Yolo 26N - Segmentation으로 노면 상태를 분할하며, ByteTrack으로 객체를 추적한다.
  이중 게이트(Reflex Gate + Surface Gate)로 위험도를 1차 분류하는 듀얼헤드 파이프라인.
---

# Yolo 26N - Object Detection (3단계: AI 장애물 실시간 인식)  v1.1 핵심

> **작성일**: 2026-06-24
> **버전**: v0.2.0
> **설계 기준**: `docs/minchodan_design_note.md` 3단계 (v1.1 듀얼헤드 + 이중 게이트)
> **코딩 패턴 준수**: [`docs/course_codebase_guide.md`](../../../docs/course_codebase_guide.md) 섹션 10, 9, 17.2

## 개요

2단계(프레임 수신)에서 받은 640x640 BGR 프레임을 **Yolo 26N - Object Detection**으로 추론하여 킥보드, 볼라드, 계단, 차량 등 위험 사물을 탐지하고, **Yolo 26N - Segmentation**으로 노면 상태(보행 가능 영역, 횡단보도, 점자블록 파손 등)를 분할하며, **ByteTrack**으로 Track ID를 부여한다. **이중 게이트**(Reflex Gate + Surface Gate) 룰로 위험도를 1차 분류한다.

## v1.1 핵심 변경 사항

| 항목 | 기존 | v1.1 |
| --- | --- | --- |
| 객체 탐지 | YOLOv8 | **Yolo 26N - Object Detection** (NMS-free, sm_120, 소형객체 최적화) |
| 분할 | 없음 | **Yolo 26N - Segmentation** |
| 게이트 | 단일 Risk Gate | **이중 게이트**: Reflex Gate (Detection) + Surface Gate (Seg) |
| 노면 클래스 | 혼합 | **분리(C2)**: `braille normal/damaged`, `sidewalk normal/damaged`, `crosswalk`, `roadway`, `caution` |
| LLM 경유 | high도 LLM 거침 | **반사 경로 LLM 미경유** (비협상 원칙) |

## 전체 아키텍처 위치

```
[모바일 카메라]  [2단계: 프레임 수신]  3단계: Yolo 26N - Object Detection + Yolo 26N - Segmentation + ByteTrack + 이중 게이트
                                             high  Reflex Gate  사전합성 클립 (LLM 미경유)
                                             P0 노면  Surface Gate  사전합성 클립 (LLM 미경유)
                                             mid/low  Redis Streams  5단계 RAG  6단계 LangGraph
```

이 스킬은 **서버 측(GPU)** 에서 동작하며, 프레임당 **80ms 이내** 추론을 목표로 한다.

## 사전 조건

| 항목 | 요구사항 |
|------|----------|
| Python | 3.13 |
| GPU | Blackwell sm_120 (RTX 5090/5070 Ti), CUDA 12.8 + cu128 PyTorch 휠 |
| 패키지 | `ultralytics>=8.3`, `opencv-python>=4.10`, `redis>=5.0`, `bytetracker` |
| 모델 파일 | `server/models/yolo26n/object_detection.pt`, `server/models/yolo26n/segmentation.pt` |
| Redis | 7 이상, Streams 지원 필수 |
| 이전 단계 | 2단계에서 640x640 BGR numpy 배열이 전달되어야 함 |

## 디렉토리 구조 (Minchodan 기준)

```
server/detection/
├── __init__.py
├── yolo_detector.py          # Yolo 26N - Object Detection 로딩 + 추론
├── yolo_segmentor.py         # Yolo 26N - Segmentation 로딩 + 추론
├── bytetrack_tracker.py      # ByteTrack 래퍼
├── schemas.py                # DetectionResult, SurfaceResult, RiskEvent 타입
└── gates/
    ├── reflex_gate.py        # Reflex Risk Gate (고위험 + 근접  alert_id+방향)
    └── surface_gate.py       # Surface Fast-Alert Gate (P0 노면  alert_id)
```

## 핵심 구현 절차

### 단계 3-1. Yolo 26N - Object Detection 모델 로딩 (서버 시작 시 1회)

```python
# -*- coding: utf-8 -*-
# server/detection/yolo_detector.py
import os
import sys
from ultralytics import YOLO

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# 가이드 3.3: 실행 위치와 무관한 모델 경로 계산
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
model_path = os.path.join(project_root, "server", "models", "yolo26n", "object_detection.pt")

model = YOLO(model_path)
print(model.names)
# 커스텀 클래스: kickboard, bollard, stair, car, truck, bus, ...
```

- 모델은 **싱글턴**으로 유지 — 매 요청마다 재로딩 금지
- `verify_gpu.py`로 `device_capability >= (12,0)` 사전 검증

### 단계 3-2. Yolo 26N - Object Detection 추론 실행

```python
results = model.predict(source=frame, conf=0.35, verbose=False)
result = results[0]
boxes = result.boxes
```

- `conf=0.35` — Confidence Threshold (design_note 기준)
- `verbose=False` — 콘솔 로그 억제 (성능)

### 단계 3-3. Yolo 26N - Segmentation 추론 실행

```python
# -*- coding: utf-8 -*-
# server/detection/yolo_segmentor.py
import os
import sys
from ultralytics import YOLO

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# 가이드 3.3: 실행 위치와 무관한 모델 경로 계산
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
model_path = os.path.join(project_root, "server", "models", "yolo26n", "segmentation.pt")

segmentor = YOLO(model_path)
results = segmentor.predict(source=frame, conf=0.35, verbose=False)
result = results[0]
masks = result.masks if result.masks is not None else []
# 노면 클래스: braille_normal, braille_damaged, sidewalk_normal, sidewalk_damaged, crosswalk, roadway, caution
```

### 단계 3-4. ByteTrack 객체 추적

```python
# -*- coding: utf-8 -*-
# server/detection/bytetrack_tracker.py
import sys
from bytetracker import ByteTracker

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

tracker = ByteTracker()
tracks = tracker.update(detections, frame)
# 각 track에 "T-0023" 형태의 고유 ID 매핑
```

### 단계 3-5. Redis 시계열 컨텍스트 버퍼 (TTL=30)

```python
import time, json

for track in tracks:
    track_id = f"T-{track['id']:04d}"
    prev = redis_bus.hgetall(f"ctx:{track_id}")

    if prev:
        speed = calculate_speed(prev['last_pos'], track['bbox'], dt)
        direction = "approaching" if speed > 0.5 else "departing"
    else:
        speed = 0.0
        direction = "unknown"

    redis_bus.hset(f"ctx:{track_id}", mapping={
        "last_pos": json.dumps(track['bbox']),
        "speed": str(speed),
        "direction": direction,
        "class_name": track['class_name'],
    })
    redis_bus.expire(f"ctx:{track_id}", 30)  # 30초 TTL
```

### 단계 3-6. Reflex Risk Gate (룰베이스, LLM 미경유)

```python
# -*- coding: utf-8 -*-
# server/detection/gates/reflex_gate.py
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

HIGH_RISK_CLASSES = {"car", "truck", "bus", "motorcycle"}
PROXIMITY_THRESHOLD = 0.15  # 프레임 하단 면적 비율

def reflex_gate(detection, frame_height, frame_width):
    """고위험 클래스 && 근접(면적·하단)  즉시 alert_id + 방향"""
    if detection.class_name in HIGH_RISK_CLASSES:
        bbox = detection.bbox
        # 하단 근접 체크: bbox 하단이 프레임 하단 15% 이내
        bottom_y = bbox.y + bbox.h
        if bottom_y > frame_height * (1 - PROXIMITY_THRESHOLD):
            direction = _estimate_direction(bbox, frame_width)
            alert_id = f"high_{direction}"
            return {"alert_id": alert_id, "direction": direction, "risk_level": "high"}
    return None

def _estimate_direction(bbox, frame_width):
    center_x = bbox.x + bbox.w / 2
    if center_x < frame_width / 3: return "left"
    elif center_x > frame_width * 2 / 3: return "right"
    else: return "front"
```

### 단계 3-7. Surface Fast-Alert Gate (룰베이스, LLM 미경유)

```python
# -*- coding: utf-8 -*-
# server/detection/gates/surface_gate.py
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# P0 노면 클래스 (즉시 경보 대상)
P0_SURFACE_CLASSES = {
    "crosswalk", "manhole", "stair", "grating", "braille_damaged"
}

def surface_gate(surface_result, frame_height):
    """P0 노면 하단 검출  즉시 alert_id"""
    for seg in surface_result:
        if seg.class_name in P0_SURFACE_CLASSES:
            centroid_y = seg.centroid[1]
            # 하단 검출 체크
            if centroid_y > frame_height * 0.6:
                alert_id = f"surface_{seg.class_name}"
                return {"alert_id": alert_id, "direction": "front", "risk_level": "high"}
    return None
```

### 단계 3-8. 위험도별 처리 분기

| 위험도 | 게이트 | 행동 |
|--------|--------|------|
| `high` | Reflex Gate | **LLM/RAG 미경유**, 사전합성 클립 즉시 재생 (7단계 반사 경로) |
| `high` | Surface Gate | **LLM/RAG 미경유**, 사전합성 클립 즉시 재생 (7단계 반사 경로) |
| `mid` | (게이트 통과) | Redis Streams `xadd("risk.events")` 발행  인지 경로 |
| `low` | (게이트 통과) | Redis Streams `xadd("risk.events")` 발행  인지 경로 |

### 단계 3-9. mid/low Redis Streams 발행

```python
def publish_to_cognitive_path(detection, risk):
    redis_bus.xadd("risk.events", {
        "track_id": detection.track_id or "unknown",
        "class_name": detection.class_name,
        "confidence": str(detection.confidence),
        "bbox": json.dumps(detection.bbox),
        "speed": str(detection.speed or 0),
        "direction": detection.direction or "unknown",
        "risk": risk,
        "timestamp": str(time.time())
    })
```

## 노면 클래스 분리 (C2)

| 클래스 | 설명 | 게이트 |
| --- | --- | --- |
| `braille_normal` | 점자블록 정상 | (해당 없음) |
| `braille_damaged` | 점자블록 파손 | Surface Gate (P0) |
| `sidewalk_normal` | 보도 정상 | (해당 없음) |
| `sidewalk_damaged` | 보도 파손 | (해당 없음, mid) |
| `crosswalk` | 횡단보도 | Surface Gate (P0) |
| `roadway` | 차도 | (주의, mid) |
| `caution` | 계단/맨홀/그레이팅 | Surface Gate (P0) |

> 같은 클래스로 묶으면 파손 학습이 불가하므로 **독립 클래스**로 분리한다.

## Pydantic 스키마

```python
# -*- coding: utf-8 -*-
# server/detection/schemas.py
import sys
from typing import List, Optional
from pydantic import BaseModel

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

class BBox(BaseModel):
    x: float; y: float; w: float; h: float

class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: BBox
    track_id: Optional[str] = None
    speed: Optional[float] = None
    direction: Optional[str] = None
    risk: Optional[str] = None       # "high" | "mid" | "low"

class SurfaceResult(BaseModel):
    class_name: str
    mask: Optional[str] = None
    centroid: List[float]

class RiskEvent(BaseModel):
    event_id: str
    detections: List[Detection]
    surface: List[SurfaceResult]
    risk_hint: str
    inference_ms: float
```

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| 킥보드 탐지 | `conf>=0.87, track_id` | 추론 < 80ms |
| Yolo 26N - Segmentation | 노면 마스크 생성 | 클래스 분리 확인 |
| Reflex Gate 분기 | 고위험+근접  alert_id+방향 | LLM 미경유 |
| Surface Gate 분기 | P0 노면 하단  alert_id | LLM 미경유 |
| Redis 컨텍스트 TTL | 30초 후 자동 삭제 | `exists`  False |
| mid/low 발행 | `xadd("risk.events")` | 메시지 ID 반환 |
| 무탐지 빈 리스트 | 에러 없이 빈 리스트 | 파이프라인 영속성 |
| 노면 클래스 분리 (C2) | `braille_damaged` 독립 검출 | 분리 클래스 학습 |

## 에러 처리

| 상황 | 처리 |
|------|------|
| 모델 파일 없음 | 서버 시작 실패 + 로그 경고 |
| 프레임이 None | 추론 스킵, 빈 detections 반환 |
| Redis 연결 실패 | 컨텍스트 업데이트 스킵, 탐지 결과는 정상 반환 |
| CUDA OOM | CPU 폴백 (`device='cpu'`) |
| ByteTrack 초기화 실패 | Track ID 없이 탐지 결과만 반환 |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- 아키텍처 설계서: [`docs/architecture.md`](../../../docs/architecture.md) 5.3절
- 학습 환경 전제: [`docs/architecture.md`](../../../docs/architecture.md) 11절
