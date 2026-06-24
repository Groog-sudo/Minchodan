---
name: rag-realtime-search
description: |
  ChromaDB 로컬 벡터 DB와 Ollama nomic-embed-text 임베딩을 사용하여
  탐지된 장애물에 대한 행동 수칙을 50ms 이내로 검색하는 실시간 RAG 검색 모듈.
  VectorDBFactory로 Chroma  Qdrant 핫스왑을 지원한다.
---

# RAG Realtime Search (5단계: 실시간 대처 수칙 검색)

> **작성일**: 2026-06-24
> **버전**: v0.1.0
> **설계 기준**: `docs/minchodan_design_note.md` 5단계

## 개요

3단계(YOLO26 객체 탐지)에서 감지된 장애물 정보를 기반으로, 4단계에서 구축한 ChromaDB 로컬 벡터 DB에서 관련 행동 수칙을 **50ms 이내**에 검색하여 LangGraph 상태에 RAG 컨텍스트로 주입한다.

## 핵심 가치

- **API 비용 제로**: 로컬 임베딩(nomic-embed-text)만 사용하여 외부 API 호출 없음
- **초고속 매칭**: ChromaDB의 HNSW 인덱스 활용으로 50ms 미만 응답
- **오프라인 동작**: 인터넷 연결 없이도 완전 작동

## 시스템 내 위치

```
[3단계: YOLO26 탐지]  detected_classes
        
[5단계: RAG 실시간 검색]  ChromaDB (4단계에서 구축)
        
[6단계: LangGraph 가이드 생성]  rag_context
```

## 기술 스택

| 구성 요소 | 기술 | 버전/모델 |
|-----------|------|-----------|
| 벡터 DB | ChromaDB | >= 0.5.x |
| 임베딩 모델 | Ollama nomic-embed-text | nomic-embed-text:latest |
| 유사도 측정 | Cosine Distance | ChromaDB 기본값 |
| 상태 관리 | LangGraph State | langgraph >= 0.2.x |
| 추상화 | VectorDBFactory | Chroma  Qdrant 핫스왑 |

## 디렉토리 구조 (Minchodan 기준)

```
server/rag/
├── retriever.py               # similarity_search_with_score(k=5)
├── fallback.py                # 유사도 미달 시 룰 기반 fallback
└── vector_db_factory.py       # Chroma  Qdrant 핫스왑 추상화
```

## 핵심 구현 절차

### 단계 5-1. ChromaDB 로컬 인스턴스 로드 (읽기 전용)

```python
# server/rag/retriever.py
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434",
)

vector_db = Chroma(
    persist_directory="data/chroma_db",
    embedding_function=embeddings,
    collection_name="safety_guidelines",
)
```

> 서버 시작 시 워밍업 필수. 4단계에서 `data/chroma_db`에 데이터가 persist되어 있어야 함.

### 단계 5-2. 탐지 클래스  검색 쿼리 변환

```python
# server/rag/retriever.py (계속)

OBSTACLE_KR_MAP = {
    "car": "자동차", "truck": "트럭", "bus": "버스",
    "kickboard": "전동 킥보드", "bollard": "볼라드", "stair": "계단",
    "pothole": "포트홀", "manhole": "맨홀", "crosswalk": "횡단보도",
    "braille_damaged": "점자블록 파손", "sidewalk_damaged": "보도 파손",
}

def build_search_query(detected_classes: list, positions: list = None) -> str:
    if not detected_classes:
        return "보행 중 일반 안전 수칙"
    primary = detected_classes[0]
    kr_name = OBSTACLE_KR_MAP.get(primary, primary)
    query = f"{kr_name} 보행 중 회피 방법"
    if len(detected_classes) > 1:
        secondary = [OBSTACLE_KR_MAP.get(c, c) for c in detected_classes[1:3]]
        query += f" 및 {', '.join(secondary)} 주의"
    if positions and positions[0]:
        query += f" {positions[0]}"
    return query
```

### 단계 5-3. 유사도 검색 실행

```python
# server/rag/retriever.py (계속)
import time
from server.rag.fallback import get_fallback_guidance

async def search(detected_classes: list, positions: list = None) -> dict:
    query = build_search_query(detected_classes, positions)
    start_time = time.perf_counter()

    try:
        results = vector_db.similarity_search_with_score(query, k=5)
    except Exception as e:
        return _create_fallback(detected_classes, query, error=str(e))

    latency_ms = (time.perf_counter() - start_time) * 1000
    if latency_ms > 50:
        logger.warning(f"검색 지연 초과: {latency_ms:.1f}ms > 50ms")

    # 점수 필터링 (cosine distance: 낮을수록 유사)
    filtered = [(doc, score) for doc, score in results if score <= 0.3]

    if not filtered:
        return _create_fallback(detected_classes, query)

    rag_context = "\n".join([doc.page_content for doc, _ in filtered])
    return {
        "rag_context": rag_context,
        "results": [{"content": doc.page_content, "score": round(1 - score, 4), "metadata": doc.metadata} for doc, score in filtered],
        "is_fallback": False,
        "latency_ms": round(latency_ms, 2),
        "query": query,
    }
```

### 단계 5-4. Fallback 룰

```python
# server/rag/fallback.py

FALLBACK_RULES = {
    "car": "전방에 차량이 있습니다. 즉시 멈추고 차량이 지나갈 때까지 대기하세요.",
    "kickboard": "전동 킥보드가 근처에 있습니다. 주의하며 옆으로 피하세요.",
    "bollard": "전방에 볼라드가 있습니다. 좌측 또는 우측으로 피해 지나가세요.",
    "stair": "전방에 계단이 있습니다. 난간을 잡고 천천히 이동하세요.",
    "crosswalk": "전방 횡단보도입니다. 주변을 확인하고 천천히 건너세요.",
    "braille_damaged": "전방 점자블록이 파손되어 있습니다. 우측으로 우회하세요.",
}
DEFAULT_FALLBACK = "전방에 장애물이 감지되었습니다. 천천히 멈추고 주변을 확인하세요."

def get_fallback_guidance(detected_classes: list) -> str:
    if not detected_classes:
        return DEFAULT_FALLBACK
    guidance = FALLBACK_RULES.get(detected_classes[0], DEFAULT_FALLBACK)
    if len(detected_classes) > 1:
        guidance += " 추가 장애물이 감지되었으니 각별히 주의하세요."
    return guidance
```

### 단계 5-5. VectorDBFactory 추상화

```python
# server/rag/vector_db_factory.py
from typing import Protocol

class VectorStore(Protocol):
    def similarity_search_with_score(self, query: str, k: int): ...

class ChromaStore:
    """ChromaDB 구현"""
    def __init__(self, persist_dir: str, embedding_fn, collection: str):
        from langchain_community.vectorstores import Chroma
        self.store = Chroma(persist_directory=persist_dir, embedding_function=embedding_fn, collection_name=collection)
    def similarity_search_with_score(self, query, k=5):
        return self.store.similarity_search_with_score(query, k=k)

class QdrantStore:
    """Qdrant 구현 (핫스왑 대비)"""
    def __init__(self, url: str, embedding_fn, collection: str):
        from langchain_community.vectorstores import Qdrant
        # Qdrant 초기화 (post-MVP)
        raise NotImplementedError("Qdrant는 post-MVP 핫스왑 대상")

def create_vector_store(provider: str = "chroma", **kwargs) -> VectorStore:
    if provider == "chroma": return ChromaStore(**kwargs)
    elif provider == "qdrant": return QdrantStore(**kwargs)
    raise ValueError(f"지원하지 않는 VectorDB: {provider}")
```

## 데이터 인터페이스

| 방향 | 페이로드 |
| --- | --- |
| In | 탐지 클래스/쿼리(String) |
| Out | 결합 컨텍스트(String) — LangGraph `state["rag_context"]`에 저장 |

## 의존성·예외

- 선행 = 3단계 라벨 + 4단계 DB. 출력 = 6단계 Context.
- DB 손상/경로 부재(`FileNotFoundError`); 유사도 기준 미달 시 디폴트 안내 문자열 반환(중단 금지).

## 성능 최적화

| 전략 | 설명 |
|------|------|
| 싱글톤 인스턴스 | ChromaDB 인스턴스를 서버 수명 동안 1회만 생성 |
| Top-K 제한 | k=5로 제한 |
| 점수 필터링 | 임계값 미달 결과 제거 |
| 임베딩 캐싱 | 동일 쿼리 반복 시 캐싱 (LRU) |

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| 읽기 전용 로드 | `Chroma(persist_directory, embedding_function)` | 인스턴스 생성 |
| kickboard 쿼리 정합 | 원본 수칙 일치 반환 + score 정상 | 정합 확인 |
| **검색 지연** | 전체 검색 소요 | **< 50ms** |
| k=5 | 상위 5건 반환 | `len(results) <= 5` |
| 미적중 fallback | 디폴트 안내 문자열 반환 | `is_fallback=True` |
| DB 손상 가드 | `FileNotFoundError` 시 안내 문자열 | 중단 없음 |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- 아키텍처 설계서: [`docs/architecture.md`](../../../docs/architecture.md) 5.5절
