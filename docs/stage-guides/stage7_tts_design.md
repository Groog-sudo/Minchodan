# Minchodan 7단계 음성 안내 출력 (이중 채널) 설계서

> **작성일**: 2026-07-01
> **버전**: v0.4.2 (2026-07-19 `react-native-tts`→`expo-speech` 잔여 정정 + 단말 TTS 백업 명세 동기화 + 이전 v0.4.1 이력 유지: 2026-07-10 th 브랜치 병합: pyttsx3를 로컬 저사양 대체 옵션으로 병기 + 이전 v0.4.0 이력 유지: 실기기 TTS 절단 근본 원인 규명에 따른 전면 갱신, 기본 TTS 엔진 Piper→Supertonic 교체(`SupertonicTTSService` 신규, Piper는 핫스왑 폴백으로 보존), guide 오디오 `audio_mp3_b64`→WS 바이너리 프레임 전환, `_synthesize_lock` 동시성 직렬화, iOS Hearing Protection 우회용 가이드 상시 재생 플레이어(`playGuideAudioBytes`) 반영)
> **설계 기준**: [`docs/design/minchodan_design_note.md`](../design/minchodan_design_note.md) 7단계, [`docs/design/architecture.md`](../design/architecture.md) 5.7절, [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) 5.7절
> **코딩 패턴 기준**: [`docs/dev-guides/course_codebase_guide.md`](../dev-guides/course_codebase_guide.md) 섹션 3, 17.2
> **스킬 참조**: [`../../.agents/skills/tts-voice-streamer/SKILL.md`](../../.agents/skills/tts-voice-streamer/SKILL.md)

---

## 1. 개요

7단계는 파이프라인의 최종 단계로, **이중 채널(반사 = 사전합성 클립 / 인지 = 실시간 TTS)** 음성 안내를 단말에 전달하는 역할을 담당한다.

종단 사용자는 시각장애인이므로 음성·햅틱이 1순위이며, 서버는 얇은 클라이언트(React Native) 부담을 최소화하기 위해 실시간 합성을 수행한다.

| 핵심 가치 | 설명 |
| --------- | ---- |
| **이중 경로 물리 분리** | 반사 경로는 LLM/RAG/실시간 TTS 절대 경유 금지. 사전합성 클립만 사용 |
| **선점(Preempt)** | 반사 음성은 인지 음성을 즉시 중단하고 재생 |
| **서버 합성** | 클라이언트 배터리·연산 부담 제거, 로컬망에서도 동작 |
| **사전합성 + 실시간 하이브리드** | 즉시 경보는 클립, 상세 가이드는 실시간 합성 |

> **비협상 원칙**: 반사 경로(high)에는 실시간 TTS를 절대 사용하지 않는다. 반사 음성은 앱 번들 사전합성 클립만 사용한다.

---

## 2. 구현 목록

- **[완료]** 반사 경로: direction/유형 기준 사전합성 클립 즉시 재생 + 선점 + 중복 억제. **2026-07-09 정정**: 실제 전송 경로는 `server/detection/consumer.py`의 `_send_reflex_alert()`가 게이트(`reflex_gate.py`/`surface_gate.py`/`head_level_gate.py`)가 채운 `ReflexAlert.clip`을 그대로 사용한다 — `server/tts/reflex_clip_sender.py`(아래 참조)는 실제로는 어디서도 호출되지 않는 죽은 코드였다.
- **[완료, 2026-07-09 엔진 교체]** 인지 경로: LangGraph L3 검증 통과 가이드 문장 → 서버 실시간 TTS(**Supertonic 3**, `TTS_ENGINE=supertonic` 기본) → raw **WAV** WS 바이너리 프레임 전송(`audio_mp3_b64` base64 필드는 폐기됨, §9 참조) → 단말 `expo-audio` 재생(Web Audio API 아님, React Native 환경 제약)
- **[완료]** TTSService 추상화 계층: **Supertonic**(`SupertonicTTSService`, 기본), **Piper**(`PiperTTSService`, 핫스왑 폴백으로 코드 보존, `TTS_ENGINE=piper`로 즉시 전환 가능), **pyttsx3**(`Pyttsx3TTSService`, GPU·네트워크 불필요한 로컬 저사양 대체, `TTS_ENGINE=pyttsx3`) 3종 구현. Kokoro/Coqui는 여전히 미구현(핫스왑 대비 설계만 존재).
- **[완료]** 중복 억제 (Suppressor, Redis SETEX 60초)
- **[부분 완료]** 햅틱·접근성 연동 (Haptics 연동 완료, `announceForAccessibility` 별도 확인 필요)
- **[완료, 2026-07-09]** 클라이언트 번들 클립 관리: 최초 설계(`data/reflex_clips/` → `client/assets/reflex_clips/`)와 실제 경로가 다르다 — 실제로는 `client/assets/sounds/reflex_clips/`(기존 `beep.wav`와 같은 `sounds/` 하위 규칙 준수)에 WAV 5종(direction 3종 + surface_caution + head_level_warning)으로 번들됨. `audioEngine.playReflexClip()` 신규 구현.
- **[완료, 2026-07-09]** 실패 시 기기 내장 TTS 우회: `expo-speech`로 서버 TTS 3초 타임아웃 시 단말이 직접 발화하는 `audioEngine.speakFallback()` 구현. 상세는 `docs/changelogs/kb.md`(2026-07-09) 참조.
- **[완료, 2026-07-09]** TTS 엔진 Piper→Supertonic 전면 교체: 실기기 청취 검증 결과 Piper(pygoruut/자체 G2P/espeak 음소화 모두 시도)는 흔한 음절(`측`/`직`/`걸` 등)을 발음에서 통째로 누락시키는 모델 자체 한계가 있어, Supertonic 3(supertone-inc, MIT 라이선스, 99M 파라미터 ONNX)로 교체. `PiperTTSService`는 삭제하지 않고 `TTS_ENGINE=piper`로 즉시 되돌릴 수 있는 핫스왑 경로로 보존.
- **[완료, 2026-07-09]** 합성 동시성 직렬화: `SupertonicTTSService.generate()`가 겹쳐 호출되면(연속 안내가 짧은 간격으로 도착) 서로 다른 문장인데도 동일한 오디오가 나오는 결함을 실측으로 발견 - `_synthesize_lock`(`asyncio.Lock`)으로 합성 호출 자체를 직렬화해 해소.
- **[완료, 2026-07-09]** iOS Hearing Protection 우회 (가이드 음성): 매번 `createAudioPlayer()`로 새 플레이어를 만들어 무음에서 재생을 "시작"하는 방식이 iOS의 재생 시작 시점 볼륨 제한과 누적되어 "시간이 지날수록 안내 음성이 작아지는" 현상으로 이어짐을 확인. 반사 비프 상시 루프 플레이어(§4.1 참조)와 동일한 원칙으로, `audioEngine.ts`에 무음 placeholder(`assets/sounds/silence.wav`)를 상시 재생하는 단일 웜 플레이어(`guideWarmPlayer`)를 두고 `player.replace()`로 소스만 교체하는 방식으로 전환.

---

## 3. 구현 파일 목록 (2026-07-09 실제 코드 기준 전면 정정)

> 이 절은 최초 설계 시점의 예상 파일 구조였으나 실제 구현과 다수 어긋나 있었다(파일명, 데이터 흐름 모두). 아래는 실제 코드를 확인해 정정한 목록이다.

### 서버 (인지 경로 실시간 TTS)
- `server/tts/tts_service.py`: TTSService 추상 클래스 + `get_tts_service()` 팩토리(TTS_ENGINE 기반, 기본값 `supertonic`) + `SupertonicTTSService`(기본, `_synthesize_lock`으로 합성 직렬화, 모델 캐시는 `~/.cache/supertonic3` - 볼륨 마운트 덮어쓰기 회피) + `PiperTTSService`(핫스왑 폴백, 상주 `PiperVoice` 세션 보존)
- `server/tts/korean_g2p.py` (2026-07-09 신규, 현재 미사용): Piper용 표준 발음법 규칙 기반 G2P. pygoruut의 음절 누락 결함 대응으로 작성했으나, 최종적으로는 Piper 자체가 아니라 Supertonic으로 교체해 해소했다 - Piper 핫스왑 경로가 실제 쓰일 경우를 대비해 코드는 보존.
- `server/tts/realtime_tts.py`: RealtimeTTS (`synthesize()` → `(base64 WAV, duration_ms)` 튜플, WS 전송 시에는 `server/detection/consumer.py`가 base64를 다시 디코딩해 바이너리 프레임으로 전송. **정정**: MP3가 아니라 WAV)
- `server/tts/suppressor.py`: AlertSuppressor (Redis 기반 중복 억제)
- `server/tts/reflex_clip_sender.py`: **정정(2026-07-09)** — 반사 경로 클립 전송 스켈레톤으로 작성됐으나 실제로는 어디서도 호출되지 않는 죽은 코드다. 실제 전송은 `server/detection/consumer.py`의 `_send_reflex_alert()`가 담당하며, 게이트(`server/detection/gates/{reflex_gate,surface_gate,head_level_gate}.py`)가 채운 `ReflexAlert.clip`을 그대로 WS로 보낸다.
- `server/api/session_manager.py`: **2026-07-09 신규** `send_bytes()` - guide 오디오 바이너리 프레임 전송용(카메라 프레임 client→server 프로토콜과 동일 패턴을 반대 방향에 적용).

### 데이터 (2026-07-09 정정: 서버 data/ 경유 아님)
- ~~`data/reflex_clips/`~~, ~~`DATA_REFLEX_CLIPS`~~: 최초 설계였으나 미사용. 실제로는 클라이언트가 클립을 번들로 갖고 있고 서버는 경로 문자열만 전달한다(아래 클라이언트 항목 참조).

### 클라이언트 (재생 담당)
- `client/src/services/audioEngine.ts`: 반사 비프(버킷별 스테레오 루프 플레이어), 반사 음성 클립(`playReflexClip()`), 인지 가이드 WAV(**`playGuideAudioBytes()`**, 2026-07-09 신규 - WS 바이너리 프레임 수신, 상시 재생 웜 플레이어 + `player.replace()` 방식), 단말 TTS 폴백(`speakFallback()`)을 전부 담당하는 단일 서비스. `playGuideAudio()`(구 base64 경로)는 폐기하지 않고 미사용 상태로 보존. **정정**: `reflexClipPlayer.ts`/`audioPlayer.ts`라는 별도 파일은 존재하지 않으며, Web Audio API가 아니라 `expo-audio`를 사용한다.
- `client/assets/sounds/reflex_clips/*.wav`: 사전합성 반사 음성 클립 5종(번들 자산)
- `client/assets/sounds/beep_pan/*.wav`: 방향성 비프음 스테레오 버킷 5종(번들 자산)
- `client/assets/sounds/silence.wav`: **2026-07-09 신규** - 가이드 상시 재생 웜 플레이어용 1초 무음 placeholder
- `client/src/hooks/useWebSocket.ts`: `reflex_alert`/`guide` 메시지 수신 시 위 `audioEngine` 메서드를 직접 호출. `ws.binaryType="arraybuffer"`로 guide 오디오 바이너리 프레임을 받아 `playGuideAudioBytes(Uint8Array)`에 전달.
- `client/src/utils/haptics.ts`: Haptics + announceForAccessibility

### 환경 변수 (docs/environment_variables.md 참조)
- `TTS_ENGINE`: supertonic (기본, 2026-07-09 변경) | piper (핫스왑 폴백) | pyttsx3 (로컬 저사양 대체, 2026-07-10 추가) — 그 외 값 지정 시 `tts_service.py`가 경고 로그를 남기고 supertonic으로 강제 폴백
- `SUPERTONIC_VOICE`: F1 (기본, 2026-07-09 신규 - Supertonic 보이스 스타일 이름)
- `DATA_REFLEX_CLIPS`: data/reflex_clips

### 테스트
- `tests/test_tts_reflex.py`: TC-TTS-001 ~ TC-TTS-007

**참고**: note.md (TTSTool_Test)에서 선별한 on-device 모델 (reflex-path: OS TTS for 즉시 클립, cognitive-path: OS TTS for 순차 가이드, sherpa-melotts-kr-int8 / piper-kss 등 ONNX)은 클라이언트 재생 레이어에서 하이브리드/폴백으로 활용 검토 중. 핵심 아키텍처는 docs 기반 서버+번들 클립 구조를 유지.

---

## 4. 핵심 설계 결정

- **이중 채널 강제 분리**: 반사 = 사전합성 (즉시, <300ms 목표), 인지 = 실시간 TTS (상세 가이드, 1~2Hz)
- **서버 합성 원칙**: 클라이언트 thin client 유지. Supertonic(ONNX) 로컬 모델 사용 (클라우드 비용·지연 제거, 2026-07-09 Piper에서 교체)
- **TTSService 추상화**: Supertonic(기본) + Piper(핫스왑 폴백) 2종 구현. Kokoro ↔ Coqui ↔ (미래) OpenAI TTS 핫스왑은 여전히 추상화 설계만 되어 있고 실제 구현체는 없음 (architecture.md 추상화 표)
- **선점 규칙**: 반사 WS (alert_reflex) 수신 시 인지 재생 즉시 중단
- **중복 억제**: alert_id 기준 Redis SETEX 60초 (Suppressor)
- **출력 규격 통일**: WAV bytes → WS 바이너리 프레임(2026-07-09, base64 경유 안 함) → `expo-audio`
- **클라이언트 책임**: 재생 + 선점 + 햅틱. 합성은 서버 전담 (반사 클립 제외)

---

## 5. 클래스 분리

### 서버
- `TTSService` (추상 ABC): `async generate(text: str, voice: str = "ko", speed: float = 1.0) -> Optional[bytes]`
- `RealtimeTTS`: `get_tts_service()` 주입, synthesize(text) → base64 WAV(+ duration_ms). 실제 구현체는 `SupertonicTTSService`(기본) 또는 `PiperTTSService`(핫스왑)
- `AlertSuppressor`: `should_suppress(device_id, alert_id)`, `mark_as_sent(...)`

### 클라이언트 (**정정**: 아래 클래스명은 최초 설계 예상이며 실제 구현은 `AudioEngine` 단일 서비스, §3 참조)
- ~~`ReflexClipPlayer`~~ → `audioEngine.playReflexClip()`: alert_id → 번들 WAV 로드 → play + preempt
- ~~`AudioPlayer`~~ → `audioEngine.playGuideAudioBytes()`: WS 바이너리 프레임(raw WAV bytes) → 상시 재생 웜 플레이어 소스 교체(`expo-audio`, Web Audio 아님)
- Haptics 연동 모듈

### 팩토리 패턴
`get_tts_service()` (tts_service.py) — LLMClientFactory / VectorDBFactory와 동일한 추상화 패턴 준수

---

## 6. 이중 게이트 규칙 (TTS 관점)

3단계 게이트에서 결정된 위험도에 따라 음성 채널 분기 (minchodan_design_note.md, behavior_and_risk_insight.md):

- **Reflex Gate (고위험)**: 즉시 `alert_id + 방향` → 사전합성 클립 재생 (LLM/실시간 TTS 금지)
  - 예: high_front, high_left, surface_stairs, surface_braille_damaged 등
- **Surface Gate (노면)**: P0 노면 하단 검출 → 사전합성 클립
- **인지 경로 (mid/low)**: Redis Streams → L1/L2/L3 → 실시간 TTS

반사 음성 클립 목록 (api_specification.md):
- high_front / high_left / high_right / high_stop
- surface_crosswalk / surface_manhole / surface_stairs / surface_grating / surface_braille_damaged

---

## 7. 검증 기준

(test_specification.md 5.7절)

| ID         | 검증 항목           | 기준                                      | 상태 |
|------------|---------------------|-------------------------------------------|------|
| TC-TTS-001 | 실시간 TTS 합성     | Supertonic `generate()` → WAV bytes(WS 바이너리 프레임 전송)    | 대기 |
| TC-TTS-002 | 단말 재생 성공      | `expo-audio` `playGuideAudioBytes()` 재생        | 대기 |
| TC-TTS-003 | 반사 클립 선점 재생 | 인지 음성 중단 후 반사 재생               | 대기 |
| TC-TTS-004 | high 햅틱 동시 출력 | Haptics 동시 동작                         | 대기 |
| TC-TTS-005 | 중복 억제           | `setex(suppress:…, 60)` 60초              | 대기 |
| TC-TTS-006 | TTS 실패 우회       | 기기 내장 TTS로 우회                      | 대기 |
| TC-TTS-007 | 반사 클립 사전합성  | 실시간 합성 미사용 확인                   | 대기 |

추가: 이중 경로 분리 (TC-PATH-003, TC-PATH-006/007) — 반사 경로에 실시간 TTS 호출 0건.

---

## 8. 코딩 패턴 준수 사항

- **파일 헤더**: UTF-8 reconfigure (course_codebase_guide.md 3.1)
- **임포트 순서**: stdlib → 외부 → 로컬 (3.2)
- **경로 처리**: `os.path.dirname(os.path.abspath(__file__))` (3.3)
- **환경 변수**: `load_dotenv()` + `os.getenv("TTS_ENGINE", "supertonic")` (3.4, `tts_service.py` 실제 기본값, 2026-07-09 변경)
- **방어적 코딩**: None 가드, 예외 후 루프 유지, 방어적 dict 접근 (17.2)
- **이중 경로 강제**: 반사 게이트(`server/detection/gates/`)에서 TTS 모듈 import 금지 (code_quality_guide.md, AGENTS.md Dual Path Discipline)
- **추상화**: TTSService → 구체 구현 분리 (LLMClientFactory 패턴 준수)

---

## 9. 데이터 인터페이스

### WS 메시지 (api_specification.md)

**반사 (고우선)**
```json
{
  "type": "alert_reflex",
  "alert_id": "high_front",
  "direction": "front",
  "clip": "reflex_clips/high_front.mp3",
  "haptic": true
}
```

**인지 (2026-07-09 변경: audio_mp3_b64 폐기, 바이너리 프레임 전송)**
```json
{
  "type": "guide",
  "guidance_text": "...",
  "transport": "binary",
  "risk_level": "mid"
}
```
위 JSON 메시지 직후, WAV bytes(Supertonic 출력, base64 미경유)가 별도 WS 바이너리 프레임으로 이어진다. 상세는 `docs/design/api_specification.md` §6.1 참조.

### 내부 인터페이스
- `TTSService.generate(...) -> Optional[bytes]`
- `RealtimeTTS.synthesize(text) -> Optional[str]` (base64, `server/detection/consumer.py`가 다시 디코딩해 바이너리 프레임으로 전송)

---

## 10. 에러 처리 가드레일

- TTS 호출 실패/타임아웃 → 기기 내장 TTS (expo-speech) 우회 (minchodan_design_note.md)
- 빈 텍스트 → 합성 스킵 (realtime_tts.py 가드)
- 중복 → Suppressor가 차단
- 반사 클립 누락 → 무음 또는 기본 내장 음성
- 서버 TTS 미가용 시 (TTS_ENGINE 오류) → fallback 또는 경고 로그

---

## 11. 브랜치 전략

- 개인 브랜치: `jh`
- 작업은 `jh` 브랜치에서 진행 → `dev`로 PR
- PR 시 `docs/changelogs/jh.md`에 엔트리 추가 (AGENTS.md, git_branching_strategy.md)
- 직접 `master` / `dev` push 금지

---

## 12. 의존성 및 전제

### 서버
- TTS_ENGINE = supertonic (기본, 2026-07-09 변경) | piper (핫스왑 폴백)
- Supertonic 모델 캐시(`~/.cache/supertonic3`, 최초 실행 시 자동 다운로드) 또는 Piper ONNX 모델(`server/models/piper/`, 핫스왑용 보존)
- DATA_REFLEX_CLIPS = data/reflex_clips

### 클라이언트
- Web Audio API
- expo-speech (예비 / on-device 폴백)
- Haptics, announceForAccessibility
- 번들 클립 (react-native-assets)

### 클라이언트 on-device 모델 (note.md 선별)
- reflex-path: expo-speech (OS TTS, Android 중심, 즉시 클립)
- cognitive-path: expo-speech (OS TTS, iOS 중심, 순차 가이드)
- ONNX 후보 (일관성 필요 시): sherpa-melotts-kr-int8 (51MB, MIT), sherpa-piper-kss (60.6MB), sherpa-supertonic (91.9MB)
- 목표: 100MB 이하, 오프라인, 한국어 특화

### 전제
- 반사 클립은 사전 생성 (앱 번들)
- 인지 TTS는 서버에서만 (반사 금지)
- 클라이언트는 thin (합성 미수행)

---

## 13. 참고 자료

- [`docs/minchodan_design_note.md`](minchodan_design_note.md) (7단계 골격)
- [`docs/architecture.md`](architecture.md) (5.7절, 이중 채널)
- [`docs/pipeline_stage_design.md`](pipeline_stage_design.md) (5.7절)
- [`docs/api_specification.md`](api_specification.md) (alert_reflex / guide 메시지)
- [`docs/environment_variables.md`](environment_variables.md) (TTS_ENGINE, DATA_REFLEX_CLIPS)
- [`docs/test_specification.md`](test_specification.md) (TC-TTS-*)
- [`docs/course_codebase_guide.md`](course_codebase_guide.md)
- [`docs/code_quality_guide.md`](code_quality_guide.md) (이중 경로 분리)
- [`docs/AGENTS.md`](AGENTS.md)
- [`d:\final_project\TTSTool_Test\note.md`](d:\final_project\TTSTool_Test\note.md) (on-device TTS 모델 선별 및 최적화 결과)
- architecture.md 내 mermaid 다이어그램 및 7단계 인터페이스 표

---
