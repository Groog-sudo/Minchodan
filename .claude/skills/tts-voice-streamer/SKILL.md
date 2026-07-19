---
name: tts-voice-streamer
description: |
  6단계 LangGraph에서 생성된 최종 안내문을 이중 채널로 출력한다.
  인지 경로: 로컬 TTS(Supertonic, 기본)로 한글 음성 합성 후 WS 바이너리 프레임(raw WAV bytes)으로 전송.
  반사 경로: 사전합성 고정 클립을 alert_id로 즉시 재생(선점, 실시간 합성 금지).
  TTSService 추상화로 출력 규격을 통일한다(Piper는 핫스왑 폴백으로 보존). 클라이언트 재생은 expo-audio.
---

# TTS Voice Streamer (7단계: 음성 안내 출력, 이중 채널)

> **작성일**: 2026-06-24
> **버전**: v0.4.1 (2026-07-19 단말 TTS 백업 `react-native-tts`→`expo-speech` 정정 + 이전 v0.4.0 이력 유지: 2026-07-09 실기기 TTS 절단 근본 원인 규명에 따른 전면 정정: 인지 TTS 엔진 Piper→Supertonic 교체, `audio_mp3_b64`→WS 바이너리 프레임 전환, iOS Hearing Protection 우회용 가이드 상시 재생 플레이어 도입)
> **설계 기준**: `docs/design/minchodan_design_note.md` 7단계 (v1.1 이중 채널 반영)
> **코딩 패턴 준수**: [`docs/dev-guides/course_codebase_guide.md`](../../../docs/dev-guides/course_codebase_guide.md) 섹션 8, 16, 17.2

> **2026-07-09 정정 요약 (중요, 엔진·전송 방식 모두 변경)**: 실기기 청취 검증 결과 Piper(pygoruut/자체
> 규칙 기반 G2P/espeak 음소화 모두 시도)가 흔한 음절을 발음에서 통째로 누락시키는 모델 자체 한계가
> 확인되어, **인지 TTS 기본 엔진을 Supertonic 3**(`SupertonicTTSService`, supertone-inc, MIT
> 라이선스, 99M 파라미터 ONNX)로 교체했다. `PiperTTSService`는 삭제하지 않고 `TTS_ENGINE=piper`로
> 즉시 되돌릴 수 있는 핫스왑 폴백으로 코드에 보존된다. 오디오 전송도 `audio_mp3_b64`(base64 JSON
> 필드)를 폐기하고, 카메라 프레임(client→server)에 이미 쓰이던 메타+바이너리 2단계 WS 프로토콜을
> 반대 방향(server→client)에 적용했다 - JSON 메타(`transport:"binary"`) 직후 raw WAV 바이트가
> 별도 바이너리 프레임으로 전송된다. 추가로 iOS Hearing Protection이 재생 "시작" 이벤트마다 볼륨을
> 제한하는 것을 우회하기 위해, 클라이언트는 매번 새 플레이어를 만들지 않고 무음 placeholder를 상시
> 재생 중인 단일 플레이어(`guideWarmPlayer`)의 소스만 `player.replace()`로 교체하는 방식으로
> 전환됐다(반사 비프 상시 루프 플레이어와 동일 원칙). 상세: `docs/changelogs/kb.md`(2026-07-09),
> [`docs/stage-guides/stage7_tts_design.md`](../../../docs/stage-guides/stage7_tts_design.md).

> **2026-07-07 정정 요약**: 최초 계획의 인지 TTS 엔진 Kokoro/Coqui는 **실제로 구현되지 않았다**(위 2026-07-09 정정으로 Piper도 핫스왑 폴백으로 격하됨). 클라이언트 재생 계층은 Web Audio API가 아니라 **`expo-audio`**(`createAudioPlayer`, `client/src/services/audioEngine.ts`)이다. 입체 음향(panning)은 **2026-07-09 구현 완료**(등파워 패닝, 버킷별 프리렌더링 스테레오 WAV 5종 전환 방식) - 이 절의 "저장만 되고 미적용" 서술은 구버전 정보였다. 상세: [`docs/stage-guides/stage7_tts_design.md`](../../../docs/stage-guides/stage7_tts_design.md), [`docs/design/reflex_audio_specification.md`](../../../docs/design/reflex_audio_specification.md) §4.

## 개요

최종 가이드를 한글 음성으로 변환·재생합니다. v1.1 설계에 따라 **이중 채널**(반사=사전합성, 인지=실시간 합성)로 분리합니다. 화면을 못 보는 사용자에게 귀로 전달하는 것이 핵심입니다.

## v1.1 핵심 변경 사항

| 항목 | 기존 | v1.1 |
| --- | --- | --- |
| 반사 음성 | 실시간 TTS 합성 | **사전합성 고정 클립**(앱 번들), 실시간 합성 금지 |
| 선점 | 없음 | **반사 음성이 인지 음성을 중단시키고 재생**(preempt) |
| WS 타입 | 단일 alert | **반사 = 고우선 타입**, 인지 = 일반 가이드 |
| 추상화 | 없음 | **TTSService** 추상화, MP3/WAV 규격 통일 |
| Whisper | 7단계에 혼재 | **Whisper는 STT 전용**, 7단계(출력)에 등장 안 함 |

## 아키텍처

```
[6단계 LangGraph]  guidance_text

[7-인지] 로컬 TTS(Supertonic, 기본/Piper 핫스왑) generate()  WAV bytes  WS 바이너리 프레임(transport:"binary")  단말 expo-audio 재생(상시 재생 웜 플레이어)

[3단계 Gate]  alert_id

[7-반사] 단말 사전합성 고정 클립 즉시 재생 (선점, 실시간 TTS 미경유)

중복 억제: setex(suppress:alert_id, 60)
햡틱: Haptics + announceForAccessibility
```

## 기술 스택

| 구분 | 스택 | 용도 |
|------|------|------|
| 로컬 TTS (인지) | **Supertonic 3**(기본, MIT, 99M 파라미터 ONNX) / **Piper**(piper-kss-korean.onnx, 핫스왑 폴백) | 실시간 한글 음성 합성 (Kokoro/Coqui는 미구현) |
| 사전합성 클립 (반사) | WAV 파일 (앱 번들) | 즉시 재생 |
| 서버 프레임워크 | FastAPI + Uvicorn | WebSocket |
| 메시지 버스 | Redis SETEX | 중복 억제 (60초) |
| 모바일 오디오 | **expo-audio** (`createAudioPlayer`) | 인지 음성·반사 비프 재생 (Web Audio API 아님) |
| 모바일 TTS 백업 | expo-speech | 서버 TTS 실패 시 우회 |
| 접근성 | AccessibilityInfo | VoiceOver/TalkBack |
| 햅틱 | expo-haptics | 위험도 기반 진동 |

## 디렉토리 구조 (Minchodan 기준)

```
server/tts/
├── realtime_tts.py           # 인지 경로: TTSService.generate()  base64 WAV(→ consumer.py가 바이너리 프레임으로 재전송)
├── reflex_clip_sender.py     # 정정: 실제로는 어디서도 호출되지 않는 죽은 코드 (server/detection/consumer.py의 _send_reflex_alert()가 담당)
├── suppressor.py             # Redis setex(suppress:…, 60) 중복 억제
├── korean_g2p.py             # 2026-07-09 신규(현재 미사용): Piper용 표준 발음법 G2P, 핫스왑 대비 보존
└── tts_service.py            # TTSService 추상화(SupertonicTTSService 기본 + PiperTTSService 핫스왑), WAV 출력

client/src/services/
├── audioEngine.ts            # expo-audio createAudioPlayer 재생 (인지 음성 + 반사 비프 통합)
client/src/utils/
└── haptics.ts                # Haptics + announceForAccessibility
client/assets/reflex_clips/   # 사전합성 클립 앱 번들 (server/data와 동기화)
```

## 핵심 구현 절차 (서버 측)

### 단계 7-1. 인지 경로: 실시간 TTS 합성

> **정정(2026-07-09, 이전 2026-07-07 정정 갱신)**: 아래 코드는 최초 계획(Kokoro) 기준 설계 스케치다. **실제 구현 기본값은 Supertonic**(`server/tts/tts_service.py`의 `SupertonicTTSService`, ONNX 상주 세션)이며, `PiperTTSService`(`piper-kss-korean.onnx`, 상주 `PiperVoice` 세션)는 `TTS_ENGINE=piper` 지정 시 쓰이는 핫스왑 폴백으로 코드에 남아있다. 함수 시그니처·엔진 초기화부는 실제 소스를 기준으로 삼는다.

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
        "type": "reflex_alert",
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

# 실제 구현체는 SupertonicTTSService(기본)와 PiperTTSService(핫스왑) 2종이다
# (KokoroService/CoquiService는 미구현 계획안).
class SupertonicTTSService:
    """Supertonic 3 ONNX 모델 기반 한국어 TTS (server/tts/tts_service.py, 기본 엔진)"""
    async def generate(self, text, voice="ko", speed=1.0): ...
    def get_format(self): return "wav"  # WS 전송 시 base64가 아니라 바이너리 프레임(2026-07-09)

class PiperTTSService:
    """Piper ONNX 모델 기반 한국어 TTS (server/tts/tts_service.py, 핫스왑 폴백)"""
    async def generate(self, text, voice="ko", speed=0.9): ...
    def get_format(self): return "wav"

class OpenAITTSService:
    """post-MVP: OpenAI TTS 핫스왑"""
    async def generate(self, text, voice="ko", speed=0.9): raise NotImplementedError
    def get_format(self): return "mp3"
```

## 핵심 구현 절차 (React Native 앱 측)

### 단계 7-5. 인지 경로: expo-audio 재생

> **정정(2026-07-07)**: React Native에는 브라우저 `AudioContext`/`decodeAudioData`/`createStereoPanner`가 없다. 아래 Web Audio API 예시는 **미채택**이며, 실제 재생은 `expo-audio`의 `createAudioPlayer`로 구현돼 있다(`client/src/services/audioEngine.ts`). **입체 음향(panning)은 현재 실제 좌우 밸런스에 적용되지 않는다**(값은 저장되나 미사용) — [`docs/design/reflex_audio_specification.md`](../../../docs/design/reflex_audio_specification.md) 참조.

```typescript
// client/src/services/audioEngine.ts (실제 구현 요지)
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';

// base64 오디오 또는 번들 WAV 소스를 createAudioPlayer로 로드해 재생한다.
// AudioContext/StereoPanner는 사용하지 않으며, panning은 미구현이다.
const player = createAudioPlayer(sourceUri);
player.volume = 1.0;
player.play();
```

### 단계 7-6. 반사 경로: 사전합성 클립 선점 재생

> **오디오 API (2026-07-04)**: 클라이언트 오디오 재생 계층은 `expo-av` 대신 **`expo-audio`**(Expo SDK 56+ 차세대 API)로 통일되었다. `createAudioPlayer()` 동기 팩토리 + `player` 프로퍼티(`volume`, `pan`, `loop`) 기반. 현재 반사 비프음은 `client/src/services/audioEngine.ts`에 이미 expo-audio로 구현되어 있다.

```typescript
// client/src/services/reflexClipPlayer.ts
import { createAudioPlayer, type AudioPlayer } from 'expo-audio';

export class ReflexClipPlayer {
  private currentPlayer: AudioPlayer | null = null;

  async playPreempt(alertId: string, clipPath: string) {
    // 선점: 현재 재생 중인 인지 음성 중단
    if (this.currentPlayer) {
      this.currentPlayer.stop();
      this.currentPlayer.release?.();
      this.currentPlayer = null;
    }
    // 사전합성 클립 즉시 재생 (실시간 TTS 미경유)
    this.currentPlayer = createAudioPlayer({ uri: clipPath });
    this.currentPlayer.play();
  }
}
```

### 단계 7-7. 햅틱 + 접근성

```typescript
// client/src/utils/haptics.ts
import * as Haptics from 'expo-haptics';
import { AccessibilityInfo } from 'react-native';

export async function triggerHaptic(severity: 'high' | 'mid' | 'low') {
  switch (severity) {
    case 'high':
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      break;
    case 'mid':
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      break;
    case 'low':
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
- WS에서 반사 이벤트는 **별도 고우선 타입**(`reflex_alert`)으로 전송합니다.
- 반사 음성은 **실시간 TTS 합성을 금지**하며 사전합성 고정 클립만 사용합니다.

## 데이터 인터페이스

| 방향 | 페이로드 |
| --- | --- |
| In (인지) | 가이드 문장(String) |
| In (반사) | `alert_id` |
| Out (인지) | 오디오 bytes — raw WAV, WS 바이너리 프레임(2026-07-09, JSON 메타의 `transport:"binary"` 직후) |
| Out (반사) | 사전합성 클립 경로 — WS 고우선 타입 |

## 의존성·예외

- 선행 = 6단계(인지) / 3단계 게이트(반사). 파이프라인 종착.
- TTS 호출 실패/타임아웃 시 기기 내장 TTS로 우회(시스템 중단 금지).

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| 실시간 TTS 합성 | Supertonic generate()  WAV bytes(WS 바이너리 프레임) | TTFB < 200ms |
| 단말 재생 성공 | expo-audio 상시 재생 웜 플레이어(`playGuideAudioBytes`) 재생 | 재생 확인 |
| **반사 클립 선점 재생** | 인지 음성 중단 후 반사 재생 | 선목 동작 |
| high 햅틱 동시 출력 | Haptics 동시 동작 | 진동 확인 |
| 중복 억제 | setex(suppress:…, 60) 60초 | 60초 내 재전송 없음 |
| TTS 실패 우회 | 기기 내장 TTS로 우회 | 중단 없음 |
| **반사 클립 사전합성** | 실시간 합성 미사용 확인 | 고정 클립만 |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- API 명세서: [`docs/design/api_specification.md`](../../../docs/design/api_specification.md) 4·5절
- 아키텍처 설계서: [`docs/design/architecture.md`](../../../docs/design/architecture.md) 5.7절
