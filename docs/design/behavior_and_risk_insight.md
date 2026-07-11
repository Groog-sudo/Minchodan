# 보행이론 기반 시각장애인 행동 패턴 및 위험도 정의 인사이트 보고서

> **작성일**: 2026-06-25
> **버전**: v1.1.0 (2026-07-07 §3.1 표를 실제 구현 클래스 배정 기준으로 정정, §4.1 미구현 상태 명시)
> **참조 자료**: `final_project_meet/docs/보행지도사_Gmini_요약.txt`
> **관련 문서**: [`docs/minchodan_design_note.md`](minchodan_design_note.md), [`docs/stage-guides/stage3_detection_design.md`](../stage-guides/stage3_detection_design.md)
> **주의**: 본 문서는 보행이론 교육자료를 분석한 **인사이트/제안 보고서**다. §3.1의 클래스 배정 예시는 2026-07-07 기준 실제 코드(`server/detection/gates/reflex_gate.py`, `server/orchestration/nodes/l1_classifier.py`, `server/detection/gates/surface_gate.py`)와 일치하도록 갱신했으나, 실제 구현이 이 제안을 100% 그대로 따른 것은 아니므로 코드가 최종 근거임을 유의한다.

---

## 1. 개요

본 문서는 보행지도사의 전문 이론 교육 자료(1강~9강)를 분석하여, **Minchodan 스마트 가이드독 AI 플랫폼**의 환경 인식 알고리즘, 이중 게이트(Reflex/Surface Gate) 설계, 그리고 최종 음성 안내 메시지 생성 필터에 적용할 도메인 인사이트를 정의합니다. 학술적인 보행 이론을 실제 소프트웨어 아키텍처 및 데이터 스키마로 구체화하는 데 목적이 있습니다.

---

## 2. 시각장애인 보행 행동 패턴 및 AI 적용점

보행지도사 교육과정에서 도출된 핵심 행동 패턴과 이를 구현하기 위한 백엔드/클라이언트 설계 적용점입니다.

### 2.1. 방향정위(Orientation)와 기준위치 프레임
* **도메인 이론**: 시각장애인은 자기 신체를 기준으로 삼는 **자기중심 기준위치(Egocentric Frame)**를 바탕으로 코스 및 객체 공간을 맵핑하고 방향정위를 수행합니다.
* **AI 적용점**:
  - 6단계 LangGraph 오케스트레이터의 L2 안내문 생성 노드는 절대 경로(예: "동쪽", "좌표 기준 우측")가 아닌 **사용자의 시선/카메라 정면을 12시 방향 기준으로 삼는 클록 아날로그 방식(Clock Position)** 혹은 **사용자 중심 좌/우/정면 상대 좌표계**를 엄격히 사용하여 음성을 생성해야 합니다.
  - 예: "1시 방향에 볼라드 주의" 또는 "오른쪽으로 우회하세요."

### 2.2. 공간 갱신(Spatial Updating) 피드백
* **도메인 이론**: 사용자가 보행을 지속함에 따라 변화하는 주변 공간 관계를 실시간으로 재정렬하고 갱신하는 능력이 필요합니다.
* **AI 적용점**:
  - 3단계 ByteTrack 추적 모듈은 객체(Object)의 고유 ID를 트래킹하여 사용자와 장애물 간의 상대적 거리 벡터 변화량을 지속 계산해야 합니다.
  - 사용자가 접근하여 거리가 좁아지는 장애물은 인지 경로 내에서 안내 우선순위(Priority Queue)를 동적으로 격상시킵니다.

### 2.3. 비어링 이탈 및 수정(Bearing Correction)
* **도메인 이론**: 보행 중 직선 경로에서 사선 방향으로 미세하게 빗나가는 현상(Bearing Deviation)이 발생하며, 시각장애인은 주로 발바닥의 압력, 경사도, 점자블록 등의 **환경적 단서(Clues)**를 이용해 이를 수정합니다.
* **AI 적용점**:
  - Yolo 26N - Segmentation(노면 분할)이 탐지한 **보도블록과 차도 경계선** 또는 **점자블록**의 기울기 벡터를 분석하여 사용자가 안전 지대 내에서 직선 보행을 하는지 감지합니다.
  - 직선 이탈 징후가 포착될 경우, 즉각적인 방향 교정 안내(예: "왼쪽으로 조금 치우쳤습니다. 오른쪽으로 맞추어 걸으세요")를 내보내 횡단보도나 교차로에서의 Bearing 문제를 예방합니다.

---

## 3. 보행이론 기반 위험도(Risk Level) 및 게이트(Gate) 정의

보행지도사 이론의 **랜드마크(Landmark)**, **단서(Clue)**, 그리고 신체 보호법 개념을 바탕으로 플랫폼의 위험 단계를 3단계로 구체화하고 3단계 이중 게이트와 연동합니다.

```
                  ┌─────────────────── [ Yolo 26N Dual-Head ] ───────────────────┐
                  │                                                              │
           (Object BBox)                                                  (Surface Seg)
                  │                                                              │
                  ▼                                                              ▼
        [ Reflex Gate (장애물) ]                                       [ Surface Gate (노면) ]
                  │                                                              │
                  ├─────────── 🚨 고위험 (충돌 1.5초 이내) ───────────┤
                  │            - 반사 경로 (사전합성 클립 즉시 선점 재생)         │
                  │                                                              │
                  ├─────────── ⚠️ 중위험 (회피/우회 필요) ─────────────┤
                  │            - 인지 경로 (LangGraph + RAG 가이드 생성)         │
                  │                                                              │
                  └─────────── ℹ️ 저위험 (긍정적 단서 / 랜드마크) ────────┘
                               - 인지 경로 (유도 피드백 및 랜드마크 참조 점각)
```

### 3.1. 위험 수준별 상세 매트릭스

| 위험 등급 (Risk Level) | 보행이론적 정의 및 영향 | 대상 탐지 클래스 및 세그먼트 | 시스템 액션 및 타임 필드 |
| :--- | :--- | :--- | :--- |
| **🚨 고위험<br>(High / Reflex)** | - 직접적인 신체 충돌 위협이 존재함.<br>- 낙상, 낭떠러지 추락 등 즉각적인 상해 유발 환경. | (실제 구현, `reflex_gate.py`/`surface_gate.py` 기준) 전방 이동체 `car, truck, bus, motorcycle, scooter`.<br>- 노면 P0: `caution`(계단/맨홀/그레이팅 통합 클래스). | **반사 경로(Reflex Path) 가동**<br>- LLM 및 실시간 TTS 절대 경유 금지.<br>- RTT/지연 최소화하여 사전합성 고정 클립 즉시 재생 (`< 300ms`). |
| **⚠️ 중위험<br>(Mid / Cognitive)** | - 직접 충돌은 아니나 정상 경로를 방해하여 **행동 수정(회피 또는 우회)**을 지시해야 하는 환경. | (실제 구현, `l1_classifier.py`/`detection_pipeline.py` `MID_RISK_CLASSES` 기준) `barricade, bench, bicycle, bollard, carrier, chair, fire_hydrant, kiosk, movable_signage, parking_meter, pole, potted_plant, power_controller, stroller, table, traffic_light_controller, tree_trunk, wheelchair` + 노면 `caution`(P0 미도달 시)/`roadway`. | **인지 경로(Cognitive Path) 가동**<br>- Yolo 탐지 이벤트의 Redis Streams 발행.<br>- LangGraph L1/L2/L3 및 RAG(수칙 검색) 거쳐 음성 스트리밍 송출. |
| **ℹ️ 저위험/단서<br>(Low / Clue)** | - 안전 보행의 **단서(Positive Clues)** 및 공간 정의를 돕는 **랜드마크(Landmark)** 역할.<br>- 보행 정위(Orientation)의 보조 지표. | - 정상 **점자블록(Braille Block, `braille_normal`)**.<br>- 안전한 보도 인도면(`sidewalk_normal`).<br>- 정보성 클래스(`person, cat, dog, traffic_light, traffic_sign, stop`). | **인지 경로 가이드 강화**<br>- 보행 정렬 보정 정보 전송.<br>- 랜드마크 도달 시 확인 피드백 제공 (예: "점자블록 유도선 상에 진입했습니다"). |

> **2026-07-07 정정 및 버그 수정**: 최초 제안 시점에는 킥보드/오토바이/차량/이동 중인 사람을 고위험으로, 가로수·소화전·보행로 적치물을 중위험으로, 횡단보도를 저위험(랜드마크)으로 구상했다. 실제 구현을 조사한 결과 `surface_gate.py`의 P0 노면 클래스명이 실제 4클래스 모델과 전혀 안 맞아 **노면 즉시경보가 한 번도 발동하지 않았고**, `l1_classifier.py`/`detection_pipeline.py`의 중위험 분류기 2개도 서로 다른 어휘(COCO 잔재, `kickboard`/`pothole`/`manhole`/`construction_cone` 등 실재하지 않는 클래스명)를 쓰며 어긋나 있던 **실제 코드 결함**임을 확인하고, 위 표를 실제 코드 기준으로 수정 완료했다(가로수/소화전/보행로 적치물도 이제 중위험으로 정상 반영됨). `tests/test_langgraph.py::TestRiskClassifierConsistency`가 재발을 방지한다.

---

## 4. 시각장애인 보호법(Self-Protection) 연동 설계

시각장애인이 보행 중 위험한 돌출 사물에 대비하기 위해 사용하는 **신체보호법**을 AI 음성 가이드와 햅틱으로 보강합니다.

1. **상체 보호법 (Upper Body Protection) 보완**
   - **이론**: 머리나 어깨 등 상체 높이에 있는 나뭇가지, 열려 있는 트럭 적재함 등은 흰지팡이로 감지하기 힘들어 충돌 사고 위험이 매우 높습니다.
   - **AI 대응(제안, 미구현)**: Yolo 26N - Object Detection에서 카메라 상단 임계 영역(Y축 상단 40% 이상 영역)에 위치한 위험 객체 감지 시, 중위험 사물이라도 **고위험(High) 수준으로 격상**시켜 "상체 머리 위 주의" 사전합성 음성을 출력하는 것을 제안한다.
   - **2026-07-07 현황**: `server/detection/gates/`, `server/orchestration/nodes/` 전역을 확인한 결과 이 Y축 기반 격상 로직은 아직 구현되어 있지 않다(코드 미존재). 후속 작업 후보로 남겨둔다.
2. **햅틱(Haptic) 패턴 이중화**
   - 보행지도사 이론 상 시각장애인은 촉각에 고도로 의존합니다.
   - 고위험(Reflex) 시에는 **연속적인 단발성 강한 진동(Error Haptic)**을 주어 즉각 멈추게 유도하고, 중위험(Cognitive) 우회 지시 시에는 **부드러운 이중 진동(Warning Haptic)**을 가이드 음성 시작 시점에 함께 보내 정보의 인지적 대비를 강화합니다.

---

## 5. 결론 및 향후 반영 계획

본 분석 결과를 바탕으로 아래 모듈의 코드를 고도화합니다:
- **`server/detection/gates/` (3단계 게이트)**: Bounding Box의 크기와 Y축 좌표, 노면 분할 클래스를 조합하여 고위험(Reflex) 분류 가이드를 확립합니다.
- **`server/orchestration/nodes/` (6단계 LLM)**: 자기중심 준거 틀(Egocentric Frame)과 클록 포지션을 기반으로 문장 템플릿의 가이드라인을 강제화합니다.
- **`client/src/services/hapticEngine.ts` (7단계 햅틱)**: 보행이론 촉각 반응 모델에 입각한 진동 피드백 패턴을 구현합니다.
