# YOLO/TTS MVP 다음 작업 계획

> **작성일**: 2026-06-30
> **버전**: v0.1.0
> **담당 브랜치**: `th`
> **작업 원칙**: 2026-07-01부터 핵심 로직은 담당자가 직접 코드를 입력하고, LLM은 큰 틀·연결·검증을 보조합니다.

---

## 1. 현재 완료 상태

| 구분 | 상태 | 근거 |
| --- | --- | --- |
| **브랜치** | 완료 | `th` 브랜치 기준 작업 |
| **원천데이터 위치** | 완료 | `.env`의 `AIHUB_WALK_DATASET_ROOT`로 외부 경로 참조 |
| **Git 제외** | 완료 | `.env`, `outputs/`, 샘플 이미지, 커스텀 weight 제외 |
| **AI Hub 구조 확인** | 완료 | 전체 파일 수 `541078`개 스캔 |
| **BBox XML 확인** | 완료 | `0820_26.xml` 기준 이미지 99장, 박스 887개 |
| **샘플 이미지 준비** | 완료 | `data/raw/aihub_walk_sample/`에 JPG 3장 로컬 복사 |
| **YOLO 샘플 추론** | 완료 | 샘플 3장 추론 및 TTS 문장 생성 확인 |
| **단위 테스트** | 완료 | `tests/test_detection.py` 21개 통과 |
| **단말 TTS 계약** | 완료 | `message_hint = {id, type, text}` 계약 고정 |

---

## 2. 내일 작업 원칙

내일부터는 LLM이 코드를 먼저 전부 작성하지 않습니다. 담당자가 발표에서 설명해야 하는 코드는 직접 입력하고, LLM은 옆에서 구조 설명, 오류 분석, 검증, 문서화를 맡습니다.

| 역할 | 담당 내용 |
| --- | --- |
| **태현 직접 작성** | 방향 계산, 거리 계산, 위험도 규칙, 안내 문장 규칙, 실행 명령어 |
| **LLM 보조** | 파일 구조 설명, 기존 코드 연결, import 오류 해결, pytest 검증, changelog 정리 |

---

## 3. 내일 1순위 작업

| 순서 | 작업 | 직접 칠 사람 | 대상 파일 | 완료 기준 |
| --- | --- | --- | --- | --- |
| 1 | 방향 계산 함수 다시 읽고 주석/설명 정리 | 태현 | `server/detection/direction.py` | bbox 중심점 계산을 말로 설명 가능 |
| 2 | 거리 계산 함수 이해 및 필요 시 조건 조정 | 태현 | `server/detection/direction.py` | area ratio 기준 설명 가능 |
| 3 | 위험도 규칙 직접 수정 | 태현 | `server/detection/risk_rules.py` | high/medium/low 판단 이유 설명 가능 |
| 4 | 안내 문장 매핑 직접 수정 | 태현 | `server/detection/risk_rules.py` | `오른쪽 앞 차량 주의` 생성 흐름 설명 가능 |
| 5 | YOLO 데모 명령 직접 실행 | 태현 | PowerShell | 샘플 3장 결과 재현 |
| 6 | 오류가 나면 원인 분석 및 최소 수정 | LLM | 관련 파일 | 기존 테스트 유지 |

---

## 4. 내일 직접 칠 코드 후보

### 4.1 방향 계산

담당자가 직접 입력하고 설명할 핵심 코드입니다.

```python
def estimate_direction(bbox, frame_width):
    center_x = bbox.x + bbox.w / 2
    ratio = center_x / frame_width

    if ratio < 0.33:
        return "front-left"
    if ratio > 0.66:
        return "front-right"
    return "front"
```

### 4.2 거리 계산

```python
def estimate_distance(bbox, frame_width, frame_height):
    area_ratio = (bbox.w * bbox.h) / (frame_width * frame_height)

    if area_ratio >= 0.25:
        return "near"
    if area_ratio >= 0.10:
        return "medium"
    return "far"
```

### 4.3 위험도 계산

```python
def estimate_risk_level(class_name, direction, distance):
    if distance == "near" and class_name in DANGER_CLASSES:
        return "high"
    if direction == "front" and class_name in {"obstacle", "bollard", "pole"}:
        return "high"
    if distance == "medium" and class_name in DANGER_CLASSES:
        return "medium"
    return "low"
```

---

## 5. 내일 실행 명령어

| 목적 | 명령 |
| --- | --- |
| 브랜치 확인 | `git branch --show-current` |
| 변경 상태 확인 | `git status --short` |
| detection 테스트 | `.\venv\Scripts\python.exe -m pytest tests\test_detection.py` |
| YOLO/TTS 데모 실행 | `.\venv\Scripts\python.exe scripts\run_yolo_tts_demo.py --input data\raw\aihub_walk_sample --model server\models\yolo26n\object_detection.pt --device cpu` |
| 결과 JSON 확인 | `Get-Content -Encoding UTF8 outputs\yolo_tts_demo\yolo_tts_demo_results.json` |

---

## 6. 내일 발표 설명으로 가져갈 문장

```txt
YOLO가 이미지에서 객체명, confidence, bbox를 추출합니다.
bbox 중심점의 x좌표를 화면 너비로 나누어 왼쪽, 정면, 오른쪽 방향을 계산했습니다.
bbox 면적이 화면에서 차지하는 비율로 가까움 정도를 near, medium, far로 나눴습니다.
객체 종류와 거리 정보를 이용해 위험도를 high, medium, low로 분류했습니다.
마지막으로 단말 TTS가 읽을 message_hint = {id, type, text}를 생성했습니다.
```

---

## 7. 내일 LLM에게 먼저 시킬 것

다음 세션에서 LLM은 바로 코드를 수정하지 말고 아래 순서로 시작해야 합니다.

| 순서 | LLM 행동 |
| --- | --- |
| 1 | `AGENTS.md`, `SKILLS.md`, `docs/llm_collaboration_workflow.md`, 본 문서를 읽습니다. |
| 2 | 오늘까지 완료된 파일과 테스트 결과를 요약합니다. |
| 3 | 담당자가 직접 칠 코드 범위를 20~40줄 이하로 제시합니다. |
| 4 | 담당자가 입력한 뒤 오류 로그를 받아 디버깅합니다. |
| 5 | 검증과 changelog만 LLM이 정리합니다. |

---

## 8. 보류 항목

| 항목 | 보류 이유 |
| --- | --- |
| **RAG 구축** | 이번 주 MVP 범위 제외 |
| **LangGraph 전체 구현** | 이번 주 MVP 범위 제외 |
| **서버 TTS 합성** | 이번 주는 React Native `react-native-tts` 데모 스탠드인 사용 |
| **전체 AI Hub 학습** | 발표용 1차 프로토타입 범위 초과 |
| **원천데이터 Git 업로드** | 금지. `.env` 경로 참조와 소량 샘플만 사용 |
