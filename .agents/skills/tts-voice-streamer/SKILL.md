---
name: tts-voice-streamer
description: |
  6단계 LangGraph에서 생성된 최종 안내문을 이중 채널로 출력한다.
  인지 경로: 로컬 TTS(Kokoro/Coqui)로 한글 음성 합성 후 base64 MP3로 WebSocket 전송.
  반사 경로: 사전합성 고정 클립을 alert_id로 즉시 재생(선점, 실시간 합성 금지).
  TTSService 추상화로 출력 규격을 통일하고 gpt-4o-mini 핫스왑을 지원한다.
---

# TTS Voice Streamer (7단계: 음성 안내 출력, 이중 채널)

> **작성일**: 2026-06-24
> **버전**: v0.2.0
> **설계 기준**: `docs/minchodan_design_note.md` 7단계 (v1.1 이중 채널 반영)
> **코딩 패턴 준수**: [`docs/course_codebase_guide.md`](../../../docs/course_codebase_guide.md) 섹션 8, 16, 17.2

## 개요

최종 가이드를 한글 음성으로 변환·재생합니다. v1.1 설계에 따라 **이중 채널**(반사=사전합성, 인지=실시간 합성)로 분리합니다. 화면을 못 보는 사용자에게 귀로 전달하는 것이 핵심입니다.

## v1.1 핵심 변경 사항

| 항목      | 기존            | v1.1                                                 |
| --------- | --------------- | ---------------------------------------------------- |
| 반사 음성 | 실시간 TTS 합성 | **사전합성 고정 클립**(앱 번들), 실시간 합성 금지    |
| 선점      | 없음            | **반사 음성이 인지 음성을 중단시키고 재생**(preempt) |
| WS 타입   | 단일 alert      | **반사 = 고우선 타입**, 인지 = 일반 가이드           |
| 추상화    | 없음            | **TTSService** 추상화, MP3/WAV 규격 통일             |
| Whisper   | 7단계에 혼재    | **Whisper는 STT 전용**, 7단계(출력)에 등장 안 함     |

## 아키텍처

```
[6단계 LangGraph]  guidance_text

[7-인지] 로컬 TTS(Kokoro/Coqui) generate()  base64 MP3  WS 스트리밍  단말 Web Audio 재생

[3단계 Gate]  alert_id

[7-반사] 단말 사전합성 고정 클립 즉시 재생 (선점, 실시간 TTS 미경유)

중복 억제: setex(suppress:alert_id, 60)
햡틱: Haptics + announceForAccessibility
```

## 기술 스택

| 구분                 | 스택               | 용도                  |
| -------------------- | ------------------ | --------------------- |
| 로컬 TTS (인지)      | Kokoro-82M / Coqui | 실시간 한글 음성 합성 |
| 사전합성 클립 (반사) | MP3 파일 (앱 번들) | 즉시 재생             |
| 서버 프레임워크      | FastAPI + Uvicorn  | WebSocket             |
| 메시지 버스          | Redis SETEX        | 중복 억제 (60초)      |
| 모바일 오디오        | Web Audio API      | 인지 음성 재생        |
| 모바일 TTS 백업      | react-native-tts   | 서버 TTS 실패 시 우회 |
| 접근성               | AccessibilityInfo  | VoiceOver/TalkBack    |
| 햅틱                 | expo-haptics       | 위험도 기반 진동      |

## 디렉토리 구조 (Minchodan 기준)

```
server/tts/
├── realtime_tts.py           # 인지 경로: Kokoro/Coqui generate()  base64 MP3
├── reflex_clip_sender.py     # 반사 경로: alert_id  사전합성 클립 WS 고우선 전송
├── suppressor.py             # Redis setex(suppress:…, 60) 중복 억제
└── tts_service.py            # TTSService 추상화, MP3/WAV 규격 통일

client/src/services/
├── audioPlayer.ts            # decodeAudioData() Web Audio 재생 (인지)
├── reflexClipPlayer.ts       # 반사 클립 즉시 재생 (선점 로직)
client/src/utils/
└── haptics.ts                # Haptics + announceForAccessibility
client/assets/reflex_clips/   # 사전합성 클립 앱 번들 (server/data와 동기화)
```

## 핵심 구현 절차 (서버 측)

### 단계 7-1. 인지 경로: 실시간 TTS 합성

```python
# -*- coding: utf-8 -*-
# server/tts/realtime_tts.py
import base64
import io
import logging
import sys

import kokoro
import soundfile as sf

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logger = logging.getLogger(__name__)

class RealtimeTTS:
    """인지 경로: Kokoro/Coqui 실시간 음성 합성"""
    def __init__(self):
        self.engine = None
        self._initialized = False

    async def initialize(self):
        try:
            self.engine = kokoro.KokoroTTS(model="kokoro-82m", lang="ko", device="cuda")
            self._initialized = True
            logger.info("Kokoro TTS 초기화 완료 (GPU)")
        except Exception as e:
            logger.warning(f"Kokoro GPU 실패, CPU 시도: {e}")
            self.engine = kokoro.KokoroTTS(model="kokoro-82m", lang="ko", device="cpu")
            self._initialized = True

    async def generate(self, text: str, voice: str = "ko", speed: float = 0.9) -> str:
        """텍스트  base64 MP3. TTFB < 200ms 목표"""
        audio_array = self.engine.synthesize(text=text, voice=voice, speed=speed)
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, 24000, format="WAV")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")
```

### 단계 7-2. 반사 경로: 사전합성 클립 전송

```python
# -*- coding: utf-8 -*-
# server/tts/reflex_clip_sender.py
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logger = logging.getLogger(__name__)

# 사전합성 클립 매핑 (앱 번들과 동기화)
CLIP_MAP = {
    "high_front": "reflex_clips/high_front.mp3",
    "high_left": "reflex_clips/high_left.mp3",
    "high_right": "reflex_clips/high_right.mp3",
    "high_stop": "reflex_clips/high_stop.mp3",
    "surface_crosswalk": "reflex_clips/surface_crosswalk.mp3",
    "surface_manhole": "reflex_clips/surface_manhole.mp3",
    "surface_stairs": "reflex_clips/surface_stairs.mp3",
    "surface_grating": "reflex_clips/surface_grating.mp3",
    "surface_braille_damaged": "reflex_clips/surface_braille_damaged.mp3",
}

async def send_reflex_clip(websocket, device_id, alert_id: str, direction: str, haptic: bool = True):
    """반사 경로: 사전합성 클립을 WS 고우선 타입으로 전송 (실시간 TTS 미경유)"""
    clip_path = CLIP_MAP.get(alert_id)
    if not clip_path:
        logger.warning(f"알 수 없는 alert_id: {alert_id}")
        return

    message = {
        "type": "alert_reflex",
        "event_id": f"reflex-{device_id}-{alert_id}",
        "alert_id": alert_id,
        "direction": direction,
        "risk_level": "high",
        "clip": clip_path,
        "haptic": haptic,
        "ts": time.time(),
    }
    await websocket.send_json(message)
    logger.info(f"[반사] 클립 전송: alert_id={alert_id}, direction={direction}")
```

### 단계 7-3. 중복 억제

```python
# -*- coding: utf-8 -*-
# server/tts/suppressor.py
import sys
import redis.asyncio as aioredis

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

class Suppressor:
    """Redis setex(suppress:…, 60) 중복 억제"""
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(redis_url)

    async def should_suppress(self, alert_id: str, ttl: int = 60) -> bool:
        key = f"suppress:{alert_id}"
        if await self.redis.exists(key): return True
        await self.redis.setex(key, ttl, "1")
        return False
```

### 단계 7-4. TTSService 추상화

```python
# -*- coding: utf-8 -*-
# server/tts/tts_service.py
import sys
from typing import Protocol

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

class TTSService(Protocol):
    """TTS 출력 규격 통일 추상화"""
    async def generate(self, text: str, voice: str, speed: float) -> str: ...
    def get_format(self) -> str: ...

class KokoroService:
    async def generate(self, text, voice="ko", speed=0.9): ...
    def get_format(self): return "mp3"

class CoquiService:
    async def generate(self, text, voice="ko", speed=0.9): ...
    def get_format(self): return "wav"

class OpenAITTSService:
    """post-MVP: OpenAI TTS 핫스왑"""
    async def generate(self, text, voice="ko", speed=0.9): raise NotImplementedError
    def get_format(self): return "mp3"
```

## 핵심 구현 절차 (React Native 앱 측)

### 단계 7-5. 인지 경로: Web Audio 재생

```typescript
// client/src/services/audioPlayer.ts
import { Buffer } from "buffer";

export class AudioPlayer {
  private audioContext: AudioContext | null = null;

  async initialize() {
    this.audioContext = new AudioContext({ sampleRate: 24000 });
  }

  async play(audioBase64: string, panning: number = 0) {
    if (!this.audioContext) await this.initialize();
    const arrayBuffer = Buffer.from(audioBase64, "base64").buffer;
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    const panner = this.audioContext.createStereoPanner();
    panner.pan.value = panning;
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(panner).connect(this.audioContext.destination);
    source.start();
  }
}
```

### 단계 7-6. 반사 경로: 사전합성 클립 선점 재생

```typescript
// client/src/services/reflexClipPlayer.ts
import { Audio } from "expo-av";

export class ReflexClipPlayer {
  private currentSound: Audio.Sound | null = null;

  async playPreempt(alertId: string, clipPath: string) {
    // 선점: 현재 재생 중인 인지 음성 중단
    if (this.currentSound) {
      await this.currentSound.stopAsync();
      await this.currentSound.unloadAsync();
      this.currentSound = null;
    }
    // 사전합성 클립 즉시 재생 (실시간 TTS 미경유)
    const { sound } = await Audio.Sound.createAsync({ uri: clipPath });
    this.currentSound = sound;
    await sound.playAsync();
  }
}
```

### 단계 7-7. 햅틱 + 접근성

```typescript
// client/src/utils/haptics.ts
import * as Haptics from "expo-haptics";
import { AccessibilityInfo } from "react-native";

export async function triggerHaptic(severity: "high" | "mid" | "low") {
  switch (severity) {
    case "high":
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      break;
    case "mid":
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      break;
    case "low":
      await Haptics.selectionAsync();
      break;
  }
}

export function announceForAccessibility(text: string) {
  AccessibilityInfo.announceForAccessibility(text);
}
```

## 선점 규칙 (비협상)

- 반사 음성은 인지 음성을 **중단시키고 재생**합니다.
- WS에서 반사 이벤트는 **별도 고우선 타입**(`alert_reflex`)으로 전송합니다.
- 반사 음성은 **실시간 TTS 합성을 금지**하며 사전합성 고정 클립만 사용합니다.

## 데이터 인터페이스

| 방향       | 페이로드                                  |
| ---------- | ----------------------------------------- |
| In (인지)  | 가이드 문장(String)                       |
| In (반사)  | `alert_id`                                |
| Out (인지) | 오디오 bytes(ArrayBuffer) — base64 MP3 WS |
| Out (반사) | 사전합성 클립 경로 — WS 고우선 타입       |

## 의존성·예외

- 선행 = 6단계(인지) / 3단계 게이트(반사). 파이프라인 종착.
- TTS 호출 실패/타임아웃 시 기기 내장 TTS로 우회(시스템 중단 금지).

## 테스트 체크리스트

| 항목                    | 기대 결과                          | 합격 기준           |
| ----------------------- | ---------------------------------- | ------------------- |
| 실시간 TTS 합성         | Kokoro/Coqui generate() base64 MP3 | TTFB < 200ms        |
| 단말 재생 성공          | Web Audio decodeAudioData() 재생   | 재생 확인           |
| **반사 클립 선점 재생** | 인지 음성 중단 후 반사 재생        | 선목 동작           |
| high 햅틱 동시 출력     | Haptics 동시 동작                  | 진동 확인           |
| 중복 억제               | setex(suppress:…, 60) 60초         | 60초 내 재전송 없음 |
| TTS 실패 우회           | 기기 내장 TTS로 우회               | 중단 없음           |
| **반사 클립 사전합성**  | 실시간 합성 미사용 확인            | 고정 클립만         |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- API 명세서: [`docs/api_specification.md`](../../../docs/api_specification.md) 4·5절
- 아키텍처 설계서: [`docs/architecture.md`](../../../docs/architecture.md) 5.7절
