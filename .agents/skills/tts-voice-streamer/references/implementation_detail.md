# TTS Voice Streamer - 구현 상세 레퍼런스

## 1. 오디오 포맷 및 인코딩 설계

### 1.1 WAV 포맷 사양

| 항목 | 값 | 근거 |
|------|-----|------|
| 샘플레이트 | 24,000 Hz | Kokoro-82M 기본 출력, 음성에 충분 |
| 비트 뎁스 | 16-bit PCM | 모바일 호환성 최적 |
| 채널 | Mono (1ch) | 서버에서 Mono  앱에서 Stereo Panning 처리 |
| 평균 파일 크기 | ~48KB/초 | 24000 × 2bytes × 1ch |

### 1.2 base64 인코딩 오버헤드

- base64 인코딩 시 원본 대비 약 33% 크기 증가
- 10초 안내 음성: ~480KB(WAV)  ~640KB(base64)
- WebSocket 전송 시 JSON 래핑으로 추가 ~1KB
- 총 예상 전송 크기: 짧은 안내(3초) 약 200KB, 긴 안내(10초) 약 650KB

### 1.3 대안: 청크 스트리밍 (대용량 안내 시)

10초 이상의 긴 안내문은 청크 단위로 분할 전송 고려:

```python
CHUNK_DURATION_SECONDS = 2  # 2초 단위 청크
CHUNK_SIZE = 24000 * 2 * CHUNK_DURATION_SECONDS  # 96,000 bytes

async def send_audio_chunked(websocket, audio_data, message_id):
    total_chunks = len(audio_data) // CHUNK_SIZE + 1
    for i in range(total_chunks):
        chunk = audio_data[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
        await websocket.send_json({
            "type": "audio_chunk",
            "message_id": message_id,
            "chunk_index": i,
            "total_chunks": total_chunks,
            "audio_base64": base64.b64encode(chunk).decode(),
            "is_last": i == total_chunks - 1
        })
```

## 2. 중복 억제 알고리즘 상세

### 2.1 Redis 키 설계

```
키 패턴: suppress:{device_id}:{class_name}
예시:   suppress:device_abc123:bicycle
TTL:    60초 (기본값)
```

### 2.2 위험도별 TTL 차등 적용

| 위험도 | TTL | 이유 |
|--------|-----|------|
| high | 30초 | 위험 객체는 자주 재안내 필요 |
| medium | 60초 | 기본 억제 시간 |
| low | 120초 | 낮은 위험도는 빈번한 안내 불필요 |

```python
TTL_BY_SEVERITY = {
    "high": 30,
    "medium": 60,
    "low": 120
}

async def suppress_event_with_severity(
    redis_bus, device_id, class_name, severity
):
    ttl = TTL_BY_SEVERITY.get(severity, 60)
    key = f"suppress:{device_id}:{class_name}"
    if await redis_bus.exists(key):
        return True  # 억제 중
    await redis_bus.setex(key, ttl, "1")
    return False
```

### 2.3 같은 클래스 + 다른 방향 예외

동일 클래스라도 방향이 다르면 별도 안내:

```python
# 방향 포함 키
key = f"suppress:{device_id}:{class_name}:{direction}"
# 예: suppress:dev123:car:left  vs  suppress:dev123:car:right
```

## 3. Stereo Panning 매핑 상세

### 3.1 YOLO bbox  Panning 계산

```python
def bbox_to_panning(bbox_center_x: float, frame_width: int) -> float:
    """
    YOLO 감지 bbox 중심점 X좌표를 Stereo Panning 값으로 변환
    
    카메라 프레임 기준:
    - 좌측 끝 (x=0)      panning = -1.0
    - 중앙   (x=width/2)  panning = 0.0
    - 우측 끝 (x=width)   panning = +1.0
    """
    normalized = (bbox_center_x / frame_width) * 2.0 - 1.0
    # -1.0 ~ 1.0 범위로 클램핑
    return max(-1.0, min(1.0, normalized))
```

### 3.2 방향 문자열  Panning 매핑표

| 방향 | panning 값 | 비고 |
|------|-----------|------|
| `far_left` | -1.0 | 완전 좌측 |
| `left` | -0.7 | 좌측 강조 |
| `slight_left` | -0.4 | 약간 좌측 |
| `center` | 0.0 | 정면 |
| `slight_right` | 0.4 | 약간 우측 |
| `right` | 0.7 | 우측 강조 |
| `far_right` | 1.0 | 완전 우측 |

## 4. 발화 속도 및 음성 프리셋

### 4.1 시각장애인 맞춤 발화 속도

| 상황 | speed 값 | 이유 |
|------|----------|------|
| 위험 경고 (high) | 0.85 | 약간 느리지만 긴급함 전달 |
| 일반 안내 (medium/low) | 0.90 | 명확한 청취 보장 |
| 경로 안내 | 0.80 | 복잡한 방향 정보 이해 시간 확보 |
| 도착 안내 | 0.95 | 짧고 명확한 안내 |

### 4.2 음성 프리셋

```python
VOICE_PRESETS = {
    "ko_female": {
        "description": "한국어 여성 음성 (기본)",
        "pitch": 1.0,
        "energy": 0.8
    },
    "ko_male": {
        "description": "한국어 남성 음성 (설정 변경 가능)",
        "pitch": 0.85,
        "energy": 0.75
    }
}
```

## 5. 에러 시나리오별 폴백 매트릭스

| 장애 상황 | 1차 대응 | 2차 대응 | 3차 대응 |
|-----------|----------|----------|----------|
| Kokoro-82M GPU 실패 | CPU 모드 전환 | Coqui TTS 폴백 | 에러 로그 + 앱 내장 TTS 알림 |
| Kokoro-82M CPU 실패 | Coqui TTS 폴백 | 앱 내장 TTS 전환 | 텍스트만 전달 |
| WebSocket 끊김 | 재연결 시도 (3회) | 앱 내장 TTS 자동 전환 | 텍스트 스크린리더 공지 |
| Redis 연결 실패 | 중복억제 없이 전송 | 인메모리 캐시 폴백 | 로그 경고 |
| 오디오 디코딩 실패 (앱) | 재요청 1회 | 내장 TTS 폴백 | 스크린리더 텍스트 공지 |
| 오디오 재생 실패 (앱) | 내장 TTS 폴백 | 스크린리더 텍스트 공지 | 햅틱만 출력 |

## 6. WebSocket 메시지 프로토콜

### 6.1 서버  앱 메시지 타입

```json
// 일반 오디오 안내
{
  "type": "audio_guidance",
  "text": "왼쪽 3미터 전방에 자전거가 접근 중입니다",
  "audio_base64": "UklGRi4AA...",
  "severity": "high",
  "direction": "left",
  "panning": -0.7,
  "timestamp": 1719000000.0
}

// 청크 오디오 (긴 안내)
{
  "type": "audio_chunk",
  "message_id": "msg_abc123",
  "chunk_index": 0,
  "total_chunks": 5,
  "audio_base64": "UklGRi4AA...",
  "is_last": false
}

// TTS 실패 시 텍스트 전용
{
  "type": "text_only_guidance",
  "text": "전방 5미터 계단 주의",
  "severity": "medium",
  "reason": "tts_engine_error"
}
```

### 6.2 앱  서버 피드백

```json
// 오디오 수신 확인
{
  "type": "audio_ack",
  "message_id": "msg_abc123",
  "played": true
}

// 앱 TTS 모드 전환 알림
{
  "type": "tts_mode_change",
  "mode": "local_backup",
  "reason": "websocket_instability"
}
```

## 7. 테스트 시나리오

### 7.1 단위 테스트

| 테스트 | 검증 포인트 |
|--------|------------|
| `test_tts_generate_korean` | 한글 텍스트  WAV 바이트 정상 반환 |
| `test_tts_ttfb_under_200ms` | TTFB 200ms 미만 확인 |
| `test_base64_encoding` | WAV  base64  디코딩 무손실 확인 |
| `test_redis_suppression` | 60초 내 동일 이벤트 억제 확인 |
| `test_panning_calculation` | 방향별 panning 값 정확도 |

### 7.2 통합 테스트

| 테스트 | 검증 포인트 |
|--------|------------|
| `test_e2e_guidance_to_audio` | 6단계  TTS  WebSocket  앱 재생 전체 흐름 |
| `test_backup_tts_fallback` | 서버 TTS 실패 시 내장 TTS 자동 전환 |
| `test_haptic_on_high_severity` | high 위험도  햅틱 진동 동시 출력 |
| `test_accessibility_announce` | 스크린리더 공지 정상 호출 |

## 8. 설정 파일 (Config)

```python
# backend/config/tts_config.py

TTS_CONFIG = {
    "engine": "kokoro",          # "kokoro" | "coqui"
    "model": "kokoro-82m",
    "device": "cuda",            # "cuda" | "cpu"
    "sample_rate": 24000,
    "default_voice": "ko_female",
    "default_speed": 0.9,
    "high_severity_speed": 0.85,
    
    "redis": {
        "url": "redis://localhost:6379",
        "suppress_ttl_default": 60,
        "suppress_ttl_high": 30,
        "suppress_ttl_low": 120
    },
    
    "websocket": {
        "chunk_size_seconds": 2,
        "max_audio_duration": 30,
        "reconnect_attempts": 3,
        "reconnect_delay_ms": 1000
    }
}
```
