# 실시간 RAG 검색 — 구현 상세 참조 문서

## 1. Cosine Distance 유사도 점수 산출 이론

### 1.1 Cosine Similarity vs. Cosine Distance

ChromaDB는 기본적으로 **Cosine Distance**를 사용한다:

```
Cosine Similarity = cos(θ) = (A · B) / (||A|| × ||B||)
Cosine Distance = 1 - Cosine Similarity
```

| 값 | Cosine Similarity | Cosine Distance | 의미 |
|----|-------------------|-----------------|------|
| 완전 일치 | 1.0 | 0.0 | 쿼리와 문서가 의미적으로 동일 |
| 유사함 | 0.8 | 0.2 | 높은 관련성 |
| 보통 | 0.5 | 0.5 | 중간 관련성 |
| 무관함 | 0.0 | 1.0 | 관련 없음 |

### 1.2 점수 임계값 설정 근거

`score_threshold = 0.7` (Cosine Similarity 기준)
- ChromaDB 반환값은 **distance**이므로 `distance <= 0.3`인 결과만 유효
- 실험적으로 보행 안전 수칙 도메인에서:
  - `similarity >= 0.7`: 직접 관련 수칙 (예: "자동차 회피"  "차량 접근 시 행동 수칙")
  - `0.5 <= similarity < 0.7`: 간접 관련 (노이즈 가능)
  - `similarity < 0.5`: 무관한 결과

### 1.3 nomic-embed-text 임베딩 모델 특성

| 속성 | 값 |
|------|-----|
| 모델명 | nomic-embed-text |
| 차원수 | 768 |
| 컨텍스트 길이 | 8192 토큰 |
| 한국어 지원 | 다국어 지원 (한국어 포함) |
| 로컬 추론 속도 | ~5ms/쿼리 (CPU), ~1ms/쿼리 (GPU) |
| 메모리 사용 | ~500MB RAM |

---

## 2. ChromaDB 검색 성능 벤치마크

### 2.1 예상 성능 지표 (로컬 환경)

| 문서 수 | Top-K | 평균 지연 | P99 지연 |
|---------|-------|-----------|---------|
| 100 | 5 | ~3ms | ~8ms |
| 500 | 5 | ~5ms | ~12ms |
| 1,000 | 5 | ~8ms | ~18ms |
| 5,000 | 5 | ~15ms | ~35ms |
| 10,000 | 5 | ~25ms | ~45ms |

> 목표: **50ms 이내**  문서 10,000건까지 목표 달성 가능

### 2.2 HNSW 인덱스 파라미터 (ChromaDB 기본값)

```python
# ChromaDB 내부 기본값 (커스터마이징 가능)
hnsw_params = {
    "space": "cosine",       # 거리 함수
    "ef_construction": 128,  # 인덱스 구축 시 탐색 범위
    "ef_search": 64,         # 검색 시 탐색 범위
    "M": 16,                 # 각 노드의 최대 연결 수
}
```

### 2.3 성능 최적화 옵션

```python
# ChromaDB 컬렉션 생성 시 커스텀 메타데이터 설정
collection = client.get_or_create_collection(
    name="safety_guidelines",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:search_ef": 100,        # 기본 64  100 (정확도 향상)
        "hnsw:construction_ef": 200,  # 기본 128  200 (구축 품질 향상)
    }
)
```

---

## 3. 쿼리 최적화 전략

### 3.1 쿼리 확장 기법

단순 키워드 쿼리보다 자연어 문장 쿼리가 임베딩 모델에서 더 높은 정확도를 보임:

```python
# 나쁜 예시 (키워드 나열)
query = "자동차 회피"

# 좋은 예시 (자연어 문장)
query = "자동차 보행 중 회피 방법"

# 더 나은 예시 (컨텍스트 포함)
query = "전방 좌측에 자동차가 접근 중일 때 시각장애인 보행 회피 방법"
```

### 3.2 복합 장애물 쿼리 전략

```python
# 복수 장애물 탐지 시: 각 장애물별 개별 쿼리 + 결과 병합
async def multi_obstacle_search(detected_classes: List[str]) -> str:
    """복수 장애물 탐지 시 검색 전략"""
    if len(detected_classes) == 1:
        # 단일 장애물: 표준 쿼리
        return await engine.search(detected_classes)

    # 우선순위가 높은 장애물(차량 등)만 메인 쿼리
    # 나머지는 보조 컨텍스트로 활용
    priority_order = ["car", "truck", "bus", "motorcycle", "bicycle",
                       "kickboard", "pothole", "staircase"]
    sorted_classes = sorted(
        detected_classes,
        key=lambda x: priority_order.index(x) if x in priority_order else 99
    )
    return await engine.search(sorted_classes)
```

### 3.3 LRU 임베딩 캐시 구현

```python
from functools import lru_cache
import hashlib

class CachedEmbeddingFunction:
    """동일 쿼리의 임베딩 결과를 캐싱하여 Ollama 호출 최소화"""

    def __init__(self, base_embedder: OllamaEmbeddings, cache_size: int = 256):
        self._embedder = base_embedder
        self._cache_size = cache_size
        self._cache = {}

    def embed_query(self, text: str) -> List[float]:
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        embedding = self._embedder.embed_query(text)

        # LRU 방식: 캐시 초과 시 가장 오래된 항목 제거
        if len(self._cache) >= self._cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[cache_key] = embedding
        return embedding
```

---

## 4. 테스트 시나리오

### 4.1 단위 테스트

```python
# tests/test_rag_search.py
import pytest
from server.rag.query_builder import build_search_query
from server.rag.fallback_rules import get_fallback_guidance

class TestQueryBuilder:
    def test_single_obstacle(self):
        query = build_search_query(["car"])
        assert "자동차" in query
        assert "보행 중 회피 방법" in query

    def test_multiple_obstacles(self):
        query = build_search_query(["car", "pothole", "bicycle"])
        assert "자동차" in query
        assert "포트홀" in query

    def test_empty_classes(self):
        query = build_search_query([])
        assert query == "보행 중 일반 안전 수칙"

    def test_unknown_class(self):
        query = build_search_query(["unknown_object"])
        assert "unknown_object" in query  # 원본 클래스명 유지

    def test_with_position(self):
        query = build_search_query(["car"], ["전방 좌측"])
        assert "전방 좌측" in query

class TestFallbackRules:
    def test_known_obstacle(self):
        guidance = get_fallback_guidance(["car"])
        assert "차량" in guidance or "자동차" in guidance

    def test_unknown_obstacle(self):
        guidance = get_fallback_guidance(["unknown"])
        assert "장애물" in guidance  # 기본 fallback

    def test_multiple_obstacles_adds_warning(self):
        guidance = get_fallback_guidance(["car", "pothole"])
        assert "추가 장애물" in guidance

    def test_empty_classes(self):
        guidance = get_fallback_guidance([])
        assert "천천히 멈추" in guidance
```

### 4.2 통합 테스트

```python
# tests/test_rag_integration.py
import pytest
import time
from server.rag.search_engine import RAGSearchEngine

@pytest.fixture
def search_engine():
    return RAGSearchEngine()

class TestRAGSearchIntegration:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, search_engine):
        result = await search_engine.search(["car"])
        assert "rag_context" in result
        assert isinstance(result["rag_context"], str)
        assert len(result["rag_context"]) > 0

    @pytest.mark.asyncio
    async def test_search_latency_under_50ms(self, search_engine):
        result = await search_engine.search(["pothole"])
        assert result["latency_ms"] < 50, f"검색 지연: {result['latency_ms']}ms"

    @pytest.mark.asyncio
    async def test_fallback_on_no_results(self, search_engine):
        # 존재하지 않는 장애물 클래스로 검색
        result = await search_engine.search(["nonexistent_object_xyz"])
        # fallback이 되거나 결과가 있거나 둘 중 하나
        assert result["rag_context"] is not None

    @pytest.mark.asyncio
    async def test_search_score_ordering(self, search_engine):
        result = await search_engine.search(["car"])
        if len(result["results"]) > 1:
            scores = [r["score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True), "결과는 유사도 내림차순이어야 함"
```

### 4.3 LangGraph 노드 테스트

```python
# tests/test_rag_node.py
import pytest
from server.orchestration.nodes.rag_search_node import rag_search_node

class TestRAGSearchNode:
    @pytest.mark.asyncio
    async def test_node_updates_state(self):
        input_state = {
            "detected_classes": ["car"],
            "positions": ["전방 중앙"],
        }
        output = await rag_search_node(input_state)
        assert "rag_context" in output
        assert "rag_is_fallback" in output
        assert "rag_latency_ms" in output
        assert isinstance(output["rag_context"], str)

    @pytest.mark.asyncio
    async def test_node_handles_empty_detection(self):
        input_state = {"detected_classes": [], "positions": []}
        output = await rag_search_node(input_state)
        assert output["rag_is_fallback"] is True
```

---

## 5. MariaDB 통계 쿼리 예시

```sql
-- 일별 검색 횟수 및 fallback 비율
SELECT
    DATE(created_at) AS search_date,
    COUNT(*) AS total_searches,
    SUM(is_fallback) AS fallback_count,
    ROUND(SUM(is_fallback) / COUNT(*) * 100, 1) AS fallback_rate_pct,
    ROUND(AVG(latency_ms), 2) AS avg_latency_ms,
    ROUND(MAX(latency_ms), 2) AS max_latency_ms
FROM rag_search_logs
GROUP BY DATE(created_at)
ORDER BY search_date DESC;

-- 장애물 유형별 검색 빈도
SELECT
    detected_classes,
    COUNT(*) AS search_count,
    ROUND(AVG(top_score), 4) AS avg_score,
    SUM(is_fallback) AS fallback_count
FROM rag_search_logs
GROUP BY detected_classes
ORDER BY search_count DESC
LIMIT 20;

-- 50ms 초과 검색 모니터링
SELECT
    id, query, latency_ms, created_at
FROM rag_search_logs
WHERE latency_ms > 50
ORDER BY created_at DESC
LIMIT 50;
```

---

## 6. 서버 시작 시 초기화 체크리스트

```python
# app/startup.py (FastAPI lifespan 이벤트에서 호출)

async def initialize_rag():
    """서버 시작 시 RAG 시스템 초기화 및 검증"""
    from server.rag.vector_store import VectorStoreManager

    # 1. Ollama 서버 상태 확인
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]
            assert "nomic-embed-text:latest" in model_names, \
                "nomic-embed-text 모델이 Ollama에 설치되어 있지 않습니다."
    except Exception as e:
        raise RuntimeError(f"Ollama 서버 연결 실패: {e}")

    # 2. ChromaDB 헬스 체크
    health = VectorStoreManager.health_check()
    if health["status"] == "empty":
        raise RuntimeError("ChromaDB에 문서가 없습니다. 4단계 임베딩을 먼저 실행하세요.")

    logger.info(f"RAG 시스템 초기화 완료: {health['document_count']}개 문서 로드됨")

    # 3. 워밍업 쿼리 (첫 쿼리 지연 방지)
    engine = RAGSearchEngine()
    warmup_result = await engine.search(["car"])
    logger.info(f"워밍업 검색 완료: {warmup_result['latency_ms']}ms")
```

---

## 7. 트러블슈팅 가이드

| 문제 | 원인 | 해결책 |
|------|------|--------|
| `ConnectionRefusedError: localhost:11434` | Ollama 서버 미실행 | `ollama serve` 실행 후 재시작 |
| `Collection not found` | 4단계 벡터 DB 미생성 | 4단계 스킬의 임베딩 파이프라인 실행 |
| 검색 결과 항상 fallback | 임베딩 모델 불일치 | 4단계와 동일한 `nomic-embed-text` 사용 확인 |
| 지연 50ms 초과 | 문서 수 과다 또는 CPU 부하 | HNSW 파라미터 튜닝, 문서 정리 |
| `OutOfMemoryError` | 임베딩 모델 메모리 부족 | GPU 사용 또는 배치 크기 축소 |
| 한국어 검색 정확도 낮음 | 쿼리 형식 부적절 | 자연어 문장 형식 쿼리 사용 (3.1절 참조) |
