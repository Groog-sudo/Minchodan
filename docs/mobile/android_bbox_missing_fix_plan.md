# 안드로이드 스마트폰 앱 객체 탐지 BBOX 누락 수정 계획

## 원인 분석

1. **온디바이스 디코딩 생략**:
   - 실기기(REAL) 모드에서는 ANE 가속/TFLite 추론용 디코딩 시 발생하는 JS CPU 100% 점유 및 iOS Watchdog SIGKILL 방지를 위해 디코딩된 Float32Array를 비워서(`new Float32Array(0)`) 보냅니다.
   - 이로 인해 단말의 온디바이스 추론(`detectFrame`)에 입력 텐서가 비어 있어, 온디바이스 검출 결과가 항상 `0`개로 반환됩니다.
2. **서버 탐지 결과의 피드백 부재**:
   - 스마트폰 화면의 BBOX 오버레이는 전적으로 **온디바이스 추론 결과(`detections`)**만 바라보고 있습니다.
   - 서버는 이미지를 받아서 백그라운드로 YOLO 장애물 탐지와 Segmentation 노면 탐지를 정상 수행하고 있으나, 그 탐지 결과(`detections` 목록)를 단말에 알려주는 WebSocket 프로토콜(메시지 타입)이 존재하지 않아 스마트폰 화면에 그릴 수 없습니다.

## 해결 방안

- 서버의 `DetectionConsumer`가 YOLO 및 Segmentation 추론을 마칠 때마다, 탐지된 모든 사물 및 노면 정보(`detections` 및 `surfaces` 목록)를 새로운 WebSocket 메시지 타입(`server_detection`)으로 단말에 실시간 송신합니다.
- 단말(`CameraView.tsx`)은 `server_detection` 메시지를 수신했을 때 `detections` 상태를 갱신하도록 수정하여, 서버 기반의 고성능 YOLO/Segmentation 탐지 결과가 모바일 화면에 실시간 BBOX로 완벽하게 그려지도록 조치합니다.
- 노면 분할(Segmentation) 결과인 `SurfaceResult`는 `centroid` 무게중심 점 좌표만 가지고 있으므로, 단말의 `BBoxOverlay`에서 정상적으로 렌더링될 수 있도록 서버 단에서 centroid 주변의 가상 `80x80 BBox`로 변환하여 함께 전송합니다.

---

## Proposed Changes

### 1. 클라이언트(단말) 타입 및 컴포넌트 수정 [MODIFY]

#### [MODIFY] [detection.ts](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/src/types/detection.ts)
- `MessageType` 유니온 타입에 `"server_detection"`을 추가합니다.
- `WSMessage` 인터페이스에 `detections?: any[]` 필드를 추가합니다.

#### [MODIFY] [CameraView.tsx](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/src/components/CameraView.tsx)
- `useEffect` 내 `lastMessage` 수신 감지 시, `lastMessage.type === "server_detection"` 분기를 추가하여 `lastMessage.detections`를 `setDetections` 상태로 업데이트하도록 코드를 수정합니다.

---

### 2. 서버 추론 및 송신 로직 수정 [MODIFY]

#### [MODIFY] [detection_pipeline.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/detection/detection_pipeline.py)
- `run` 메서드의 반환 형식을 `tuple[DetectionResult | ReflexAlert, list[Detection], list[SurfaceResult]]`로 확장하여, 게이트 분기(ReflexAlert 리턴 등)와 관계없이 탐지 완료된 `detections`와 `surfaces` 리스트를 항상 함께 상위 호출자에게 반환하도록 수정합니다.

#### [MODIFY] [consumer.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/detection/consumer.py)
- `_process_frame`에서 `self._pipeline.run(...)` 호출 시 튜플을 정상적으로 수신하도록 수정합니다.
- 추론 완료 직후 단말로 `server_detection` 메시지를 전송하는 `_send_server_detection(device_id, event_id, detections, surfaces)` 비동기 메서드를 구현하여 호출합니다.
  - `surfaces` 노면 정보의 경우, centroid `[cx, cy]` 기준으로 가상의 `80x80` 크기 bbox를 계산하여 단말에 전달합니다.

---

### 3. 작업 로그 기록 [MODIFY]

#### [MODIFY] [dg.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/dg.md)
- 기존 내용을 보존하고 맨 마지막에 이번 안드로이드 스마트폰 앱 객체 탐지 BBOX 누락 이슈의 원인, 해결 방안 및 수정 사항에 대한 changelog를 누적 기록합니다.

---

## Verification Plan

### Manual Verification
- 안드로이드 스마트폰 앱을 PC와 연동하여 동작시킵니다.
- 카메라를 장애물(사람, 킥보드, 차량 등)로 비추었을 때 서버 로그 상으로 YOLO 추론이 이루어지는 시점에 안드로이드 스마트폰 화면 위로 빨간색/주황색 등의 실시간 BBOX가 어긋남 없이 그려지는지 정밀 검증합니다.
