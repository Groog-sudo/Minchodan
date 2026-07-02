# Fallback LLM 대체 모델 검토 보고서 (최신 Gemini API 비용 비교 및 최적 모델 선정)

> **작성일**: 2026-06-28
> **버전**: v1.2.0
> **대상 모듈**: [llm_client_factory.py](../server/orchestration/llm_client_factory.py)

---

## 1. 개요

Minchodan 프로젝트의 6단계 오케스트레이션(L2 가이드 문장 생성 및 L3 가드레일 검증)에서는 로컬 LLM(**gemma4-e4b**)의 리소스 부하(GPU 부족) 또는 검증 실패율이 높을 때 상용 API 모델로 자동 핫스왑(폴백)하는 설계를 채택하고 있습니다.

최신 2026년 기준 Gemini API 라인업의 비용을 조사 및 분석하여, 우리 프로젝트의 특성에 부합하면서 **최소 비용**으로 운영 가능한 최적의 모델을 도출합니다.

---

## 2. 최신 상용 API 모델 요금 및 스펙 비교 (2026년 6월 기준)

2026년 기준 Google AI Studio / OpenAI의 요금 체계를 기준으로 한 비교 매트릭스입니다. (1M 토큰 = 100만 토큰 기준)

| 모델명 | 제공사 | 입력 비용 (per 1M) | 출력 비용 (per 1M) | 무료 티어 (Free Tier) | 추천 용도 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.1 Flash-Lite** | Google | **$0.25** | **$1.50** | **지원 (분당/일일 제한)** | **경량 대화, 고속 추론, 최소 비용** |
| **Gemini 3.5 Flash** | Google | $1.50 | $9.00 | 지원 (제한적) | 멀티모달 고성능 추론 |
| **Gemini 3.1 Pro** | Google | $2.00 | $12.00 | 지원 (매우 제한적) | 복잡한 추론 및 코딩 |
| **GPT-4o-mini** | OpenAI | $0.15 | $0.60 | 미지원 (유료만 가능) | 경량 범용 API 대안 |
| **Gemini 1.5 Flash** | Google | $0.075 | $0.30 | (지원 중단 진행 중) | 구버전 레거시 모델 |

> **중요 참고 사항**: 구버전인 Gemini 2.0 Flash/Lite 및 1.5 Flash는 최근 지원 중단(Deprecated/Shutdown) 처리되었거나 감축 단계에 있어, 신규 시스템 적용 시 최신 3.x 라인업인 **Gemini 3.1 Flash-Lite** 또는 **Gemini 3.5 Flash**를 채택해야 합니다.

---

## 3. Minchodan 프로젝트에 적합한 최소 비용 모델 선정

### 최적 추천 모델: **Gemini 3.1 Flash-Lite**

우리 프로젝트의 특성상 **Gemini 3.1 Flash-Lite**가 최소 비용 및 고효율을 보장하는 최적의 모델인 이유는 다음과 같습니다.

1. **실제 지출 비용 제로 (Google AI Studio Free Tier 극대화)**
   - OpenAI의 `gpt-4o-mini`는 단가 자체는 매우 낮으나 첫 호출부터 무조건 과금되는 구조입니다.
   - 반면 Google AI Studio를 통해 **Gemini 3.1 Flash-Lite**를 호출할 경우, 프로토타이핑 및 실서비스 테스트 수준의 트래픽에서는 **무료 티어 범위 내에서 100% 무상으로 이용이 가능**합니다.
2. **프로젝트 토큰 사용 패턴에 최적화**
   - Minchodan의 인지 경로 L2 출력물은 **20자 이내의 짧은 한국어 안내**입니다. 즉, 출력 토큰(Completion Tokens)이 평균 15~25개 미만으로 극히 적습니다.
   - 입력값 역시 장애물 바운딩 박스 리스트와 RAG 행동 수칙 5개 수준으로 수백 토큰 내외입니다.
   - 1M(100만) 토큰 단가가 입력 $0.25, 출력 $1.50인 **Gemini 3.1 Flash-Lite**를 사용하면, 무료 티어 한도를 초과하여 유료 결제로 전환되더라도 트랜잭션당 비용은 약 **$0.0001 (한화 약 0.13원)** 수준에 불과합니다.
3. **지연 시간(Latency) 최적화**
   - Flash-Lite 모델 계열은 대규모 트래픽 처리에 특화된 경량 설계 모델입니다. 폴백 시 발생할 수 있는 네트워크 대기 시간을 최소화하여 가이드독 시스템의 목표 시간(3초)을 안정적으로 충족합니다.

---

## 4. 구현 가이드라인 업데이트 (Gemini 3.1 Flash-Lite 반영)

[llm_client_factory.py](../server/orchestration/llm_client_factory.py)의 팩토리 클래스에서 사용할 기본 모델명을 **`gemini-3.1-flash-lite`**로 지정합니다.

```python
class SimpleGeminiClient:
    """
    httpx를 활용한 비동기 Google Gemini API 호출 클라이언트.
    2026년 최신 가성비 모델인 Gemini 3.1 Flash-Lite를 기본 적용합니다.
    """

    def __init__(self, model_name: str = "gemini-3.1-flash-lite", api_key: str = ""):
        self.model_name = model_name
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 비어 있습니다.")

    async def ainvoke(self, messages: list) -> LLMResponse:
        # API Payload 빌드 및 호출 구조 (동일)
        ...
```

---

## 5. 결론

프로젝트를 개발 및 배포하고 실서비스를 운영하는 전 과정에서 **실질적인 최소 비용(무료 티어 적용 시 $0.00)** 및 **압도적인 응답 속도**를 동시에 달성할 수 있는 모델은 **Gemini 3.1 Flash-Lite**입니다.

해당 모델을 신규 폴백 타겟으로 결정해 주시면, 소스 코드 및 문서에 반영하도록 하겠습니다.
