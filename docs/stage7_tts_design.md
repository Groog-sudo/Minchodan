# Minchodan 7단계 음성 안내 출력 (이중 채널) 설계서

> **작성일**: 2026-07-01
> **버전**: v0.1.0
> **설계 기준**: [`docs/minchodan_design_note.md`](minchodan_design_note.md) 7단계, [`docs/architecture.md`](architecture.md) 5.7절, [`docs/pipeline_stage_design.md`](pipeline_stage_design.md) 5.7절
> **코딩 패턴 기준**: [`docs/course_codebase_guide.md`](course_codebase_guide.md) 섹션 3, 17.2
> **스킬 참조**: [`.agents/skills/tts-voice-streamer/SKILL.md`](../.agents/skills/tts-voice-streamer/SKILL.md)

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

- 반사 경로: alert_id 기반 사전합성 클립 즉시 재생 + 선점 + 중복 억제
- 인지 경로: LangGraph L3 검증 통과 가이드 문장 → 서버 실시간 TTS(Kokoro/Coqui) → base64 MP3 WS 전송 → 단말 Web Audio 재생
- TTSService 추상화 계층 (핫스왑 대비: Kokoro ↔ Coqui ↔ OpenAI TTS)
- 중복 억제 (Suppressor, Redis SETEX 60초)
- 햅틱·접근성 연동 (Haptics + announceForAccessibility)
- 클라이언트 번들 클립 관리 (data/reflex_clips/ → client/assets/reflex_clips/)
- 실패 시 기기 내장 TTS 우회

---

## 3. 구현 파일 목록

### 서버 (인지 경로 실시간 TTS)
- `server/tts/tts_service.py`: TTSService 추상 클래스 + `get_tts_service()` 팩토리 (TTS_ENGINE 기반)
- `server/tts/realtime_tts.py`: RealtimeTTS (synthesize → base64 MP3)
- `server/tts/suppressor.py`: AlertSuppressor (Redis 기반 중복 억제)
- (예정) `server/tts/reflex_clip_sender.py`: 반사 경로 alert_id 클립 WS 고우선 전송 (현재 client 주도)

### 데이터
- `data/reflex_clips/`: 사전합성 반사 음성 클립 (alert_id별 MP3)
- `DATA_REFLEX_CLIPS`: 환경 변수로 경로 지정

### 클라이언트 (재생 담당)
- `client/src/services/reflexClipPlayer.ts`: 반사 클립 즉시 재생 + 선점 로직
- `client/src/services/audioPlayer.ts`: Web Audio API로 base64 MP3 디코딩·재생
- `client/src/utils/haptics.ts`: Haptics + announceForAccessibility

### 환경 변수 (docs/environment_variables.md 참조)
- `TTS_ENGINE`: kokoro (기본) | coqui (인지 경로 전용)
- `DATA_REFLEX_CLIPS`: data/reflex_clips

### 테스트
- `tests/test_tts_reflex.py`: TC-TTS-001 ~ TC-TTS-007

**참고**: note.md (TTSTool_Test)에서 선별한 on-device 모델 (reflex-path: OS TTS for 즉시 클립, cognitive-path: OS TTS for 순차 가이드, sherpa-melotts-kr-int8 / piper-kss 등 ONNX)은 클라이언트 재생 레이어에서 하이브리드/폴백으로 활용 검토 중. 핵심 아키텍처는 docs 기반 서버+번들 클립 구조를 유지.

---

## 4. 핵심 설계 결정

- **이중 채널 강제 분리**: 반사 = 사전합성 (즉시, <300ms 목표), 인지 = 실시간 TTS (상세 가이드, 1~2Hz)
- **서버 합성 원칙**: 클라이언트 thin client 유지. Kokoro-82M / Coqui 로컬 모델 사용 (클라우드 비용·지연 제거)
- **TTSService 추상화**: Kokoro ↔ Coqui ↔ (미래) OpenAI TTS 핫스왑 대비 (architecture.md 추상화 표)
- **선점 규칙**: 반사 WS (alert_reflex) 수신 시 인지 재생 즉시 중단
- **중복 억제**: alert_id 기준 Redis SETEX 60초 (Suppressor)
- **출력 규격 통일**: MP3 (또는 WAV) bytes → base64 → WS → Web Audio
- **클라이언트 책임**: 재생 + 선점 + 햅틱. 합성은 서버 전담 (반사 클립 제외)

---

## 5. 클래스 분리

### 서버
- `TTSService` (추상 ABC): `async generate(text: str, voice: str = "ko", speed: float = 1.0) -> Optional[bytes]`
- `RealtimeTTS`: `get_tts_service()` 주입, synthesize(text) → base64 MP3
- `AlertSuppressor`: `should_suppress(device_id, alert_id)`, `mark_as_sent(...)`

### 클라이언트
- `ReflexClipPlayer`: alert_id → 번들 MP3 로드 → play + preempt
- `AudioPlayer`: base64 MP3 → decodeAudioData → play (Web Audio)
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
| TC-TTS-001 | 실시간 TTS 합성     | Kokoro/Coqui `generate()` → base64 MP3    | 대기 |
| TC-TTS-002 | 단말 재생 성공      | Web Audio `decodeAudioData()` 재생        | 대기 |
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
- **환경 변수**: `load_dotenv()` + `os.getenv("TTS_ENGINE", "kokoro")` (3.4)
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

**인지**
```json
{
  "type": "guide",
  "guidance_text": "...",
  "audio_mp3_b64": "SUQzBAAAA...",
  "risk_level": "mid"
}
```

### 내부 인터페이스
- `TTSService.generate(...) -> Optional[bytes]`
- `RealtimeTTS.synthesize(text) -> Optional[str]` (base64)

---

## 10. 에러 처리 가드레일

- TTS 호출 실패/타임아웃 → 기기 내장 TTS (react-native-tts) 우회 (minchodan_design_note.md)
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
- TTS_ENGINE = kokoro (기본) | coqui
- Kokoro-82M / Coqui 로컬 설치
- DATA_REFLEX_CLIPS = data/reflex_clips

### 클라이언트
- Web Audio API
- react-native-tts (예비 / on-device 폴백)
- Haptics, announceForAccessibility
- 번들 클립 (react-native-assets)

### 클라이언트 on-device 모델 (note.md 선별)
- reflex-path: react-native-tts (OS TTS, Android 중심, 즉시 클립)
- cognitive-path: react-native-tts (OS TTS, iOS 중심, 순차 가이드)
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