# LLM 가이드 오케스트레이터 — 구현 상세 참조 문서

## 1. LangGraph 실행 흐름 상세

### 1.1 전체 실행 시나리오

#### 시나리오 A: High 위험도 (최단 경로)
```
입력: detected_classes=["car"], risk_level 미설정
   L1: risk_level="high" 판정
   L1에서 즉시 guidance_text="전방 차량, 즉시 정지하세요" 생성
   END (L2/L3 건너뜀)
  총 소요: ~1ms
```

#### 시나리오 B: Mid/Low 위험도 + L3 통과 (정상 경로)
```
입력: detected_classes=["pothole"], rag_context="포트홀 발견 시..."
   L1: risk_level="mid"
   L2: gemma4-e4b 호출  guidance_text="좌측으로 피하세요"
   L3: 검증 통과 (9자, "좌측" 포함)
   END
  총 소요: ~300ms-1000ms (gemma4-e4b 추론 시간 의존)
```

#### 시나리오 C: L3 실패 + 재시도 성공
```
입력: detected_classes=["bicycle"]
   L1: risk_level="mid"
   L2(1차): guidance_text="자전거를 조심하세요" (방향 키워드 없음)
   L3: 검증 실패 ["방향 키워드 미포함"], retry_count=1
   L2(2차): guidance_text="우측으로 비키세요"
   L3: 검증 통과
   END
  총 소요: ~1000ms-4000ms
```

#### 시나리오 D: L3 최종 실패 + 정적 Fallback
```
입력: detected_classes=["unknown_object"]
   L1: risk_level="low"
   L2(1차): guidance_text="" (LLM 호출 실패)
   L3: 검증 실패 ["빈 문장"], retry_count=1
   L2(2차): guidance_text="Be careful ahead" (영어 출력)
   L3: 검증 실패 ["한국어 미포함"], retry_count >= max
   정적 fallback: "전방 주의, 천천히 멈추세요"
   END
  총 소요: ~2000ms-6000ms
```

#### 시나리오 E: 상용 API Fallback 라우팅
```
(최근 100건 중 L3 실패율 > 10%)
입력: detected_classes=["construction_cone"]
   L1: risk_level="mid"
   L2: should_use_fallback()=True  GPT-4o-mini 호출
   L2: guidance_text="우측 우회로 가세요"
   L3: 검증 통과
   END
  총 소요: ~300ms-800ms (네트워크 포함)
```

### 1.2 상태 전이 다이어그램

```
                    ┌────────────────┐
                    │   START        │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  L1: 위험도 분류 │
                    └───────┬────────┘
                            │
                  ┌─────────┴─────────┐
                  │                   │
             high │              mid/low │
                  │                   │
          ┌───────▼──────┐   ┌───────▼────────┐
          │ 즉시 긴급안내  │   │  L2: 문장 생성   │◄──┐
          │ (사전 정의문)  │   └───────┬────────┘   │
          └───────┬──────┘           │              │
                  │           ┌───────▼────────┐   │
                  │           │  L3: 가드레일    │   │
                  │           │     검증        │   │
                  └───────────┴───────┬────────┘   │
                                      │            │
                            ┌─────────┴─────────┐  │
                            │                   │  │
                       통과  │          실패+재시도│  │
                            │          가능     │  │
                            │                   │  │
                            │           ┌───────┘  │
                            │           │ RETRY    │
                            │           └──────────┘
                            │
                            │  실패+재시도 불가
                            │   정적 fallback
                            │
                            ▼
                     ┌────────────────┐
                     │      END       │
                     │ guidance_text  │
                     └────────────────┘
```

---

## 2. 프롬프트 엔지니어링 세부사항

### 2.1 시스템 프롬프트 설계 원칙

| 원칙 | 적용 |
|------|------|
| **역할 명시** | "시각장애인 보행 보조 AI" 명확히 정의 |
| **제약 조건 수치화** | "20자 이내", "1문장", "한국어" 구체적 수치 |
| **필수 요소 명시** | "방향(좌/우/직진/정지) 포함" |
| **Few-shot 예시** | 좋은 예시 4개 + 나쁜 예시 2개 제공 |
| **출력 형식 고정** | 순수 텍스트만 반환, JSON/마크다운 금지 |

### 2.2 프롬프트 변형 (위험도별)

```python
# Mid 위험도: 회피 방향 강조
GUIDANCE_USER_PROMPT_MID = """[탐지 장애물]: {detected_classes}
[장애물 위치]: {positions}
[위험도]: 중간
[안전 수칙]:
{rag_context}

장애물을 피하는 방향을 포함하여 20자 이내 안내를 작성하세요."""

# Low 위험도: 주의 안내
GUIDANCE_USER_PROMPT_LOW = """[탐지 장애물]: {detected_classes}
[장애물 위치]: {positions}
[위험도]: 낮음
[안전 수칙]:
{rag_context}

주의 사항을 20자 이내로 안내하세요. 직진 가능하면 직진을 안내하세요."""
```

### 2.3 재시도 시 프롬프트 보강

L3 검증 실패 후 재시도 시, 검증 실패 사유를 프롬프트에 추가:

```python
RETRY_PROMPT_SUFFIX = """
[이전 생성 결과 문제점]: {validation_errors}
[주의]: 반드시 아래 조건을 지키세요:
- 방향 키워드(좌측/우측/직진/정지) 중 하나 필수 포함
- 20자 이내 (현재 {current_length}자  줄여야 함)
- 한국어만 사용

다시 작성하세요."""
```

### 2.4 gemma4-e4b 모델 특성 고려사항

| 특성 | 설명 | 대응 |
|------|------|------|
| 한국어 품질 | 영어 대비 한국어 생성 품질이 낮을 수 있음 | Few-shot 예시를 한국어로 풍부하게 제공 |
| 응답 길이 제어 | `num_predict` 파라미터로 토큰 수 제한 | 50 토큰으로 제한 (20자면 충분) |
| Temperature | 낮을수록 일관된 출력 | 0.3 설정 (안전 안내는 일관성이 중요) |
| 반복 페널티 | 동일 단어 반복 방지 | `repeat_penalty=1.1` |

---

## 3. 성능 최적화

### 3.1 gemma4-e4b 추론 성능 예상치

| 환경 | 첫 토큰 지연 | 토큰/초 | 20자 안내 생성 총 시간 |
|------|-------------|---------|----------------------|
| CPU Only (8코어) | ~1-3초 | 10-25 | ~2-5초 |
| GPU (RTX 3060 6GB) | ~100ms | 50-80 | ~300ms-800ms |
| GPU (RTX 4080 16GB) | ~50ms | 80-120 | ~150ms-400ms |

### 3.2 최적화 전략

```python
# 1. 모델 워밍업 (서버 시작 시)
async def warmup_llm():
    """첫 요청 지연 방지를 위한 워밍업"""
    llm = OllamaClientManager.get_client()
    messages = [HumanMessage(content="테스트")]
    await llm.ainvoke(messages)
    logger.info("LLM 워밍업 완료")

# 2. Keep-alive 설정 (Ollama)
# Ollama 서버 환경변수:
# OLLAMA_KEEP_ALIVE=30m  # 모델을 30분간 메모리에 유지

# 3. 배치 처리 (동시 요청 시)
# Ollama는 기본적으로 단일 요청 처리
# 여러 사용자 동시 접속 시 큐잉 필요
import asyncio

class LLMRequestQueue:
    def __init__(self, max_concurrent: int = 1):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def process(self, coro):
        async with self._semaphore:
            return await coro
```

### 3.3 L1 High 위험도 최적화

High 위험도는 사전 정의 문장을 사용하므로 LLM 호출이 없음:
- **지연 시간**: ~1ms (사실상 즉시)
- **비율**: 전체 요청의 약 20-30% (차량류가 빈번하게 탐지)
- **효과**: 전체 평균 응답 시간 대폭 단축

---

## 4. 테스트 시나리오

### 4.1 단위 테스트

```python
# tests/test_l1_classifier.py
import pytest
from server.orchestration.nodes.l1_risk_classifier import classify_risk, l1_risk_classifier_node

class TestRiskClassifier:
    def test_high_risk_car(self):
        assert classify_risk(["car"]) == "high"

    def test_high_risk_truck(self):
        assert classify_risk(["truck"]) == "high"

    def test_mid_risk_pothole(self):
        assert classify_risk(["pothole"]) == "mid"

    def test_mid_risk_bicycle(self):
        assert classify_risk(["bicycle"]) == "mid"

    def test_low_risk_person(self):
        assert classify_risk(["person"]) == "low"

    def test_low_risk_bench(self):
        assert classify_risk(["bench"]) == "low"

    def test_mixed_takes_highest(self):
        assert classify_risk(["pothole", "car"]) == "high"

    def test_empty_is_low(self):
        assert classify_risk([]) == "low"

    @pytest.mark.asyncio
    async def test_high_risk_returns_guidance(self):
        state = {"detected_classes": ["car"]}
        result = await l1_risk_classifier_node(state)
        assert result["risk_level"] == "high"
        assert "정지" in result["guidance_text"]
        assert result["verified"] is True
```

### 4.2 L3 검증 단위 테스트

```python
# tests/test_l3_validator.py
import pytest
from server.orchestration.nodes.l3_validator import validate_guidance

class TestGuidanceValidator:
    def test_valid_short_with_direction(self):
        is_valid, errors = validate_guidance("좌측으로 피하세요")
        assert is_valid is True
        assert errors == []

    def test_valid_stop(self):
        is_valid, errors = validate_guidance("전방 주의, 정지하세요")
        assert is_valid is True

    def test_too_long(self):
        is_valid, errors = validate_guidance("전방 약 3미터 지점에 포트홀이 있으니 좌측으로 조심해서 돌아가시기 바랍니다")
        assert is_valid is False
        assert any("길이 초과" in e for e in errors)

    def test_no_direction(self):
        is_valid, errors = validate_guidance("조심하세요")
        assert is_valid is False
        assert any("방향 키워드" in e for e in errors)

    def test_empty_string(self):
        is_valid, errors = validate_guidance("")
        assert is_valid is False
        assert any("빈 문장" in e for e in errors)

    def test_non_korean(self):
        is_valid, errors = validate_guidance("Turn left now")
        assert is_valid is False
        assert any("한국어" in e for e in errors)

    def test_exactly_20_chars(self):
        # 정확히 20자인 문장
        text = "전방 포트홀 주의 좌측으로 이동하세요"  # 길이 확인 필요
        is_valid, errors = validate_guidance(text)
        # 20자 이내이고 방향 키워드 있으면 통과
        if len(text) <= 20:
            assert is_valid is True
```

### 4.3 통합 테스트 (오케스트레이터)

```python
# tests/test_orchestrator.py
import pytest
from server.orchestration.orchestrator import run_orchestrator

class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_high_risk_immediate(self):
        result = await run_orchestrator(
            detected_classes=["car"],
            rag_context="차량 접근 시 즉시 정지",
        )
        assert result["risk_level"] == "high"
        assert result["verified"] is True
        assert "정지" in result["guidance_text"]
        assert result["total_latency_ms"] < 100  # L2/L3 건너뜀

    @pytest.mark.asyncio
    async def test_mid_risk_generates_guidance(self):
        result = await run_orchestrator(
            detected_classes=["pothole"],
            rag_context="포트홀 발견 시 좌측 또는 우측으로 우회",
            positions=["전방 중앙"],
        )
        assert result["guidance_text"] is not None
        assert len(result["guidance_text"]) > 0
        assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_result_has_direction(self):
        result = await run_orchestrator(
            detected_classes=["bicycle"],
            rag_context="자전거 접근 시 한쪽으로 비켜서기",
        )
        assert result["direction"] in ["좌", "우", "직진", "정지", ""]

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """LLM 반복 실패 시 정적 fallback 반환 확인"""
        # Ollama가 꺼져 있는 환경에서 테스트
        result = await run_orchestrator(
            detected_classes=["unknown"],
            rag_context="",
        )
        # 어떤 경우든 guidance_text는 반환되어야 함
        assert result["guidance_text"] is not None
        assert len(result["guidance_text"]) > 0
```

### 4.4 성능 테스트

```python
# tests/test_performance.py
import pytest
import time
from server.orchestration.orchestrator import run_orchestrator

class TestPerformance:
    @pytest.mark.asyncio
    async def test_high_risk_under_10ms(self):
        """High 위험도는 10ms 이내 응답"""
        start = time.perf_counter()
        result = await run_orchestrator(
            detected_classes=["car"],
            rag_context="차량 주의",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 10

    @pytest.mark.asyncio
    async def test_mid_risk_under_5s(self):
        """Mid 위험도는 5초 이내 응답 (CPU 환경 고려)"""
        start = time.perf_counter()
        result = await run_orchestrator(
            detected_classes=["pothole"],
            rag_context="포트홀 회피 방법",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 5000
```

---

## 5. Fallback 라우팅 정책 상세

### 5.1 Fallback 결정 흐름도

```
최근 100건 통계 집계
         │
         ├─ L3 실패율 > 10%? ──YES──▶ GPT-4o-mini 사용
         │                            │
         ├─ 평균 지연 > 3000ms? ─YES──▶ GPT-4o-mini 사용
         │                            │
         └─ 모두 정상 ──────────────▶ gemma4-e4b 유지
```

### 5.2 Fallback 복귀 조건

상용 API로 전환된 후에도 주기적으로 로컬 LLM을 시도하여 복귀:

```python
class FallbackRecoveryPolicy:
    """Fallback 상태에서 로컬 LLM 복귀 시도"""

    def __init__(self, probe_interval: int = 50):
        self._request_count = 0
        self._probe_interval = probe_interval  # 50건마다 로컬 시도

    def should_probe_local(self) -> bool:
        """Fallback 중 로컬 LLM 프로브 여부"""
        self._request_count += 1
        if self._request_count % self._probe_interval == 0:
            return True
        return False
```

### 5.3 비용 추적

```python
# GPT-4o-mini 비용 추적 (관리자 모니터링용)
class CostTracker:
    def __init__(self):
        self.total_tokens = 0
        self.total_cost_usd = 0.0

    def record(self, input_tokens: int, output_tokens: int):
        # GPT-4o-mini 가격 (2024 기준)
        INPUT_PRICE_PER_1K = 0.00015   # $0.15/1M tokens
        OUTPUT_PRICE_PER_1K = 0.0006   # $0.60/1M tokens

        self.total_tokens += input_tokens + output_tokens
        self.total_cost_usd += (
            input_tokens / 1000 * INPUT_PRICE_PER_1K +
            output_tokens / 1000 * OUTPUT_PRICE_PER_1K
        )

    def get_report(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_cost_krw": round(self.total_cost_usd * 1380, 2),  # 대략적 환율
        }
```

---

## 6. Ollama gemma4-e4b 설치 및 설정 상세

### 6.1 설치

```bash
# Ollama 설치 (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Ollama 설치 (Windows)
# https://ollama.com/download 에서 설치 파일 다운로드

# gemma4-e4b 모델 다운로드
ollama pull gemma4-e4b

# 모델 확인
ollama list
# NAME              ID          SIZE    MODIFIED
# gemma4-e4b        ...         2.5GB   ...
```

### 6.2 환경변수 설정

```bash
# Ollama 서버 설정
export OLLAMA_HOST=0.0.0.0:11434      # 바인딩 주소
export OLLAMA_KEEP_ALIVE=30m           # 모델 메모리 유지 시간
export OLLAMA_NUM_PARALLEL=1           # 동시 요청 수
export OLLAMA_MAX_LOADED_MODELS=2      # 최대 로드 모델 수 (gemma4-e4b + nomic-embed)

# GPU 설정 (NVIDIA)
export CUDA_VISIBLE_DEVICES=0          # 사용할 GPU
```

### 6.3 Ollama API 직접 테스트

```bash
# 모델 테스트
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4-e4b",
    "prompt": "시각장애인이 전방 포트홀을 피하는 10자 이내 안내를 작성해줘.",
    "stream": false,
    "options": {
      "temperature": 0.3,
      "num_predict": 50
    }
  }'
```

---

## 7. 관리자 모니터링 API 엔드포인트

```python
# app/api/monitoring.py
from fastapi import APIRouter
from server.orchestration.llm_metrics import LLMMetricsTracker

router = APIRouter(prefix="/api/monitoring", tags=["모니터링"])

@router.get("/llm-stats")
async def get_llm_stats():
    """LLM 오케스트레이터 통계"""
    metrics = LLMMetricsTracker.get_instance()
    return metrics.get_stats()

@router.get("/orchestrator-health")
async def get_orchestrator_health():
    """오케스트레이터 헬스 체크"""
    from server.orchestration.ollama_client import OllamaClientManager
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=3.0)
            models = [m["name"] for m in resp.json().get("models", [])]
            gemma_loaded = "gemma4-e4b" in models
    except Exception:
        gemma_loaded = False

    metrics = LLMMetricsTracker.get_instance()
    stats = metrics.get_stats()

    return {
        "gemma4_available": gemma_loaded,
        "using_fallback": stats["using_fallback"],
        "failure_rate": stats["failure_rate"],
        "avg_latency_ms": stats["avg_latency_ms"],
        "total_processed": stats["total_records"],
    }
```

---

## 8. 트러블슈팅 가이드

| 문제 | 원인 | 해결책 |
|------|------|--------|
| gemma4-e4b 첫 응답 매우 느림 (>10초) | 모델 콜드 스타트 | 서버 시작 시 워밍업 쿼리 실행 |
| 한국어 출력 대신 영어 출력 | gemma4-e4b 한국어 이해 부족 | 시스템 프롬프트에 "반드시 한국어로" 강조, few-shot 추가 |
| 20자 초과 빈번 발생 | 모델이 길이 제약 무시 | `num_predict` 토큰 수 제한, 프롬프트 강화 |
| 방향 키워드 누락 빈번 | 모델이 방향 포함 규칙 무시 | 프롬프트에 예시 추가, L3 재시도로 보완 |
| Fallback이 자주 발생 | gemma4-e4b 품질 부족 | GPT-4o-mini를 기본으로 전환 검토 |
| GPU 메모리 부족 (OOM) | gemma4-e4b + nomic-embed-text 동시 로드 | `OLLAMA_MAX_LOADED_MODELS=1`로 제한, 또는 nomic-embed-text 크기 확인 |
| Ollama 서버 크래시 | 메모리 부족 | 시스템 RAM/VRAM 확인, swap 확대 |
| LangGraph 무한 루프 | L3L2 재시도 조건 오류 | `max_retry_count`로 최대 1회 재시도 제한 확인 |
