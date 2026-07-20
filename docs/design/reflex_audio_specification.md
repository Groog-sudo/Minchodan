# 반사 경로 오디오 및 햅틱 피드백 기술 명세서

> **작성일**: 2026-07-01
> **버전**: v1.3.2 (2026-07-20 §5.2 우선순위 모델을 실제 코드 기준 4단(OTHER/FRONT_MED/FRONT_NEAR/STT)으로 정정하고, 대기열 폐기 정책을 시간순(FIFO)에서 위험도순(최하위 우선순위 폐기·최고 우선순위 드레인)으로 전환한 내용 반영. 기존 v1.3.1 이력 유지: 2026-07-18 §5.3 T3-S 서버 STT 억제 게이트 정정 - 응답 전송 직후 즉시 해제하던 것을 예상 재생시간+마진까지 TTL 연장하도록 수정. 기존 v1.3.0 이력 유지: 2026-07-13 긴급=핑퐁만 / 여유=음성 채널 분기, §3.1·§4.2·§5 정합)
> **기준 문서**: `docs/design/architecture.md`, `docs/design/api_specification.md`

---

## 1. 개요

시각장애인 보행 보조 상황에서 긴급 장애물 출현 시 자연어 기반의 TTS 음성 안내는 발화 길이(1.5 ~ 2.0초)로 인해 반응 지연을 초래합니다. 본 명세서는 인지 부하를 최소화하고 척수 반사 수준의 즉각 회피를 유도하기 위한 **방향성 입체 비프음(Stereo Panning Beep)** 및 **거리별 주파수 가속(주차 센서 방식)**, **햅틱 피드백**의 기술적 명세를 정의합니다.

---

시각장애인의 **반사신경(Reaction Time)**에 대한 연구를 조사한 결과, 중요한 점은 **"시각장애인은 반사신경 자체가 느린 것이 아니라, 자극의 종류(청각, 촉각, 시각)에 따라 차이가 있다"**는 것입니다.

### 1. 청각 반사속도 (Auditory Reaction Time)

가장 많이 인용되는 연구에서는 선천성 시각장애인의 **청각 반응시간이 정상인보다 오히려 빠른 경향**을 보였습니다.

| 대상              | 단순 청각 반응시간 |
| ----------------- | ------------------ |
| 선천성 시각장애인 | 약 **150~180 ms**  |
| 일반인            | 약 **170~210 ms**  |

연구에서는 선천성 시각장애인의 평균 청각 반응시간이 정상 시력군보다 짧았으며, 이는 **교차감각 신경가소성(Cross-modal neuroplasticity)**으로 설명됩니다. 시각 정보를 담당하던 뇌 영역 일부가 청각 처리에 활용되어 청각 자극 처리 효율이 향상될 수 있다는 것입니다. ([bibliomed.org][1])

### 2. 시각장애인과 일반인의 청각 반응 비교

2014년 연구에서는 다음과 같은 결과가 보고되었습니다.

- 시각장애 청소년과 일반 청소년의 **청각 단순 반응시간은 통계적으로 유의한 차이가 없었습니다.**
- 즉, 모든 시각장애인이 반드시 더 빠른 것은 아니며, 연령, 시력 상실 시기, 훈련 경험 등에 따라 차이가 나타날 수 있습니다. ([Springer][2])

### 3. 촉각 반응속도

보행 보조장치 연구에서는 진동(촉각) 신호에 대한 반응시간이 주로 측정됩니다.

| 자극       | 평균 반응시간     |
| ---------- | ----------------- |
| 진동(촉각) | 약 **250~400 ms** |

이 범위는 보행 보조 벨트, 스마트 지팡이 등에서 장애물 경고를 설계할 때 기준으로 활용됩니다. ([SCIRP][3])

### 4. 보행 연구와의 관련성

앞서 정리한 보행 속도와 함께 보면 다음과 같이 요약할 수 있습니다.

| 항목                 | 일반인      | 시각장애인                                 |
| -------------------- | ----------- | ------------------------------------------ |
| 평균 보행속도        | 1.3~1.4 m/s | 0.8~1.0 m/s (독립보행)                     |
| 보조자 동반 보행속도 | -           | 1.2~1.35 m/s                               |
| 청각 반응시간        | 170~210 ms  | 150~190 ms(연구에 따라 유사하거나 더 빠름) |
| 촉각 반응시간        | 200~350 ms  | 250~400 ms                                 |

### 핵심 해석

시각장애인은 **청각이나 촉각 자극에 대한 반응이 반드시 느린 것은 아닙니다.** 오히려 청각 반응은 일반인과 비슷하거나 더 빠르게 나타나는 연구가 있습니다. 반면 **독립 보행 속도는 안전 확보를 위해 의도적으로 낮추는 경향**이 있어 평균적으로 일반인보다 약 25~35% 느립니다. 이는 반사신경의 저하 때문이라기보다, 주변 환경을 청각·촉각으로 탐색하는 과정과 안전 전략의 영향으로 해석됩니다. ([bibliomed.org][1])

만약 **자율주행 휠체어, 안내 로봇, 웨어러블 보행 보조장치**의 설계 기준을 위해 사용하실 예정이라면, 관련 논문에서 자주 사용하는 **반응시간(Reaction Time), 장애물 회피시간(Avoidance Time), 제동거리(Stopping Distance)**까지 함께 정리해 드릴 수 있습니다.

[1]: https://www.bibliomed.org/?mno=14543&utm_source=chatgpt.com "Comparative study of simple auditory reaction time between congenitally total blind people and normally sighted controls | National Journal of Physiology, Pharmacy and Pharmacology"
[2]: https://link.springer.com/article/10.7603/s40680-013-0002-5?utm_source=chatgpt.com "A comparison of reaction times between adolescents with visual and auditory impairment and those without any impairment | Türk Fizyoterapi ve Rehabilitasyon Dergisi/Turkish Journal of Physiotherapy and Rehabilitation | Springer Nature Link"
[3]: https://www.scirp.org/journal/paperinformation?paperid=38831&utm_source=chatgpt.com "Assistive Navigation Device for Visually Impaired—A Study on Reaction Time to Tactile Modality Stimuli"

## 2. 데이터 계약 (Data Contract)

반사 게이트가 작동하여 즉각 경보를 쏠 때, 기존의 `ReflexAlert` 웹소켓 이벤트 구조를 확장하여 입체 음향 및 비프음 속도 정보를 탑재합니다.

### 2.1 WebSocket 패킷 규격 확장

| 필드명               | 타입    | 필수 여부 | 설명                                                                                    |
| :------------------- | :------ | :-------- | :-------------------------------------------------------------------------------------- |
| **type**             | String  | **필수**  | 메시지 타입 식별자 (`reflex_alert` 고정)                                                |
| **alert_id**         | String  | **필수**  | 경보 고유 식별자 (`f"high_{class_name}_{direction}"` 형식, 예: `high_car_front-left`. `server/detection/gates/reflex_gate.py:55` 참조) |
| **direction**        | String  | **필수**  | 장애물 출현 방향 (`front-left`, `front`, `front-right` — `server/detection/direction.py`의 `estimate_direction()` 산출값. `left`/`right`/`center`/`stop`은 사용하지 않음) |
| **panning**          | Float   | **필수**  | 오디오 좌우 밸런스 편향값 (**-1.0**은 완전 왼쪽, **1.0**은 완전 오른쪽, **0.0**은 중앙) |
| **clip**             | String  | **필수**  | 사전합성 음성 클립 경로(`reflex_clips/high_front.wav` 형식). 클래스와 무관하게 direction/유형 기준으로만 정해진다(§4.2 참조). 서버는 오디오 바이트가 아니라 이 경로 문자열만 전달하고, 실제 파일은 단말 번들(`client/assets/sounds/reflex_clips/`)에서 재생한다 |
| **distance**         | Float   | **필수**  | 탐지된 장애물과의 렌즈 기준 상대 거리 (단위: 미터)                                      |
| **beep_interval_ms** | Integer | **필수**  | 비프음 반복 재생 주기 (단위: 밀리초, **0**은 무점멸 연속음)                             |
| **haptic_pattern**   | String  | **필수**  | 기기에 전달할 진동 프로파일 식별자 (`short`, `double`, `continuous`)                    |

---

## 3. 비프음 및 햅틱 출력 스펙

거리별 장애물 위험도에 따라 다르게 렌더링될 청각 및 촉각 피드백의 구체적 프로파일 명세입니다.

### 3.1 위험 등급별 피드백 테이블

| 위험 단계           | 상대 거리             | 비프음 주기 (beep_interval_ms)   | 햅틱 패턴                | 출력 채널 (2026-07-13) | 설명                            |
| :------------------ | :-------------------- | :------------------------------- | :----------------------- | :--------------------- | :------------------------------ |
| **주의 (Low)**      | 1.5m 초과 ~ 2.0m 이하 | **500 ms** 간격 점멸             | `short` (짧은 진동 1회)  | **음성 클립 + 비프**   | 장애물 감지 진입 경고           |
| **경고 (Mid)**      | 1.0m 초과 ~ 1.5m 이하 | **250 ms** 간격 점멸             | `double` (짧은 진동 2회) | **음성 클립 + 비프**   | 신속한 정지 또는 회피 준비 단계 |
| **위험 (High)**     | 0.5m 초과 ~ 1.0m 이하 | **100 ms** 간격 고속 점멸        | `continuous` (지속 진동) | **핑퐁 비프만**        | 물리적 충돌 직전, 제동 필수     |
| **정지 (Critical)** | 0.5m 이하             | **0 ms** (끊김 없는 연속 경고음) | `continuous` (지속 진동) | **핑퐁 비프만**        | 즉시 완전 정지 지시             |

---

## 4. 모바일 클라이언트 재생 아키텍처 (2026-07-09 §4.2 패닝 구현 완료 반영)

> 최초 설계는 Web Audio API(`AudioContext`/`OscillatorNode`/`GainNode`/`StereoPannerNode`)를 전제로 했으나, 실제 구현(`client/src/services/audioEngine.ts`)은 React Native 환경 제약(Web Audio API 노드 미지원, `expo-audio`에 실시간 pan API 부재, iOS Hearing Protection 우회 필요)에 맞춰 **버킷별 프리렌더링 스테레오 음원 루프 + 볼륨 스위칭** 방식으로 대체되었다. 아래는 실제 코드 기준 서술이다.

### 4.1 실제 재생 파이프라인

```mermaid
graph TD
    "beep.wav 원본 샘플을<br/>Python wave/struct로 등파워 패닝<br/>(-1.0/-0.5/0.0/0.5/1.0, 5버킷 프리렌더링)" --> "expo-asset Asset.fromModule<br/>(버킷별 스테레오 WAV 5개 로드)"
    "expo-asset Asset.fromModule<br/>(버킷별 스테레오 WAV 5개 로드)" --> "expo-audio createAudioPlayer x5<br/>(전부 loop=true 상시 재생 스트림)"
    "expo-audio createAudioPlayer x5<br/>(전부 loop=true 상시 재생 스트림)" --> "panning 값으로 최근접 버킷 선택<br/>-> 해당 플레이어만 volume 스위칭<br/>(1.0 <-> 0.0, 120ms 펄스), 나머지는 0.0 유지"
    "panning 값으로 최근접 버킷 선택<br/>-> 해당 플레이어만 volume 스위칭<br/>(1.0 <-> 0.0, 120ms 펄스), 나머지는 0.0 유지" --> "Destination<br/>(스피커/이어폰 출력)"
```

### 4.2 실제 재생 로직 명세 (`client/src/services/audioEngine.ts`)

- **음원**: 원본 `assets/sounds/beep.wav`(800Hz 비프)에서 좌우 채널 게인만 다르게 프리렌더링한 스테레오 WAV 5종(`assets/sounds/beep_pan/beep_pan_{-1.0,-0.5,0.0,0.5,1.0}.wav`)을 각각 `createAudioPlayer(sourceUri)`로 생성하고, 5개 전부 `player.loop = true`로 앱 전체 생명주기 동안 **동시에 끊김 없이 계속 재생**시켜 둔다(iOS가 재생 시작 시점마다 부여하는 Hearing Protection 볼륨 제한을 우회하기 위함).
- **비프 표현**: 실제 오디오 신호를 켜고 끄는 대신, 선택된 버킷 플레이어의 `player.volume`을 `1.0`(소리 남)과 `0.0`(무음)으로 스위칭하는 방식으로 "삐-" 펄스를 만든다. 각 펄스는 볼륨 `1.0` 설정 후 120ms 뒤 `0.0`으로 복귀한다.
- **주기 제어**: `beep_interval_ms`가 `0`이면 볼륨을 `1.0`으로 고정해 끊김 없는 연속음을 낸다. `0`이 아니면 `setInterval(..., intervalMs)`로 위 펄스를 반복한다.
- **`panning`(좌우 밸런스) 구현 완료 (2026-07-09)**: WS로 수신한 `panning` 값(-1.0~1.0 연속값)은 `nearestPanBucket()`으로 5단계 버킷(`DebugTriggerPanel.tsx`의 `PAN_PRESETS`와 동일 단계) 중 가장 가까운 값에 매핑되고, 해당 버킷의 스테레오 플레이어만 볼륨 스위칭되며 나머지 4개는 `0.0`으로 묵음 유지된다. 방향이 바뀌면 이전 버킷을 즉시 묵음 처리하고 새 버킷으로 전환한다. 버킷별 WAV는 등파워 패닝(equal-power panning, `left_gain=cos(θ)`, `right_gain=sin(θ)`, `θ=(panning+1)·π/4`)으로 프리렌더링돼 있어 하드좌측/하드우측 버킷은 반대쪽 채널 진폭이 정확히 0이다(파형 레벨로 검증 완료). §1의 "방향성 입체 비프음(Stereo Panning Beep)" 목표가 실현됐다.
- **정지 규칙**: `stopBeep()`은 500~600ms 쿨다운 타이머 후 현재 활성 버킷의 볼륨을 `0.0`으로 되돌리며(널뛰기 방지), `stopAllActiveAudio()`는 즉시 무음 처리한다.
- **반사 음성 클립 (채널 분기, 2026-07-13)**: `reflex_alert.clip`은 항상 페이로드에 실을 수 있으나, 단말(`useWebSocket`)은 **`beep_interval_ms > 100`(Mid/Low, 여유)** 일 때만 `playReflexClip()`을 호출한다. **Critical/High(`<=100`)는 핑퐁 비프(+햅틱)만** 재생해 긴급 반응을 방해하지 않는다. 인지 경로 `guide` TTS는 mid/low risk 상세 안내용으로 그대로 유지한다. 클립 파일은 `assets/sounds/reflex_clips/`에 번들되며, 서버는 경로 문자열만 전달한다(§2.1 참조).

---

## 5. 선점(Preemption) 정책 및 안전 규칙

### 5.1 반사-인지 선점 (기존)

1. **오디오 채널 선점**: 긴급 반사(`beep_interval_ms<=100`) 발생 시 인지 TTS를 즉각 중단하고 핑퐁 비프를 우선 송출한다. 여유 단계(`>100`)는 음성 클립/인지 안내를 허용하되, 비프는 가이드 재생 중 덕킹될 수 있다(`audioEngine` HIGH_DANGER 정책).
2. **햅틱 동시성**: 비프음이 울리는 매 프레임마다 모바일 기기의 진동 모터를 연동 구동시켜 청각장애 동반 시각장애인 또는 시끄러운 실외 환경에서도 위험을 직감하도록 보장합니다.
3. **독립성 유지**: 반사 오디오 생성과 햅틱 제어 로직은 단말 내부에서 로컬 연산으로 완결되며, 어떠한 경우에도 외부 API 호출이나 LLM/RAG 연산 결과에 대기하지 않는 비동기 병렬 구조를 취합니다.

### 5.2 통합 오디오 우선순위 모델 (2026-07-19 4단 전환, 2026-07-20 대기열 정책 갱신)

클라이언트 `audioEngine`은 단일 가이드 채널을 다음 우선순위로 조정한다(`client/src/services/guidePriority.ts` `GUIDE_PRIORITY`). 이 모델은 인지 안내(12시 회랑 NEAR/MED)와 STT 응답 간 충돌을 해결하고, 반사 경로는 별도 최상위 채널로 유지한다.

| 우선순위 | 상수 | 소스 | 정책 |
| :--- | :--- | :--- | :--- |
| **4 (최상위)** | `STT` | STT 응답(사용자 명시 요청) | 인지 안내를 선점·차단. 반사 채널에만 양보. |
| **3** | `FRONT_NEAR` | 12시 회랑 + Near 인지 안내 | STT 미만 전부 선점. |
| **2** | `FRONT_MED` | 12시 회랑 + Medium 인지 안내 | FRONT_NEAR·STT에 선점당함. |
| **1 (하위)** | `OTHER` | 측면 Near/Medium, Far, 방향 불명 등 그 외 인지 안내 | 상위 전부에 선점당함. |

우선순위 판정은 `resolveGuidePriority({isStt, clockDirection, distanceClass})`가 담당하며, **거리보다 "12시 정면 여부"가 먼저 걸리는 하드 게이트**다 — 측면의 Near/Medium과 Far는 방향 무관하게 전부 `OTHER`(1)로 동급 처리된다(측면 위험은 반사 채널이 별도 담당).

**대기열 정책 (`GUIDE_PENDING_MAX=6`, 2026-07-20 전환)**:
- 재생 중 더 높은 우선순위가 들어오면 즉시 선점 재생하고, 대기열에 남아있던 하위 우선순위는 전량 폐기한다(`discardPendingGuidesBelow`) — 위급 상황 종료 후 낡은 저위험 안내가 뒤늦게 재생되는 것을 막기 위한 의도적 보수 정책.
- 재생 중 동일/하위 우선순위는 더 이상 즉시 드롭되지 않고 대기열에 쌓인다(상한 6). 6개 초과 시 **최하위 우선순위부터** 폐기한다(`evictLowestPriorityPendingGuide`, 동률이면 오래된 쪽). 2026-07-19 이전에는 오래된 순(FIFO)으로 폐기했다.
- 현재 재생이 자연 종료되면 대기열에서 **최고 우선순위 1건**(동률이면 최신)만 꺼내 재생하고 나머지는 폐기한다(`drainHighestPriorityPendingGuide`). 2026-07-19 이전에는 "최신 1건"만 재생했다.
- STT 상호작용(녹음~응답 종료) 구간 동안 `audioEngine.setSttActive(true)`로 STT 미만 전부를 드롭한다(대기열에도 넣지 않음 - 질문 방해 금지가 최우선). 녹음 시작은 `CameraView.tsx`가 담당한다.
- STT 응답 수신 시 `useWebSocket.ts`가 priority=STT(4)로 재생하며, `didJustFinish`/`onDone`/`onStopped` 콜백에서 결정론적으로 상태를 해제한다.
- 콜백 누락 시 `useWebSocket.ts`의 안전 상한 타이머(`STT_INTERACTION_TIMEOUT_MS`, 20초)가 강제 해제한다.
- 반사 클립/비프는 별도 최상위 채널로 유지되며, 이 우선순위 모델을 거치지 않는다.

### 5.3 서버 STT 억제 게이트 (T3-S, 2026-07-18)

`server/api/session_manager.py`의 `_stt_activity` 레지스트리를 통해 STT 처리 중인 device_id를 추적한다. `server/api/ws_router.py`의 `_handle_stt_audio`가 `_process_stt_audio` 진입 시 `manager.set_stt_active(device_id, True)`를 호출한다. `server/detection/consumer.py`의 `_send_cognitive_guide` 진입부에서 `manager.is_stt_active(device_id)`가 true면 인지 가이드 발행을 조기 반환하여 연산 낭비와 경쟁 창을 제거한다. 반사 경로 `_send_reflex_alert`는 이 게이트를 적용하지 않는다.

**2026-07-18 정정**: 최초 구현은 응답 전송 직후(`finally`) 즉시 `manager.set_stt_active(device_id, False)`를 호출해, 실제 오디오 재생 구간에는 서버 억제가 이미 풀려 있는 gap이 있었다. `_process_stt_audio`가 응답 전송 시점에 `_estimate_stt_hold_seconds()`(클라이언트 `useWebSocket.ts`의 텍스트 길이 추정 + 1200ms 마진 공식과 동일)로 예상 재생 시간(초)을 계산해 반환하고, `_handle_stt_audio`가 이를 `set_stt_active(device_id, False, ttl_seconds=hold_seconds)`로 전달해 예상 재생 종료 시점까지 억제를 연장하도록 정정했다.

---

## 6. 억제 재무장(Re-arm) 정책 (2026-07-17, P0-1)

실사용 필드 테스트 피드백(S1 정지 후 60초 침묵, S2 새 객체 무시) 기반 반사 억제 정책 개선.

### 6.1 정책 전환

- **이전**: 동일 `alert_id`(high_obstacle) 60초 무조건 침묵.
- **이후**: "같은 상황 반복은 억제, 상황 변화(새 객체/거리 악화) 시 즉시 재발화".

### 6.2 억제 키 분리

- 키: `suppress:{device_id}:high_obstacle:{track_id}:{distance_band}`
- 새 객체(track_id 상이) 또는 거리 밴드 악화(far->medium->near) 시 키가 달라져 억제 우회.
- 동일 키 TTL: `REFLEX_SUPPRESS_TTL_S=5`초.

### 6.3 거리 밴드

| 밴드 | 거리 | 억제 정책 |
| :--- | :--- | :--- |
| `near` | <=0.6m | TTL 억제 **제외**, `REFLEX_NEAR_HAPTIC_THROTTLE_S=0.5`초 스로틀만 (충돌 임박 촉각 신호 반복 안전 이득) |
| `medium` | <=1.5m | 동일 키 5s TTL + device 단위 `REFLEX_MIN_GAP_S=1.5`초 쿨다운 + 밴드 악화 재발화 |
| `far` | >1.5m | (reflex_gate 범위 밖, 발생 안 함) |

### 6.4 should_rearm 판정

동일 track_id 내에서 거리 밴드가 가까워지면(far->medium->near) 즉시 재발화. 동일/멀어지면 기존 억제 유지. 신규 트랙(prev=None)은 보수적 재발화.

### 6.5 오해 방지

"폴백 동작 제거"는 임시 함수 기본값 폴백을 의미하며, 서버-온디바이스 폴백(WS 끊김 시 단말 CoreML/TFLite 추론 전환)은 유지됩니다.
