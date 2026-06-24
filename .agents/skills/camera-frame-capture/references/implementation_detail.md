# Camera Frame Capture — 상세 구현 레퍼런스

## 1. 이미지 파이프라인 상세

### 1.1 전체 데이터 흐름

```
┌─────────────────────────────────────────────────────────┐
│  [앱] 카메라 센서                                       │
│  ┌──────────────────────────────────────────┐           │
│  │  1. Camera.takePhoto()                   │           │
│  │      PhotoFile 객체                      │           │
│  │     qualityPrioritization: 'speed'       │           │
│  │     flash: 'off'                         │           │
│  │     enableShutterSound: false            │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  2. photo.toBase64()                     │           │
│  │      JPEG base64 문자열                  │           │
│  │     크기: 약 30-50KB                      │           │
│  │     해상도: 디바이스 기본값                  │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  3. JSON 조립 (DetectionEvent)           │           │
│  │     event_id: "evt-{ts}-{rand}"          │           │
│  │     thumbnail_jpeg_b64: base64           │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  4. WebSocket.send(JSON.stringify(...))  │           │
│  │     바이너리 대신 텍스트 프레임 사용         │           │
│  └──────────────┬───────────────────────────┘           │
└─────────────────┼───────────────────────────────────────┘
                  │  네트워크 (Wi-Fi / LTE)
┌─────────────────▼───────────────────────────────────────┐
│  [서버] FastAPI WebSocket Handler                       │
│  ┌──────────────────────────────────────────┐           │
│  │  5. ws.receive_text()                    │           │
│  │      raw JSON 문자열                     │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  6. json.loads(raw)                      │           │
│  │      Python dict                        │           │
│  │     type == "detection" 확인              │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  7. base64.b64decode(b64_str)            │           │
│  │      jpeg_bytes (바이트 배열)             │           │
│  │     크기 확인: len(jpeg_bytes) / 1024     │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  8. np.frombuffer(jpeg_bytes, np.uint8)  │           │
│  │      1차원 numpy 배열                    │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  9. cv2.imdecode(np_buffer, IMREAD_COLOR)│           │
│  │      3채널 BGR numpy 배열                │           │
│  │     shape: (height, width, 3)            │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  10. cv2.resize(frame, (640, 640))       │           │
│  │       YOLO26 입력 크기로 통일            │           │
│  │      interpolation: INTER_LINEAR         │           │
│  │      최종 shape: (640, 640, 3)           │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  11. cv2.imencode('.jpg', frame)         │           │
│  │       JPEG 바이트 재인코딩               │           │
│  │       .tobytes().hex() 문자열 변환       │           │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│  ┌──────────────▼───────────────────────────┐           │
│  │  12. redis.xadd("risk.events", {...})    │           │
│  │       3단계 YOLO Worker가 소비           │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 이미지 크기/품질 계산

| 항목 | 값 | 설명 |
|------|-----|------|
| 원본 해상도 | 디바이스 의존 (예: 1920x1080) | 후면 카메라 기본 해상도 |
| JPEG 품질 | speed 우선 (약 50-70%) | qualityPrioritization: 'speed' |
| base64 인코딩 팽창률 | ×1.33 | 3바이트  4문자 |
| 원본 JPEG 크기 | 약 30-50KB | 저품질 JPEG |
| base64 문자열 크기 | 약 40-67KB | 원본 × 1.33 |
| 목표 리사이즈 | 640×640 | YOLO26 표준 입력 |
| 리사이즈 후 JPEG 크기 | 약 20-40KB | 640×640 재인코딩 |

### 1.3 프레임 레이트 설계 근거

```
1fps를 선택한 이유:
- 보행 속도: 약 1.2m/s (시각장애인 평균 보행 속도)
- 1초당 1.2m 이동  1프레임당 약 1.2m 범위 변화
- 위험 감지에 충분한 갱신 주기 (차량, 장애물 등)
- 네트워크 대역폭 절약 (50KB × 1fps = 50KB/s)
- 배터리 소모 최소화 (카메라 센서 활성화 빈도 감소)

2fps까지 올릴 수 있는 경우:
- Wi-Fi 환경 (안정적 대역폭)
- 서버 부하가 낮은 경우
- 빠른 보행/주행 시 정확도 향상 필요 시
```

## 2. React Native 구현 상세

### 2.1 react-native-vision-camera v4 API 정리

```typescript
// ── 핵심 임포트 ──
import {
  Camera,                // 카메라 UI 컴포넌트
  useCameraDevice,       // 카메라 디바이스 선택 훅
  useCameraPermission,   // 권한 관리 훅
  PhotoFile,             // 캡처된 사진 타입
  CameraDevice,          // 카메라 디바이스 타입
} from 'react-native-vision-camera';

// ── useCameraDevice ──
const device = useCameraDevice('back');     // 후면 카메라
const device = useCameraDevice('front');    // 전면 카메라
// 반환: CameraDevice | undefined

// ── useCameraPermission ──
const { hasPermission, requestPermission } = useCameraPermission();
// hasPermission: boolean — 현재 권한 상태
// requestPermission: () => Promise<boolean> — 권한 요청

// ── Camera 컴포넌트 Props ──
<Camera
  ref={cameraRef}
  device={device}           // 카메라 디바이스 (필수)
  isActive={true}           // 카메라 활성화 (필수)
  photo={true}              // 사진 캡처 활성화
  video={false}             // 비디오 비활성화 (불필요)
  audio={false}             // 오디오 비활성화
  style={StyleSheet.absoluteFill}
  orientation="portrait"    // 세로 모드 고정
  enableZoomGesture={false} // 줌 제스처 비활성화
/>

// ── takePhoto 옵션 ──
const photo = await cameraRef.current.takePhoto({
  qualityPrioritization: 'speed',  // 'speed' | 'balanced' | 'quality'
  flash: 'off',                     // 'off' | 'on' | 'auto'
  enableShutterSound: false,        // 셔터음 비활성화
  enableAutoDistortionCorrection: false,  // 왜곡 보정 비활성화 (속도)
  enableAutoStabilization: false,   // 흔들림 보정 비활성화 (속도)
});

// ── PhotoFile 속성 ──
photo.path      // string: 파일 경로
photo.width     // number: 이미지 너비
photo.height    // number: 이미지 높이
photo.toBase64() // Promise<string>: base64 인코딩
```

### 2.2 GPS 위치 정보 추가 (선택 사항)

```typescript
// src/hooks/useLocation.ts
import * as Location from 'expo-location';
import { useEffect, useState } from 'react';

export function useLocation() {
  const [location, setLocation] = useState<{
    lat: number;
    lon: number;
    accuracy: number;
  } | null>(null);

  useEffect(() => {
    let subscription: Location.LocationSubscription | null = null;

    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;

      subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 5000,       // 5초마다 갱신
          distanceInterval: 2,      // 2m 이동 시 갱신
        },
        (loc) => {
          setLocation({
            lat: loc.coords.latitude,
            lon: loc.coords.longitude,
            accuracy: loc.coords.accuracy ?? 0,
          });
        }
      );
    })();

    return () => {
      subscription?.remove();
    };
  }, []);

  return location;
}
```

### 2.3 배터리 최적화 전략

```typescript
// src/hooks/useBatteryOptimizedCapture.ts
import { useEffect, useRef, useState } from 'react';
import * as Battery from 'expo-battery';

/**
 * 배터리 잔량에 따라 캡처 fps를 자동 조절하는 훅.
 * - 배터리 > 50%: 1fps
 * - 배터리 20-50%: 0.5fps (2초마다)
 * - 배터리 < 20%: 0.33fps (3초마다)
 */
export function useBatteryOptimizedFps(): number {
  const [fps, setFps] = useState(1);

  useEffect(() => {
    const checkBattery = async () => {
      const level = await Battery.getBatteryLevelAsync();

      if (level > 0.5) {
        setFps(1);
      } else if (level > 0.2) {
        setFps(0.5);
      } else {
        setFps(0.33);
      }
    };

    checkBattery();
    const interval = setInterval(checkBattery, 60000); // 1분마다 확인
    return () => clearInterval(interval);
  }, []);

  return fps;
}
```

## 3. 서버 측 구현 상세

### 3.1 frame_processor.py 전체 코드 (완성판)

```python
# server/api/frame_processor.py
import base64
import logging
import time
import numpy as np
import cv2
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

TARGET_SIZE = (640, 640)
MAX_FRAME_SIZE_KB = 500     # 500KB 초과 프레임은 거부
MIN_FRAME_SIZE_KB = 1       # 1KB 미만 프레임은 거부 (손상된 데이터)

@dataclass
class ProcessedFrame:
    """디코딩 및 리사이징 완료된 프레임"""
    event_id: str
    device_id: str
    frame: np.ndarray          # (640, 640, 3) BGR
    original_size: tuple       # (height, width)
    size_kb: float             # 원본 JPEG 크기 (KB)
    processing_time_ms: float  # 처리 소요 시간 (ms)

async def decode_frame(payload: dict) -> Optional[ProcessedFrame]:
    """
    detection 이벤트의 payload에서 JPEG base64  OpenCV numpy 배열로 변환.

    반환: ProcessedFrame 또는 None (실패 시)
    """
    start_time = time.time()
    event_id = payload.get("event_id", "unknown")
    device_id = payload.get("device_id", "unknown")
    b64_str = payload.get("thumbnail_jpeg_b64")

    # ── 유효성 검사 ──
    if not b64_str:
        logger.warning(f"[프레임] base64 데이터 없음: event_id={event_id}")
        return None

    if not isinstance(b64_str, str):
        logger.warning(f"[프레임] base64가 문자열이 아님: event_id={event_id}, type={type(b64_str)}")
        return None

    try:
        # ── 1) base64 디코딩 ──
        jpeg_bytes = base64.b64decode(b64_str)
        size_kb = len(jpeg_bytes) / 1024

        # 크기 검증
        if size_kb > MAX_FRAME_SIZE_KB:
            logger.warning(f"[프레임] 크기 초과: event_id={event_id}, size={size_kb:.1f}KB > {MAX_FRAME_SIZE_KB}KB")
            return None
        if size_kb < MIN_FRAME_SIZE_KB:
            logger.warning(f"[프레임] 크기 부족 (손상 의심): event_id={event_id}, size={size_kb:.1f}KB")
            return None

        # ── 2) numpy 배열 변환 ──
        np_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)

        # ── 3) OpenCV 이미지 복원 ──
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)

        if frame is None:
            logger.error(f"[프레임] cv2.imdecode 실패 (JPEG 손상): event_id={event_id}")
            return None

        # 채널 수 확인 (BGR 3채널이어야 함)
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            logger.error(f"[프레임] 잘못된 이미지 형식: shape={frame.shape}")
            return None

        original_size = (frame.shape[0], frame.shape[1])

        # ── 4) 리사이징 ──
        frame_resized = cv2.resize(frame, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"[프레임] 처리 완료: event_id={event_id}, "
            f"원본={original_size[1]}x{original_size[0]}, "
            f"리사이즈={TARGET_SIZE[0]}x{TARGET_SIZE[1]}, "
            f"크기={size_kb:.1f}KB, "
            f"소요={processing_time:.1f}ms"
        )

        return ProcessedFrame(
            event_id=event_id,
            device_id=device_id,
            frame=frame_resized,
            original_size=original_size,
            size_kb=size_kb,
            processing_time_ms=processing_time,
        )

    except base64.binascii.Error as e:
        logger.error(f"[프레임] base64 디코딩 오류: event_id={event_id}, {e}")
        return None
    except cv2.error as e:
        logger.error(f"[프레임] OpenCV 오류: event_id={event_id}, {e}")
        return None
    except MemoryError:
        logger.critical(f"[프레임] 메모리 부족: event_id={event_id}")
        return None
    except Exception as e:
        logger.error(f"[프레임] 예기치 않은 오류: event_id={event_id}, {e}")
        return None


def frame_to_redis_data(processed: ProcessedFrame) -> dict:
    """
    ProcessedFrame을 Redis xadd에 넘길 dict로 변환한다.
    프레임은 JPEG로 재인코딩  hex 문자열로 저장.
    """
    # JPEG 재인코딩 (품질 80%)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
    success, jpeg_encoded = cv2.imencode('.jpg', processed.frame, encode_params)

    if not success:
        logger.error(f"[Redis] JPEG 재인코딩 실패: event_id={processed.event_id}")
        return {}

    frame_hex = jpeg_encoded.tobytes().hex()

    return {
        "event_id": processed.event_id,
        "device_id": processed.device_id,
        "frame": frame_hex,
        "frame_width": str(TARGET_SIZE[0]),
        "frame_height": str(TARGET_SIZE[1]),
        "original_width": str(processed.original_size[1]),
        "original_height": str(processed.original_size[0]),
        "size_kb": str(round(processed.size_kb, 1)),
        "processing_ms": str(round(processed.processing_time_ms, 1)),
    }
```

### 3.2 Redis에서 프레임 복원하기 (3단계 YOLO Worker용 참고)

```python
# 3단계에서 사용할 프레임 복원 코드 (참고용)

async def restore_frame_from_redis(event_data: dict) -> np.ndarray:
    """
    Redis에 저장된 hex 문자열  OpenCV numpy 배열로 복원.
    3단계 YOLO Worker에서 호출.
    """
    frame_hex = event_data.get("frame", "")
    jpeg_bytes = bytes.fromhex(frame_hex)
    np_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    return frame  # shape: (640, 640, 3)
```

## 4. 에러 처리 및 엣지 케이스

### 4.1 앱 측 에러 처리

| 상황 | 처리 방법 | 구현 위치 |
|------|-----------|-----------|
| 카메라 권한 거부 | 권한 안내 화면 표시, TTS 음성 안내 | CameraView.tsx |
| 카메라 디바이스 없음 | 에러 화면 표시, 앱 비정상 종료 방지 | CameraView.tsx |
| takePhoto() 실패 | 에러 로그, 다음 간격에 재시도 | useCameraCapture.ts |
| base64 변환 실패 | null 반환, 해당 프레임 스킵 | useCameraCapture.ts |
| WebSocket 미연결 시 캡처 | 캡처 중지 (status !== 'connected') | CameraView.tsx |
| 앱 백그라운드 전환 | isActive=false, 캡처 중지 | AppState 리스너 |
| 메모리 부족 | JPEG 품질 낮춤, 캡처 빈도 감소 | useBatteryOptimizedCapture.ts |

### 4.2 서버 측 에러 처리

| 상황 | 처리 방법 | 구현 위치 |
|------|-----------|-----------|
| base64 디코딩 실패 | error 응답 전송, 해당 이벤트 스킵 | frame_processor.py |
| JPEG 손상 (imdecode 실패) | error 응답 전송, 로그 경고 | frame_processor.py |
| 프레임 크기 초과 (>500KB) | 거부, 클라이언트에 품질 조정 요청 | frame_processor.py |
| Redis 연결 실패 | 프레임 임시 메모리 큐에 버퍼링, 재연결 시 발행 | ws_routes.py |
| numpy/OpenCV 메모리 오류 | MemoryError 캐치, 로그 critical | frame_processor.py |
| 동시 다수 프레임 수신 | asyncio.Queue로 순차 처리 | ws_routes.py |

### 4.3 앱 백그라운드 전환 처리

```typescript
// src/hooks/useAppState.ts
import { useEffect, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';

/**
 * 앱 상태(포그라운드/백그라운드) 변화 감지 훅.
 * 백그라운드 전환 시 카메라 비활성화, 복귀 시 재활성화.
 */
export function useAppState(
  onForeground: () => void,
  onBackground: () => void
) {
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    const subscription = AppState.addEventListener(
      'change',
      (nextState: AppStateStatus) => {
        if (
          appState.current.match(/inactive|background/) &&
          nextState === 'active'
        ) {
          onForeground();
        } else if (
          appState.current === 'active' &&
          nextState.match(/inactive|background/)
        ) {
          onBackground();
        }
        appState.current = nextState;
      }
    );

    return () => subscription.remove();
  }, [onForeground, onBackground]);
}
```

## 5. 성능 최적화

### 5.1 네트워크 대역폭 최적화

```
전송 데이터 크기 분석:
─────────────────────────
기본 JSON 오버헤드:   ~200 bytes (type, event_id, device_id, timestamp 등)
base64 이미지 데이터: ~40-67 KB (30-50KB JPEG × 1.33 base64 팽창)
─────────────────────────
총 전송량 (1fps):     ~50 KB/s
총 전송량 (2fps):     ~100 KB/s
총 전송량 (분당):     ~3 MB/min (1fps 기준)

LTE 환경 (약 10Mbps):   충분한 여유
Wi-Fi 환경 (약 50Mbps):  충분한 여유
3G 환경 (약 1Mbps):      1fps는 가능, 2fps는 위험
```

### 5.2 이미지 품질 vs 크기 트레이드오프

```python
# 서버 측에서 이미지 크기가 크면 클라이언트에 품질 조정 요청
QUALITY_THRESHOLDS = {
    "normal": 70,      # 기본 JPEG 품질
    "low_bandwidth": 40,    # 저대역폭 시
    "critical": 20,    # 극도로 낮은 대역폭 시
}

# 클라이언트에 품질 조정 메시지 전송
await ws.send_json({
    "type": "config",
    "quality_hint": "low_bandwidth",
    "target_size_kb": 30,
})
```

### 5.3 프레임 드롭 전략 (서버 과부하 시)

```python
# server/api/frame_throttle.py
import time
from collections import defaultdict

class FrameThrottle:
    """
    디바이스별 프레임 수신 속도를 제한한다.
    서버 과부하 시 오래된 프레임을 드롭하고 최신 프레임만 처리.
    """

    def __init__(self, min_interval_ms: int = 800):
        self.min_interval = min_interval_ms / 1000  # 초 단위
        self.last_frame_time: dict[str, float] = defaultdict(float)

    def should_process(self, device_id: str) -> bool:
        """현재 프레임을 처리해야 하는지 판단."""
        now = time.time()
        elapsed = now - self.last_frame_time[device_id]

        if elapsed < self.min_interval:
            return False  # 너무 빠름  드롭

        self.last_frame_time[device_id] = now
        return True

# 사용 예:
throttle = FrameThrottle(min_interval_ms=800)

if not throttle.should_process(device_id):
    logger.debug(f"[프레임 드롭] device_id={device_id}")
    continue  # 프레임 무시
```

## 6. 테스트 코드

### 6.1 서버 측 프레임 디코딩 단위 테스트

```python
# tests/test_frame_processor.py
import pytest
import base64
import numpy as np
import cv2
from backend.gateway.frame_processor import decode_frame, frame_to_redis_data

@pytest.fixture
def sample_frame_payload():
    """테스트용 640x480 빨간 이미지  base64 payload 생성"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :, 2] = 255  # 빨간색 (BGR)
    _, jpeg = cv2.imencode('.jpg', frame)
    b64 = base64.b64encode(jpeg.tobytes()).decode('utf-8')
    return {
        "event_id": "evt-test-001",
        "device_id": "dev-test",
        "timestamp": "2025-06-21T14:30:00",
        "thumbnail_jpeg_b64": b64,
    }

@pytest.mark.asyncio
async def test_decode_frame_success(sample_frame_payload):
    """정상 프레임 디코딩 테스트"""
    result = await decode_frame(sample_frame_payload)
    assert result is not None
    assert result.event_id == "evt-test-001"
    assert result.device_id == "dev-test"
    assert result.frame.shape == (640, 640, 3)
    assert result.size_kb > 0

@pytest.mark.asyncio
async def test_decode_frame_no_base64():
    """base64 데이터 없을 때 None 반환"""
    payload = {"event_id": "evt-test-002", "device_id": "dev-test"}
    result = await decode_frame(payload)
    assert result is None

@pytest.mark.asyncio
async def test_decode_frame_invalid_base64():
    """잘못된 base64 데이터"""
    payload = {
        "event_id": "evt-test-003",
        "device_id": "dev-test",
        "thumbnail_jpeg_b64": "NOT_VALID_BASE64!!!"
    }
    result = await decode_frame(payload)
    assert result is None

@pytest.mark.asyncio
async def test_decode_frame_corrupted_jpeg():
    """손상된 JPEG 데이터"""
    corrupted = base64.b64encode(b"not a jpeg image at all" * 100).decode()
    payload = {
        "event_id": "evt-test-004",
        "device_id": "dev-test",
        "thumbnail_jpeg_b64": corrupted,
    }
    result = await decode_frame(payload)
    assert result is None

def test_frame_to_redis_data(sample_frame_payload):
    """Redis 저장용 데이터 변환 테스트"""
    import asyncio
    result = asyncio.run(decode_frame(sample_frame_payload))
    assert result is not None

    redis_data = frame_to_redis_data(result)
    assert redis_data["event_id"] == "evt-test-001"
    assert redis_data["frame_width"] == "640"
    assert redis_data["frame_height"] == "640"
    assert len(redis_data["frame"]) > 0  # hex 문자열
```

### 6.2 통합 테스트 (WebSocket + 프레임 전송)

```python
# tests/test_frame_pipeline.py
import pytest
import base64
import json
import numpy as np
import cv2
from httpx import AsyncClient, ASGITransport
from httpx_ws import aconnect_ws
from backend.gateway.main import app

@pytest.mark.asyncio
async def test_detection_frame_pipeline():
    """앱  서버: detection 이벤트 전송  ack 수신 전체 파이프라인 테스트"""
    # 테스트 이미지 생성
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    _, jpeg = cv2.imencode('.jpg', frame)
    b64 = base64.b64encode(jpeg.tobytes()).decode('utf-8')

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        async with aconnect_ws("/ws/detect?device_id=dev-001", client) as ws:
            # 1) welcome 수신
            welcome = await ws.receive_json()
            assert welcome["type"] == "welcome"

            # 2) hello 인증
            await ws.send_json({
                "type": "hello",
                "device_id": "dev-001",
                "token": "token-abc-001"
            })
            auth = await ws.receive_json()
            assert auth["type"] == "auth_ok"

            # 3) detection 이벤트 전송
            detection = {
                "type": "detection",
                "payload": {
                    "event_id": "evt-test-pipeline-001",
                    "device_id": "dev-001",
                    "timestamp": "2025-06-21T14:30:00",
                    "frame_id": 1,
                    "thumbnail_jpeg_b64": b64,
                    "detections": []
                }
            }
            await ws.send_json(detection)

            # 4) ack 수신 확인
            ack = await ws.receive_json()
            assert ack["type"] == "ack"
            assert ack["event_id"] == "evt-test-pipeline-001"
            assert "received_at" in ack
```

### 6.3 수동 테스트 스크립트 (Python)

```python
# tests/manual_test_frame.py
"""
수동 테스트: 로컬 웹캠  WebSocket  서버 전송
실행: python tests/manual_test_frame.py
"""
import asyncio
import websockets
import json
import base64
import cv2
import time

SERVER_URL = "ws://localhost:8000/ws/detect?device_id=dev-001"

async def test_webcam_to_server():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("웹캠 열기 실패")
        return

    async with websockets.connect(SERVER_URL) as ws:
        # welcome 수신
        welcome = json.loads(await ws.recv())
        print(f"[수신] {welcome}")

        # hello 인증
        await ws.send(json.dumps({
            "type": "hello",
            "device_id": "dev-001",
            "token": "token-abc-001"
        }))
        auth = json.loads(await ws.recv())
        print(f"[수신] {auth}")

        # 5프레임 전송 테스트
        for i in range(5):
            ret, frame = cap.read()
            if not ret:
                break

            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            b64 = base64.b64encode(jpeg.tobytes()).decode('utf-8')
            size_kb = len(jpeg.tobytes()) / 1024

            event = {
                "type": "detection",
                "payload": {
                    "event_id": f"evt-{int(time.time()*1000)}-{i:03d}",
                    "device_id": "dev-001",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "frame_id": i + 1,
                    "thumbnail_jpeg_b64": b64,
                    "detections": []
                }
            }

            start = time.time()
            await ws.send(json.dumps(event))
            ack = json.loads(await ws.recv())
            rtt = (time.time() - start) * 1000

            print(f"[프레임 {i+1}] 크기={size_kb:.1f}KB, RTT={rtt:.1f}ms, ack={ack['event_id']}")
            await asyncio.sleep(1)  # 1fps

    cap.release()
    print("테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_webcam_to_server())
```

## 7. 다음 단계 연결 (3단계: YOLO 객체 감지)

이 단계에서 Redis `risk.events` 스트림에 저장된 프레임은 3단계(YOLO 객체 감지)에서 소비된다.

```python
# 3단계에서 읽는 방식 (참고):
events = await redis.xread({"risk.events": "$"}, count=1, block=1000)

for stream, messages in events:
    for msg_id, data in messages:
        frame_hex = data["frame"]
        jpeg_bytes = bytes.fromhex(frame_hex)
        np_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)

        # YOLO26 추론
        results = yolo_model(frame)
        # ... 후속 처리 ...
```
