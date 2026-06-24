---
name: llm-guidance-orchestrator
description: |
  LangGraph 3계층 오케스트레이션(L1 룰 분류  L2 Gemma2 문장 생성  L3 가드레일 검증)으로
  탐지 장애물과 RAG 수칙을 종합하여 20자 이내 한국어 회피 안내 문장을 생성하는 모듈.
  LLMClientFactory로 로컬(Ollama)  상용(gpt-4o-mini) 핫스왑을 지원한다.
---

# LLM Guidance Orchestrator (6단계: 종합 회피 가이드 생성)

> **작성일**: 2026-06-24
> **버전**: v0.2.0
> **설계 기준**: `docs/minchodan_design_note.md` 6단계
> **코딩 패턴 준수**: [`docs/course_codebase_guide.md`](../../../docs/course_codebase_guide.md) 섹션 14, 12, 11, 17.2

## 개요

3단계(YOLO26)에서 탐지된 장애물 정보와 5단계(RAG)에서 검색된 행동 수칙을 종합하여, **로컬 Gemma2 모델**로 시각장애인이 즉시 이해할 수 있는 **20자 이내 한국어 1문장 회피 안내**를 생성한다.

## 핵심 가치

- **네트워크 RTT 제거**: Ollama 로컬 추론으로 네트워크 왕복 지연 제거
- **토큰 API 비용 제로**: 상용 API 미사용 (fallback 시에만 gpt-4o-mini 호출)
- **가드레일 검증**: 생성문의 길이·방향 키워드·안전성을 자동 검증

## 시스템 내 위치

```
[3단계: YOLO26 탐지]  detected_classes, risk_level
[5단계: RAG 검색]  rag_context
        
[6단계: LLM 가이드 오케스트레이터]
   ├── L1: 룰 기반 위험도 분류 (high는 이미 반사 경로에서 처리됨, mid/low만 진입)
   ├── L2: ChatOllama(Gemma2) ainvoke — 20자/방향 포함
   └── L3: 가드레일 검증, RETRY(최대 1회)
        
[7단계: 실시간 TTS]  guidance_text
```

> **주의**: `high` 위험도는 3단계 Reflex/Surface Gate에서 이미 반사 경로(사전합성 클립)로 처리됩니다. L1은 **mid/low만 진입**시킵니다.

## 3계층 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                   LangGraph StateGraph               │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │  L1 노드  │───▶│  L2 노드  │───▶│  L3 노드  │      │
│  │ 위험도 분류│    │ 문장 생성  │    │ 검증/재시도│      │
│  └──────────┘    └──────────┘    └──────────┘       │
│       │               ▲               │              │
│       │ high(이미처리) │ RETRY(1회)    │              │
│       ▼               └───────────────┘              │
│  [진입 차단]                       │ PASS/FINAL_FAIL │
│                                     ▼                │
│                              [최종 guidance_text]     │
│                              또는 정적 fallback        │
└─────────────────────────────────────────────────────┘
```

## 기술 스택

| 구성 요소 | 기술 | 버전/모델 |
|-----------|------|-----------|
| LLM (기본) | Ollama Gemma2 | gemma2:9b |
| LLM (Fallback) | OpenAI GPT-4o-mini | gpt-4o-mini |
| 오케스트레이션 | LangGraph | >= 0.2.x |
| LLM 래퍼 | LangChain ChatOllama / ChatOpenAI | langchain >= 0.3 |
| 추상화 | LLMClientFactory | BaseChatModel 핫스왑 |

## 디렉토리 구조 (Minchodan 기준)

```
server/orchestration/
├── state.py                   # OrchState TypedDict
├── graph.py                   # StateGraph 조립, 노드 등록, 엣지 정의
├── llm_client_factory.py      # BaseChatModel Ollama  gpt-4o-mini 핫스왑
└── nodes/
    ├── l1_classifier.py       # L1: 룰 기반 위험도 분류 (mid/low만 진입)
    ├── l2_generator.py        # L2: ChatOllama(Gemma2) ainvoke
    ├── l3_validator.py        # L3: 길이·방향 검증, RETRY(최대 1회)
    └── fallback_node.py       # 최종 실패  고정 문장
```

## 핵심 구현 절차

### 단계 6-1. State 정의

```python
# -*- coding: utf-8 -*-
# server/orchestration/state.py
import sys
from typing import List, Literal, Optional, TypedDict

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

class OrchState(TypedDict, total=False):
    event: dict
    detected_classes: List[str]
    risk_level: Literal["high", "mid", "low"]
    rag_context: str
    positions: List[str]
    guidance_text: str
    direction: Literal["좌", "우", "직진", "정지", ""]
    verified: bool
    retry_count: int
    validation_errors: List[str]
    used_fallback_llm: bool
    used_static_fallback: bool
    total_latency_ms: float
```

### 단계 6-2. L1 노드 — 룰 기반 위험도 분류

```python
# -*- coding: utf-8 -*-
# server/orchestration/nodes/l1_classifier.py
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

MID_RISK_CLASSES = {"bicycle", "kickboard", "pothole", "manhole", "construction_cone"}
# high 위험도는 3단계 게이트에서 이미 반사 경로로 처리됨

def classify_risk(detected_classes: list) -> str:
    for cls in detected_classes:
        if cls in MID_RISK_CLASSES: return "mid"
    return "low"

async def l1_classifier_node(state: dict) -> dict:
    detected_classes = state.get("detected_classes", [])
    risk_level = classify_risk(detected_classes)
    return {"risk_level": risk_level, "retry_count": 0}
```

### 단계 6-3. L2 노드 — Gemma2 가이드 생성

```python
# -*- coding: utf-8 -*-
# server/orchestration/llm_client_factory.py
import os
import sys

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# 환경 변수 및 절대 경로 설정 (가이드 3.3, 3.4 준수)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path)

class LLMClientFactory:
    """BaseChatModel 핫스왑: Ollama / gpt-4o-mini"""
    _ollama: ChatOllama = None
    _openai: ChatOpenAI = None

    @classmethod
    def get_ollama(cls) -> ChatOllama:
        if cls._ollama is None:
            cls._ollama = ChatOllama(model="gemma2:9b", base_url="http://localhost:11434", temperature=0.3, num_predict=50)
        return cls._ollama

    @classmethod
    def get_openai(cls) -> ChatOpenAI:
        if cls._openai is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
            # 가이드 17.2: API 키 부재 시 방어적 폴백
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            cls._openai = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, max_tokens=50, api_key=api_key)
        return cls._openai

    @classmethod
    def get_client(cls, provider: str = "ollama"):
        if provider == "openai": return cls.get_openai()
        return cls.get_ollama()
```

```python
# -*- coding: utf-8 -*-
# server/orchestration/nodes/l2_generator.py
import sys

from langchain.schema import HumanMessage, SystemMessage

from server.orchestration.llm_client_factory import LLMClientFactory

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

GUIDANCE_SYSTEM_PROMPT = """당신은 시각장애인 보행 보조 AI입니다.
탐지된 장애물 정보와 안전 수칙을 바탕으로 즉각적인 회피 안내를 생성합니다.

[규칙]
1. 반드시 한국어 1문장으로 작성
2. 20자 이내 (공백 포함)
3. 방향 키워드(좌/우/직진/정지) 중 하나를 반드시 포함
4. 존댓말(~하세요, ~세요) 사용
5. 간결하고 즉시 이해 가능한 표현 사용

[좋은 예시]
- "좌측으로 피하세요" (9자)
- "우측 보도로 이동하세요" (11자)
- "전방 주의, 정지하세요" (11자)
"""

async def l2_generator_node(state: dict) -> dict:
    llm = LLMClientFactory.get_client("ollama")
    user_prompt = f"[탐지 장애물]: {', '.join(state.get('detected_classes', []))}\n[위험도]: {state.get('risk_level', 'mid')}\n[안전 수칙]:\n{state.get('rag_context', '관련 수칙 없음')}\n\n위 정보를 바탕으로 20자 이내 한국어 1문장 회피 안내를 작성하세요."

    messages = [SystemMessage(content=GUIDANCE_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    response = await llm.ainvoke(messages)
    guidance_text = response.content.strip()
    direction = extract_direction(guidance_text)
    return {"guidance_text": guidance_text, "direction": direction}

def extract_direction(text: str) -> str:
    for d, keywords in {"좌": ["좌측","좌","왼쪽"], "우": ["우측","우","오른쪽"], "직진": ["직진","앞으로"], "정지": ["정지","멈추","서세요"]}.items():
        if any(kw in text for kw in keywords): return d
    return ""
```

### 단계 6-4. L3 노드 — 가드레일 검증

```python
# -*- coding: utf-8 -*-
# server/orchestration/nodes/l3_validator.py
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

MAX_LEN = 20
MAX_RETRY = 1

def validate_guidance(text: str) -> tuple:
    errors = []
    if not text or not text.strip(): return False, ["빈 문장"]
    if len(text) > MAX_LEN: errors.append(f"길이 초과: {len(text)}자 > {MAX_LEN}자")
    if not any(kw in text for kw in ["좌","우","왼","오른","직진","정지","멈추"]): errors.append("방향 키워드 미포함")
    if not any('\uac00' <= c <= '\ud7a3' for c in text): errors.append("한국어 미포함")
    return len(errors) == 0, errors

async def l3_validator_node(state: dict) -> dict:
    text = state.get("guidance_text", "")
    retry = state.get("retry_count", 0)
    is_valid, errors = validate_guidance(text)

    if is_valid: return {"verified": True, "validation_errors": []}

    if retry < MAX_RETRY:
        return {"verified": False, "retry_count": retry + 1, "validation_errors": errors}
    else:
        return {"verified": True, "guidance_text": "전방 주의, 천천히 멈추세요", "direction": "정지", "used_static_fallback": True, "validation_errors": errors}
```

### 단계 6-5. Fallback 노드

```python
# -*- coding: utf-8 -*-
# server/orchestration/nodes/fallback_node.py
import sys

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# 최종 실패 시 고정 문장 반환
FALLBACK_MESSAGE = "전방 주의, 천천히 멈추세요"

async def fallback_node(state: dict) -> dict:
    return {"guidance_text": FALLBACK_MESSAGE, "direction": "정지", "used_static_fallback": True, "verified": True}
```

### 단계 6-6. LangGraph StateGraph 조립

```python
# -*- coding: utf-8 -*-
# server/orchestration/graph.py
import sys

from langgraph.graph import END, StateGraph

from server.orchestration.nodes.l1_classifier import l1_classifier_node
from server.orchestration.nodes.l2_generator import l2_generator_node
from server.orchestration.nodes.l3_validator import l3_validator_node
from server.orchestration.state import OrchState

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

def route_after_l3(state: dict) -> str:
    if state.get("verified"): return "end"
    return "l2_generate"

def build_graph():
    graph = StateGraph(OrchState)
    graph.add_node("l1_classify", l1_classifier_node)
    graph.add_node("l2_generate", l2_generator_node)
    graph.add_node("l3_validate", l3_validator_node)
    graph.set_entry_point("l1_classify")
    graph.add_edge("l1_classify", "l2_generate")
    graph.add_edge("l2_generate", "l3_validate")
    graph.add_conditional_edges("l3_validate", route_after_l3, {"l2_generate": "l2_generate", "end": END})
    return graph.compile()

_compiled = None
def get_orchestrator():
    global _compiled
    if _compiled is None: _compiled = build_graph()
    return _compiled
```

## 핫스왑 라우팅 (LLMClientFactory)

| 조건 | 전환 |
| --- | --- |
| 기본 | ChatOllama(gemma2:9b) 로컬 |
| L3 실패율 > 10% | gpt-4o-mini 자동 전환 |
| `LLM_PROVIDER=openai` | gpt-4o-mini 강제 |
| L3 최종 실패 | 고정 문장("전방 주의, 천천히 멈추세요") |

## 데이터 인터페이스

| 방향 | 페이로드 |
| --- | --- |
| In | `OrchState{event, risk_level, rag_context}` |
| Out | 가이드 문장(String) — 20자 내, 방향 포함 |

## 의존성·예외

- 선행 = 3·5단계. 출력 = 7단계.
- API 장애/Rate Limit/네트워크 차단 시 디폴트 수칙 문장 즉시 반환(프레임워크 정지 금지).

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| bollard 주입 가이드 | 20자 내 안내 정상 적재 | 길이 <= 20 |
| 방향 키워드 포함 | 좌/우/직진/정지 중 하나 | 키워드 존재 |
| L1 위험도 분류 | high 제외, mid/low만 진입 | high 진입 안 함 |
| L2 Gemma2 ainvoke | 한국어 1문장 생성 | 한국어 포함 |
| L3 검증 + RETRY | 위반 시 RETRY(최대 1회) | retry_count <= 1 |
| Fallback 고정 문장 | 최종 실패 시 "전방 주의, 천천히 멈추세요" | 문장 일치 |
| 조건부 분기 | StateGraph 엣지 정상 | END 도달 |
| API 장애 디폴트 | Rate Limit 시 디폴트 수칙 반환 | 중단 없음 |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- 아키텍처 설계서: [`docs/architecture.md`](../../../docs/architecture.md) 5.6절
