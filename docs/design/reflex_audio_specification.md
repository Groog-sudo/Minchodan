# 반사 경로 오디오 및 햅틱 피드백 기술 명세서

> **작성일**: 2026-07-01
> **버전**: v1.1.0 (2026-07-07 §2.1 direction/alert_id 예시, §4 재생 아키텍처를 실제 구현 기준으로 정정)
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
| **distance**         | Float   | **필수**  | 탐지된 장애물과의 렌즈 기준 상대 거리 (단위: 미터)                                      |
| **beep_interval_ms** | Integer | **필수**  | 비프음 반복 재생 주기 (단위: 밀리초, **0**은 무점멸 연속음)                             |
| **haptic_pattern**   | String  | **필수**  | 기기에 전달할 진동 프로파일 식별자 (`short`, `double`, `continuous`)                    |

---

## 3. 비프음 및 햅틱 출력 스펙

거리별 장애물 위험도에 따라 다르게 렌더링될 청각 및 촉각 피드백의 구체적 프로파일 명세입니다.

### 3.1 위험 등급별 피드백 테이블

| 위험 단계           | 상대 거리             | 비프음 주기 (beep_interval_ms)   | 햅틱 패턴                | 설명                            |
| :------------------ | :-------------------- | :------------------------------- | :----------------------- | :------------------------------ |
| **주의 (Low)**      | 1.5m 초과 ~ 2.0m 이하 | **500 ms** 간격 점멸             | `short` (짧은 진동 1회)  | 장애물 감지 진입 경고           |
| **경고 (Mid)**      | 1.0m 초과 ~ 1.5m 이하 | **250 ms** 간격 점멸             | `double` (짧은 진동 2회) | 신속한 정지 또는 회피 준비 단계 |
| **위험 (High)**     | 0.5m 초과 ~ 1.0m 이하 | **100 ms** 간격 고속 점멸        | `continuous` (지속 진동) | 물리적 충돌 직전, 제동 필수     |
| **정지 (Critical)** | 0.5m 이하             | **0 ms** (끊김 없는 연속 경고음) | `continuous` (지속 진동) | 즉시 완전 정지 지시             |

---

## 4. 모바일 클라이언트 재생 아키텍처 (2026-07-07 실제 구현 기준 정정)

> 최초 설계는 Web Audio API(`AudioContext`/`OscillatorNode`/`GainNode`/`StereoPannerNode`)를 전제로 했으나, 실제 구현(`client/src/services/audioEngine.ts`)은 React Native 환경 제약(Web Audio API 노드 미지원, iOS Hearing Protection 우회 필요)에 맞춰 **`expo-audio`의 정적 음원 루프 + 볼륨 스위칭** 방식으로 대체되었다. 아래는 실제 코드 기준 서술이다.

### 4.1 실제 재생 파이프라인

```mermaid
graph TD
    "expo-asset Asset.fromModule<br/>(로컬 800Hz 비프 WAV 로드)" --> "expo-audio createAudioPlayer<br/>(loop=true 상시 재생 스트림)"
    "expo-audio createAudioPlayer<br/>(loop=true 상시 재생 스트림)" --> "player.volume 스위칭<br/>(1.0 <-> 0.0, 120ms 펄스)"
    "player.volume 스위칭<br/>(1.0 <-> 0.0, 120ms 펄스)" --> "Destination<br/>(스피커/이어폰 출력)"
```

### 4.2 실제 재생 로직 명세 (`client/src/services/audioEngine.ts`)

- **음원**: `assets/sounds/beep.wav`(로컬 번들 정적 800Hz 비프 파일)를 `createAudioPlayer(sourceUri)`로 1회 생성하고, `player.loop = true`로 앱 전체 생명주기 동안 **끊김 없이 계속 재생**시켜 둔다(iOS가 재생 시작 시점마다 부여하는 Hearing Protection 볼륨 제한을 우회하기 위함).
- **비프 표현**: 실제 오디오 신호를 켜고 끄는 대신, `player.volume`을 `1.0`(소리 남)과 `0.0`(무음)으로 스위칭하는 방식으로 "삐-" 펄스를 만든다. 각 펄스는 볼륨 `1.0` 설정 후 120ms 뒤 `0.0`으로 복귀한다.
- **주기 제어**: `beep_interval_ms`가 `0`이면 볼륨을 `1.0`으로 고정해 끊김 없는 연속음을 낸다. `0`이 아니면 `setInterval(..., intervalMs)`로 위 펄스를 반복한다.
- **`panning`(좌우 밸런스) 미적용**: WS로 수신한 `panning` 값은 `AudioEngine.currentPanning`에 저장만 되고(`audioEngine.ts:72`), 실제로 좌우 스피커 밸런스나 팬(pan)에 적용되는 코드 경로가 없다. 즉 **입체 음향(스테레오 패닝) 기능은 현재 미구현**이며, 볼륨 스위칭 기반 모노 비프음만 출력된다. 이는 §1의 "방향성 입체 비프음(Stereo Panning Beep)" 목표가 아직 완전히 실현되지 않았음을 의미하며, `panning` 필드를 실제 좌우 밸런스에 반영하는 것은 후속 작업 과제로 남는다.
- **정지 규칙**: `stopBeep()`은 500~600ms 쿨다운 타이머 후 볼륨을 `0.0`으로 되돌리며(널뛰기 방지), `stopAllActiveAudio()`는 즉시 무음 처리한다.

---

## 5. 선점(Preemption) 정책 및 안전 규칙

1. **오디오 채널 선점**: 반사 오디오(`reflex_alert`) 발생 시, 인지 경로에서 실시간 재생 중인 TTS 음성 가이드를 즉각 음소거(Mute)하고 오디오 스피커 채널을 강제 탈취하여 비프음을 우선 송출합니다.
2. **햅틱 동시성**: 비프음이 울리는 매 프레임마다 모바일 기기의 진동 모터를 연동 구동시켜 청각장애 동반 시각장애인 또는 시끄러운 실외 환경에서도 위험을 직감하도록 보장합니다.
3. **독립성 유지**: 반사 오디오 생성과 햅틱 제어 로직은 단말 내부에서 로컬 연산으로 완결되며, 어떠한 경우에도 외부 API 호출이나 LLM/RAG 연산 결과에 대기하지 않는 비동기 병렬 구조를 취합니다.
