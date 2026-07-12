> **작성일**: 2026-07-12
> **버전**: v1.2.0 (실내 탐지 저하 명시 + 종합 원인 분석 + 개선 방향)
> **작성자**: th (태현)
> **대상**: Android 실기기 STT 인식 실패, 실내 음성/장애물 탐지 인식률 저하

# Android 실기기 인식 문제 종합 리포트 (STT + 실내 탐지)

## 1. 현상 요약

Android 실기기 테스트에서 아래 문제가 **동시에** 관찰된다.

| 영역 | 현상 | 체감 |
|------|------|------|
| **STT** | 화면을 누르고 말해도 반응이 약함 / "음성이 인식되지 않았어요" | 명령·목적지 설정 실패 |
| **지도** | 지도 패널이 안 뜨거나 토글이 없음 | STT·`nav_route` 실패와 혼동 |
| **실내 STT** | 실내에서 음성 인식률이 특히 나쁨 | 잔향·소음 환경 |
| **실내 탐지** | 실내 장애물/노면 **탐지 체감 정확도가 실외보다 분명히 떨어짐** | 미탐·오탐·안내 지연 |

사용자가 기대하는 STT 흐름:

1. 화면 press-and-hold
2. 말하기 (예: "길댕아 길찾아줘", 목적지)
3. 손 떼기
4. 서버 전사 → 안내 / (조건부) `nav_route` 지도

---

## 2. 실내 탐지·실내 STT 관찰 (핵심)

### 2.1 실내 장애물 탐지 저하

실기기에서 **실내**는 실외·개방 공간 대비 YOLO/온디바이스 탐지 체감이 낮다.

| 관찰 | 설명 |
|------|------|
| 미탐 | 가까운 장애물·가구·문틀이 안 잡히거나 늦게 잡힘 |
| 오탐 | 반사면·그림자를 장애물로 오인 |
| 노면 계층 약함 | segmentation 가중치(`segbest.pt`) 부재로 `MockSegmentor` 폴백 → 실내 노면 위험 계층이 사실상 비활성 |
| 조명 민감 | 형광등/스팟/저조도에서 conf가 흔들림 |

추정 원인 (비전):

| 요인 | 설명 |
|------|------|
| 도메인 갭 | AI Hub 인도보행 등 **야외 인도 중심** 학습/검증 → 실내(복도·로비·매장) 분포와 불일치 |
| 광학 | 유리·거울·바닥 반사, 역광, 저조도 |
| 파이프라인 | 서버 `YOLO26N_SEG` 실파일 없음 → Mock 폴백 |
| 온디바이스 | TFLite 출력 포맷 정합(6채널)은 반영했으나, 실내 conf 임계값·NMS 튜닝은 미실시 |
| 환경 설정 | 과거 `DETECTOR_TYPE=mock` 오설정 이슈가 있어 "탐지 안 됨"과 혼동된 이력 있음 (현재 yolo로 전환) |

### 2.2 실내 STT 저하

| 관찰 | 추정 요인 |
|------|-----------|
| 미인식·오인식 증가 | 잔향, 에어컨/환풍기 상시 소음 |
| 짧은 명령 실패 | VAD(`TRANSCRIBE_VAD_FILTER=True`)가 짧은 발화를 무음 처리 |
| 체감 "버튼이 안 먹힘" | 실제로는 전사 빈 문자열 → `stt-bridge-empty` 안내 |

---

## 3. 이번 세션 조치

| 항목 | 결과 |
|------|------|
| FastAPI (8000) | 종료 완료 |
| Metro (8081) | 종료 완료 |
| Android 빌드 | 중단됨 (Gradle 중간 종료) |
| 기기 USB | `R3CX70EB6QH` `device` 상태였음 |

---

## 4. 종합 원인 분석

원인을 **인프라 / STT / 비전·실내 탐지 / UX 혼동** 4축으로 정리한다.

### 4.1 인프라·런타임

| ID | 원인 | 심각도 | 근거 |
|----|------|--------|------|
| I-1 | Whisper 초기화 실패 (Python 3.14 + CPU + ctranslate2) | **높음** | `stt_audio` 수신 후에도 전사 실패 / 프리로드 실패 로그 |
| I-2 | Redis `localhost:6379` 거부 | 중간 | Streams/MCP 부가 경로 불안정 |
| I-3 | Ollama `nomic-embed-text` 부재 | 중간 | RAG 상시 fallback |
| I-4 | Metro LAN 8081 방화벽 | 낮음~중간 | `adb reverse`로 우회 중 |

완화 이력: `SttService.get_model()` CPU `int8` → `int8_float32` → `float32` 폴백 (`9f194da`).

### 4.2 STT 경로

| ID | 원인 | 심각도 | 근거 |
|----|------|--------|------|
| S-1 | 빈 전사 → `stt-bridge-empty` | **높음** | bridge가 "음성이 인식되지 않았어요" 반환 |
| S-2 | 짧은 press / 녹음 레이스 | 중간 | `pendingStartRef`로 일부 완화, 짧은 탭은 여전히 취약 |
| S-3 | VAD 과필터 | 중간 | `TRANSCRIBE_VAD_FILTER=True` |
| S-4 | Android AAC 캡처 검증 약함 | 중간 | iOS만 PCM 길이 조기 탐지 |
| S-5 | Android AEC JS 미연결 | 낮음~중간 | Kotlin 모듈 있으나 `audioSessionBridge.ts`가 iOS만 로드 |
| S-6 | 실내 잔향·상시 소음 | **높음(실내)** | 체감 관찰 |

### 4.3 비전·실내 탐지 경로

| ID | 원인 | 심각도 | 근거 |
|----|------|--------|------|
| D-1 | **실내 도메인 갭** (야외 인도 편향) | **높음(실내)** | 실내 탐지 체감 저하 |
| D-2 | 실내 광학 (유리/반사/저조도) | **높음(실내)** | 미탐·오탐 |
| D-3 | `segbest.pt` 부재 → MockSegmentor | **높음** | 노면 계층 비활성 |
| D-4 | 실내 전용 conf/게이트 미튜닝 | 중간 | 야외 임계값 그대로 사용 추정 |
| D-5 | 온디바이스 TFLite ↔ 서버 가중치 불일치 잔여 리스크 | 중간 | NMS 출력 6채널 정합은 반영, 실내 재검증 필요 |

### 4.4 UX·제품 흐름 혼동

| ID | 원인 | 심각도 | 설명 |
|----|------|--------|------|
| U-1 | 지도 = STT 성공 후에만 표시 | 중간 | `nav_route` 없으면 패널/토글 숨김 → "인식 실패"로 오해 |
| U-2 | 탐지 안 보임 ↔ mock/가중치/실내 품질 혼재 | 중간 | 원인 분리가 안 되면 디버깅 비용 증가 |

### 4.5 원인 우선순위 (실무용)

```text
1순위: I-1 Whisper 런타임 안정화 (없으면 STT 전체 마비)
2순위: D-3 seg 가중치 확보 + D-1/D-2 실내 탐지 품질
3순위: S-1/S-3/S-6 실내 STT (VAD·발화 길이·소음)
4순위: S-5 Android AEC 연결, I-2 Redis, I-3 임베딩
5순위: U-1 UX 안내 문구 (실패 원인 구분 표시)
```

---

## 5. 개선 방향

### 5.1 즉시 (1~2일, 환경·설정)

| 우선순위 | 개선 | 기대 효과 | 담당 힌트 |
|----------|------|-----------|-----------|
| P0 | Python **3.13** venv 재구성 + faster-whisper 재설치 | STT 프리로드 성공 | th/인프라 |
| P0 | 서버 기동 로그에 `Whisper 모델 프리로드 완료` 확인 | STT 경로 해금 | th |
| P0 | Redis 기동 | Streams/MCP 안정 | 로컬 Docker/brew |
| P1 | `YOLO26N_SEG` 실파일 배치 (`segbest.pt`) | 노면 계층 복구, 실내 탐지 품질 일부 회복 | 학습/가중치 담당 |
| P1 | `.env` `DETECTOR_TYPE=yolo` + 실제 det 가중치 경로 유지 | mock 혼동 제거 | th (gitignore) |
| P1 | STT 실측 시 **1.5초 이상** 누르고 또렷이 발화 | 빈 전사 감소 | QA |

### 5.2 단기 (1주, STT)

| 개선 | 내용 |
|------|------|
| VAD 튜닝 | 실내 테스트 시 VAD 완화 옵션 또는 최소 발화 길이 가드 |
| Android 캡처 검증 | m4a 파일 크기/duration 기반 조기 실패 안내 |
| AEC 연결 | `audioSessionBridge.ts` Android 로드 + 모듈명/`AudioSessionInfo` 정합 |
| 에러 UX | `stt-bridge-empty` / Whisper 실패 / WS 끊김을 화면 문구로 구분 |
| hotwords | 실내 명령 패턴 추가 검증 |

### 5.3 단기~중기 (1~2주, 실내 탐지)

| 개선 | 내용 |
|------|------|
| 실내 데이터 | 복도·로비·매장 프레임 수집 후 파인튜닝 또는 도메인 적응 |
| conf 분리 | 실내/실외 conf·게이트 임계값 분리 (또는 조명 추정 기반) |
| 온디바이스 | TFLite 실내 시나리오 매트릭스 (scooter/bollard/caution 등) |
| 서버-단말 정합 | 동일 장면에 대해 서버 YOLO vs 단말 TFLite 결과 교차 비교 |
| Mock 제거 강제 | seg 가중치 없으면 콘솔/로그에 **명확한 경고** (현재 WARNING은 있으나 QA 체크리스트화) |

### 5.4 중기 (제품·평가)

| 개선 | 내용 |
|------|------|
| 시나리오 매트릭스 | 실내/실외 × STT 문구 × 장애물 클래스 정량표 |
| KPI | STT 성공률, 빈 전사율, 탐지 Recall@거리, 실내/실외 갭 |
| 지도 UX | `nav_route` 없을 때 "경로 없음" vs "음성 인식 실패" 구분 카피 |

---

## 6. 재현·판정 체크리스트

### STT

- [ ] 누르는 중 **"듣는 중..."**
- [ ] 손 떼면 **"전송 중..."**
- [ ] 서버: `[WS] stt_audio 수신`
- [ ] 서버: `Whisper 모델 프리로드 완료` 또는 `전사 실패`
- [ ] 서버: `STT 전사 완료 text_len=`
- [ ] `text_len=0` + `stt-bridge-empty` → 빈 전사
- [ ] `text_len>0` + 안내 → 인식 성공, 후단(지도/인텐트) 확인

### 실내 탐지

- [ ] `DETECTOR_TYPE=yolo` 인지
- [ ] det 가중치 실파일 로드 로그
- [ ] seg가 Mock인지 실가중치인지
- [ ] 동일 장애물을 실내/실외에서 비교 (거리·각도 고정)
- [ ] 단말 TFLite 로그 vs 서버 detection 클래스 교차

---

## 7. 파이프라인 요약

```text
[STT]
단말 press-and-hold -> useSttRecorder (Android m4a)
  -> WS stt_audio
  -> Whisper small (CPU)
  -> SttToLlmBridge
  -> 빈 텍스트면 실패 안내 / 성공 시 guide + (조건부) nav_route

[탐지]
단말 카메라 -> (온디바이스 TFLite reflex) + 서버 YOLO cognitive
  -> gates / RAG / LLM guide
  -> seg 없으면 MockSegmentor (실내 노면 약화)
```

---

## 8. 결론

1. STT "안 먹힘"의 1순위는 **Whisper 런타임(I-1)** 과 **빈 전사(S-1)**, 지도 혼동(U-1)이다.
2. **실내에서는 탐지 품질도 분명히 떨어진다 (D-1~D-3)**. 야외 인도 편향 + 광학 + seg Mock이 겹친 상태다.
3. 개선은 **런타임 안정화 → seg 가중치 → 실내 STT/VAD → 실내 데이터·conf 튜닝 → UX 구분** 순으로 가는 것이 효율적이다.
4. 현재 수치는 체감 관찰이다. 다음 스프린트에서 실내/실외 비교 매트릭스로 정량화해야 한다.

---

## 9. 관련 파일

| 경로 | 역할 |
|------|------|
| `client/src/hooks/useSttRecorder.ts` | 단말 녹음/전송 |
| `client/src/components/CameraView.tsx` | press-and-hold, 지도 가드 |
| `client/src/services/audioSessionBridge.ts` | AEC (iOS만) |
| `client/android/.../AudioSessionBridgeModule.kt` | Android AEC (JS 미연결) |
| `client/src/inference/tfliteDetector.ts` | 온디바이스 탐지 |
| `server/api/ws_router.py` | `stt_audio` |
| `server/stt/stt_service.py` | Whisper |
| `server/stt/stt_config.py` | small/cpu/VAD |
| `server/stt/stt_to_llm_bridge.py` | 빈 입력/네비 |
| `server/detection/config.py` | YOLO/seg 로드·Mock 폴백 |
