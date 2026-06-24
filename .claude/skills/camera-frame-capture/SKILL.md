---
name: camera-frame-capture
description: |
  스마트폰 카메라 실시간 프레임 캡처 및 서버 전송 파이프라인 구현.
  React Native vision-camera로 이중 캡처(반사 8~10fps / 인지 1~2fps), base64 인코딩 후 WebSocket 전송,
  서버에서 OpenCV 디코딩 및 Redis Streams 발행까지의 전체 흐름을 다룬다.
---

# Camera Frame Capture (2단계: 카메라 화면 전송)

> **작성일**: 2026-06-24
> **버전**: v0.1.0
> **설계 기준**: `docs/minchodan_design_note.md` 2단계 (v1.1 이중 스트림 반영)

## 개요

시각장애인 보행자가 **지금 어떤 길을 걷고 있는지** 실제 시각 정보를 AI 서버에 실시간으로 전달하는 파이프라인이다. v1.1 설계에 따라 **이중 캡처 스트림**(반사 8~10fps / 인지 1~2fps)으로 분리하여 충돌 회피와 상세 가이드를 동시에 지원한다.

## 선행 의존성

- **1단계 (websocket-gateway)**: WebSocket 연결이 수립된 상태에서 동작한다.
- WebSocket `status === 'connected'` 상태에서만 프레임 캡처를 시작한다.

## 목표 아키텍처

```
┌────────────────────────────────────────┐
│          React Native 앱               │
│                                        │
│  ┌──────────┐    ┌───────────────────┐ │
│  │ Camera   │───►│ 이중 캡처 루프     │ │
│  │ (후면)   │    │ 반사 8~10fps      │ │
│  │          │    │ 인지 1~2fps       │ │
│  └──────────┘    └────────┬──────────┘ │
│                           │ base64      │
│                  ┌────────▼──────────┐ │
│                  │ WebSocket.send()  │ │
│                  │ detection 이벤트  │ │
│                  └────────┬──────────┘ │
└───────────────────────────┼────────────┘
                            │ ws://
┌───────────────────────────▼────────────┐
│          FastAPI 서버                   │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ server/capture/frame_decoder.py │  │
│  │  base64 decode                  │  │
│  │  np.frombuffer()                │  │
│  │  cv2.imdecode()                 │  │
│  │  cv2.resize(640, 640)           │  │
│  └──────────────┬───────────────────┘  │
│                 │ xadd                  │
│  ┌──────────────▼───────────────────┐  │
│  │ server/capture/stream_splitter.py│  │
│  │ 반사 스트림 / 인지 스트림 분기    │  │
│  └──────────────┬───────────────────┘  │
│                 │ xadd                  │
│  ┌──────────────▼───────────────────┐  │
│  │ Redis Stream: risk.events        │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| 모바일 카메라 | react-native-vision-camera v4 | 후면 카메라 이중 캡처 |
| 이미지 인코딩 | base64 (JPEG) | 바이너리텍스트 변환 (WS 전송용) |
| 서버 이미지 처리 | OpenCV (cv2) + NumPy | JPEG 디코딩 + 리사이징 |
| 전송 프로토콜 | WebSocket (1단계 연결 재사용) | 프레임 데이터 전송 |
| 이벤트 버스 | Redis Streams | YOLO 파이프라인으로 프레임 전달 |

## 디렉토리 구조 (Minchodan 기준)

```
# ── 앱 측 (React Native) ──
client/src/
├── components/
│   └── CameraView.tsx          # 카메라 컴포넌트 (UI)
├── hooks/
│   ├── useWebSocket.ts         # 1단계에서 구현한 WS 훅
│   ├── useCamera.ts            # 이중 캡처 타이머 훅
├── services/
│   └── frameCapture.ts         # takePhoto  base64  send
├── utils/
│   └── haptics.ts              # Haptics + 접근성
└── types/
    └── detection.ts            # DetectionEvent 타입 정의

# ── 서버 측 (FastAPI) ──
server/capture/
├── frame_decoder.py            # 프레임 디코딩 + 리사이징 모듈
└── stream_splitter.py          # 반사/인지 스트림 분기
```

## v1.1 핵심 변경: 이중 캡처 스트림

단일 2fps 캡처는 충돌 회피에 부적합하므로 **이중 스트림**으로 분리한다.

| 스트림 | 목표 fps | 용도 | 후속 처리 |
| --- | --- | --- | --- |
| **반사 (reflex)** | 8~10fps | Detection 전용, 즉시 경보 | 3단계 Yolo 26N - Object Detection  Reflex Gate  사전합성 클립 |
| **인지 (cognitive)** | 1~2fps | 상세 가이드 | 3단계 Yolo 26N - Object Detection + Yolo 26N - Segmentation  Redis Streams  LangGraph |

## 핵심 구현 절차 (React Native 앱 측)

### 단계 2-1. useCamera.ts — 이중 캡처 타이머

```typescript
// client/src/hooks/useCamera.ts
import { useEffect, useRef, useCallback, useState } from 'react';
import { Camera, useCameraDevice, useCameraPermission, PhotoFile } from 'react-native-vision-camera';

export function useCamera(reflexFps: number = 10, cognitiveFps: number = 2) {
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice('back');
  const cameraRef = useRef<Camera>(null);
  const reflexTimerRef = useRef<NodeJS.Timeout | null>(null);
  const cognitiveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  useEffect(() => {
    if (!hasPermission) requestPermission();
  }, [hasPermission, requestPermission]);

  const captureFrame = useCallback(async (stream: 'reflex' | 'cognitive'): Promise<string | null> => {
    if (!cameraRef.current) return null;
    try {
      const photo: PhotoFile = await cameraRef.current.takePhoto({
        qualityPrioritization: 'speed',
        flash: 'off',
        enableShutterSound: false,
      });
      const base64 = await photo.toBase64();
      return base64;
    } catch (error) {
      console.error(`[캡처] ${stream} 프레임 오류:`, error);
      return null;
    }
  }, []);

  const startCapture = useCallback(() => {
    if (isCapturing) return;
    setIsCapturing(true);

    const reflexInterval = Math.floor(1000 / reflexFps);
    const cognitiveInterval = Math.floor(1000 / cognitiveFps);

    reflexTimerRef.current = setInterval(async () => {
      const frame = await captureFrame('reflex');
      if (frame) sendFrame(frame, 'reflex');
    }, reflexInterval);

    cognitiveTimerRef.current = setInterval(async () => {
      const frame = await captureFrame('cognitive');
      if (frame) sendFrame(frame, 'cognitive');
    }, cognitiveInterval);

    console.log(`[캡처] 이중 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`);
  }, [reflexFps, cognitiveFps, isCapturing, captureFrame]);

  const stopCapture = useCallback(() => {
    if (reflexTimerRef.current) { clearInterval(reflexTimerRef.current); reflexTimerRef.current = null; }
    if (cognitiveTimerRef.current) { clearInterval(cognitiveTimerRef.current); cognitiveTimerRef.current = null; }
    setIsCapturing(false);
    console.log('[캡처] 루프 중지');
  }, []);

  useEffect(() => { return () => stopCapture(); }, [stopCapture]);

  return { cameraRef, device, hasPermission, isCapturing, startCapture, stopCapture, captureFrame };
}
```

### 단계 2-2. frameCapture.ts — 프레임 전송

```typescript
// client/src/services/frameCapture.ts
let frameCounter = 0;

export function generateEventId(): string {
  const ts = Date.now();
  const rand = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
  return `evt-${ts}-${rand}`;
}

export function buildDetectionEvent(base64: string, deviceId: string, stream: 'reflex' | 'cognitive') {
  frameCounter += 1;
  return {
    type: 'detection',
    payload: {
      event_id: generateEventId(),
      device_id: deviceId,
      timestamp: new Date().toISOString(),
      frame_id: frameCounter,
      stream: stream,
      thumbnail_jpeg_b64: base64,
      detections: [],
    },
  };
}

export function sendFrame(base64: string, stream: 'reflex' | 'cognitive', deviceId: string, send: (data: object) => void) {
  const event = buildDetectionEvent(base64, deviceId, stream);
  send(event);
  console.log(`[전송] stream=${stream}, frame_id=${frameCounter}, size≈${Math.round(base64.length * 0.75 / 1024)}KB`);
}
```

### 단계 2-3. CameraView.tsx

```tsx
// client/src/components/CameraView.tsx
import React, { useEffect } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { Camera } from 'react-native-vision-camera';
import { useCamera } from '../hooks/useCamera';
import { useWebSocket } from '../hooks/useWebSocket';
import { sendFrame } from '../services/frameCapture';

interface CameraViewProps { deviceId: string; token: string; }

export function CameraView({ deviceId, token }: CameraViewProps) {
  const { status, send } = useWebSocket(deviceId, token);
  const { cameraRef, device, hasPermission, isCapturing, startCapture, stopCapture } = useCamera(10, 2);

  useEffect(() => {
    if (status === 'connected' && !isCapturing) startCapture();
    else if (status !== 'connected' && isCapturing) stopCapture();
  }, [status, isCapturing, startCapture, stopCapture]);

  // frameCapture 서비스에서 sendFrame 호출 시 send 함수 전달
  // 실제 구현에서는 useCamera 내부에서 send를 받거나 별도 훅으로 연결

  if (!hasPermission) return <View><Text>카메라 권한이 필요합니다.</Text></View>;
  if (!device) return <View><Text>카메라를 찾을 수 없습니다.</Text></View>;

  return (
    <View style={styles.container}>
      <Camera ref={cameraRef} device={device} isActive={true} photo={true} style={StyleSheet.absoluteFill} />
      <View style={styles.statusOverlay}
        accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? '활성' : '비활성'}`} />
    </View>
  );
}
```

## 핵심 구현 절차 (서버 측)

### 단계 2-4. frame_decoder.py — 프레임 디코딩

```python
# server/capture/frame_decoder.py
import base64
import logging
import numpy as np
import cv2
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

TARGET_SIZE = (640, 640)
MAX_FRAME_SIZE_KB = 500
MIN_FRAME_SIZE_KB = 1

@dataclass
class ProcessedFrame:
    event_id: str
    device_id: str
    stream: str           # "reflex" | "cognitive"
    frame: np.ndarray     # (640, 640, 3) BGR
    original_size: tuple
    size_kb: float
    processing_time_ms: float

async def decode_frame(payload: dict) -> Optional[ProcessedFrame]:
    event_id = payload.get("event_id", "unknown")
    device_id = payload.get("device_id", "unknown")
    stream = payload.get("stream", "cognitive")
    b64_str = payload.get("thumbnail_jpeg_b64")

    if not b64_str:
        logger.warning(f"[프레임] base64 데이터 없음: event_id={event_id}")
        return None

    try:
        jpeg_bytes = base64.b64decode(b64_str)
        size_kb = len(jpeg_bytes) / 1024

        if size_kb > MAX_FRAME_SIZE_KB or size_kb < MIN_FRAME_SIZE_KB:
            logger.warning(f"[프레임] 크기 이상: {size_kb:.1f}KB")
            return None

        np_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)

        if frame is None:
            logger.error(f"[프레임] cv2.imdecode 실패: event_id={event_id}")
            return None

        original_size = (frame.shape[0], frame.shape[1])
        frame_resized = cv2.resize(frame, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)

        logger.info(f"[프레임] 수신: event_id={event_id}, stream={stream}, 원본={original_size[1]}x{original_size[0]}, 크기={size_kb:.1f}KB")
        return ProcessedFrame(event_id, device_id, stream, frame_resized, original_size, size_kb, 0.0)

    except Exception as e:
        logger.error(f"[프레임] 오류: event_id={event_id}, {e}")
        return None
```

### 단계 2-5. stream_splitter.py — 스트림 분기

```python
# server/capture/stream_splitter.py
import logging
from server.capture.frame_decoder import ProcessedFrame
from server.bus.redis_client import redis_bus

logger = logging.getLogger(__name__)

async def route_frame(processed: ProcessedFrame):
    """스트림 타입에 따라 Redis 발행 또는 즉시 탐지 경로로 전달"""
    if processed.stream == "reflex":
        # 반사 스트림: 3단계 Yolo 26N - Object Detection 전용 (Reflex Gate 우선)
        await redis_bus.publish_event("risk.events", {
            "event_id": processed.event_id,
            "device_id": processed.device_id,
            "stream": "reflex",
            "timestamp": "",
            "frame_hex": processed.frame.tobytes().hex(),
        })
    else:
        # 인지 스트림: 3단계 Yolo 26N - Object Detection + Yolo 26N - Segmentation (인지 경로)
        await redis_bus.publish_event("risk.events", {
            "event_id": processed.event_id,
            "device_id": processed.device_id,
            "stream": "cognitive",
            "timestamp": "",
            "frame_hex": processed.frame.tobytes().hex(),
        })
```

## 데이터 인터페이스

| 방향 | 페이로드 |
| --- | --- |
| In | 비디오 프레임 (이중 타이머 캡처) |
| Out | `{type:"detection", payload:{event_id, device_id, ts, frame_id, stream:"reflex"\|"cognitive", thumbnail_jpeg_b64}}` |

## 의존성·예외

- 선행 = 1단계 WS. 출력 = 3단계 입력.
- 카메라 권한 거부(`NotAllowedError`); 소켓 유실 시 `clearInterval`로 타이머 자원 즉시 해제(메모리 고갈 방지).
- 빈 버퍼/디코딩 실패(`None`) 가드레일; 무탐지 시 에러 없이 빈 리스트 반환.

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| 카메라 권한 요청 | 승인 다이얼로그 | Android/iOS 모두 |
| 후면 카메라 활성화 | isActive=true | device !== null |
| 반사 캡처 8~10fps | setInterval 주기 확인 | ±100ms 오차 |
| 인지 캡처 1~2fps | setInterval 주기 확인 | ±100ms 오차 |
| base64 변환 | JPEG base64 문자열 | 30~50KB 범위 |
| 서버 수신 | 프레임 디코딩 성공 | frame.shape == (640, 640, 3) |
| **캡처수신 지연** | 전체 파이프라인 | **< 50ms** |
| ack 응답 | 클라이언트 ack 수신 | event_id 일치 |
| 소켓 유실 타이머 해제 | clearInterval | 자원 해제 확인 |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- API 명세서: [`docs/api_specification.md`](../../../docs/api_specification.md)
- react-native-vision-camera 공식 문서: https://react-native-vision-camera.com/
