# [Antigravity / Gemini 3.5 Flash 에이전트 작업 지시서 — 최종 병합본]
## Minchodan 프로젝트 — 4·5단계 RAG 스켈레톤 + 단위테스트 구축

당신은 Antigravity IDE에서 동작하는 Gemini 3.5 Flash 코딩 에이전트입니다.
아래 지시사항을 **순서대로, 빠짐없이** 따라 작업을 수행하세요. 모르는 부분이나 모호한 결정 지점은 임의로 판단하지 말고, 코드 내 `# TODO(human-decision):` 주석으로 표시한 뒤 작업을 계속 진행하세요.

---

## 0. 프로젝트 컨텍스트 (요약)

- **프로젝트명**: Minchodan — 시각장애인 보행 보조 AI 플랫폼
- **전체 파이프라인**: 1단계(WS 연결) → 2단계(프레임 전송) → 3단계(YOLO 탐지/분할) → **4단계(위험 대처 수칙 DB 구축)** → **5단계(실시간 RAG 검색)** → 6단계(LangGraph 가이드 문장 생성) → 7단계(TTS)
- **이번 작업 범위는 4단계와 5단계뿐**입니다. 3·6·7단계는 손대지 마세요.
- **비협상 제약**: 5단계 실시간 검색은 최종적으로 50ms 이내여야 합니다. 이를 위해 1.3절의 임베딩 분리 원칙을 반드시 지키세요.

---

## 1. 작업 목표 (Definition of Done)

### 1.1 이번 단계의 목표 — "스켈레톤 + 단위테스트"까지만

내부 핵심 AI 로직(실제 학습, 파라미터 최적화, 프롬프트 세부 튜닝)은 비워두고, **모듈 간 데이터 계약(Data Contract)과 인터페이스가 정상 작동하는지**를 수석 개발자 수준으로 꼼꼼하게 검증할 수 있는 스켈레톤을 만드세요. 목표는 다음과 같습니다:

1. 정해진 파일 구조와 함수 시그니처를 정확히 구현
2. 각 함수는 "흐름이 끝까지 도는" 최소 동작 수준으로 구현
3. **더미 데이터로 4→5단계 전체 흐름이 에러 없이 끝까지 도는 pytest 단위테스트** 작성 및 통과 확인
4. **모든 파일 하단에 `if __name__ == "__main__":` 블록을 두어, 실제 함수를 호출하는 즉시 실행형 스모크 테스트도 함께 포함**(코드를 바로 실행해서 흐름을 눈으로 볼 수 있도록)
5. 외부 API(Gemini) 호출은 기본적으로 mock 처리하여 단위테스트가 비용/쿼터를 소모하지 않게 할 것

### 1.2 선반영해야 할 기존 문제 목록

이전 두 차례 교차검증(Claude + Gemini)에서 발견된 문제입니다. 이번 스켈레톤에 전부 반영하세요.

| # | 문제 | 조치 |
|---|---|---|
| 1 | `ChatGoogleGenAI`, `GoogleGenAIEmbeddings`는 실제 패키지에 없는 클래스명 | `langchain_google_genai`의 정확한 클래스명 `ChatGoogleGenerativeAI` 사용 (임베딩은 1.3절 참고 — Gemini 임베딩 클래스는 5단계에 쓰지 않음) |
| 2 | 5단계 쿼리 임베딩까지 클라우드를 쓰면 50ms 제약 위반 + 4/5단계 벡터공간 불일치 | 1.3절 "임베딩 분리 원칙" 그대로 적용 |
| 3 | 3단계 탐지 클래스명과 4단계 메타데이터 라벨이 다르게 적힐 위험 (예: `broken_braille` vs `braille_damaged`) | 2.1절 "라벨 SSOT" 모듈 도입 — 단순히 "더미 맵으로 확인 가능하게"가 아니라 **구조적으로 불일치가 발생할 수 없게** 만들 것 |
| 4 | 메타데이터 스키마에 `risk_level` 필드 누락 | `{scene_type, risk_level, objects, guidance_template}` 4개 필드 모두 포함 |
| 5 | `requirements.txt`에 `langchain`, `langchain-community`, `langchain-ollama` 누락 | 추가 |
| 6 | 필수 가드(try/except)가 스켈레톤에 자리조차 없음 | 빈 구현이라도 가드 구조는 반드시 존재 (2.4절) |
| 7 | `load_dotenv()`가 일부 파일에만 호출되어, 파일을 독립적으로 단위 실행하면 `.env`가 안 읽힐 수 있음 | **모든 파일**의 최상단 또는 `if __name__ == "__main__":` 블록 안에서 `load_dotenv()` 호출 |
| 8 | `VectorDBFactory`가 DB 엔진 추상화(Chroma↔Qdrant)와 임베딩 엔진 추상화(Gemini↔Ollama)를 뒤섞으면 책임이 불분명해짐 | 2.5절처럼 **두 추상화를 분리**할 것 |

### 1.3 임베딩 분리 원칙 (★ 핵심 아키텍처 결정 — 임의 변경 절대 금지)

- **4단계 VLM 캡셔닝**: `gemini-2.5-flash-lite`를 기본값으로 사용 (한국 IP 환경에서 과거 `gemini-2.0-flash` 쿼터 제한 경험이 있어, 보수적으로 lite를 1차 선택. 캡션 품질이 부족하면 `gemini-2.5-flash`로 업그레이드 가능하다는 주석만 남길 것). 오프라인 배치라 지연 시간 무관.
- **5단계 쿼리 임베딩 + 4단계 인덱싱 임베딩**: **클라우드 API 사용 절대 금지.** 아래 패키지를 정확히 사용할 것:
  ```python
  # pip install langchain-ollama
  from langchain_ollama import OllamaEmbeddings
  embeddings = OllamaEmbeddings(model="nomic-embed-text")
  ```
  - `langchain_community.embeddings.OllamaEmbeddings`는 구버전이므로 사용하지 말 것.
  - 이유: (a) 50ms 실시간 제약, (b) 4단계 인덱싱과 5단계 검색이 반드시 동일 임베딩 모델을 써야 벡터공간이 일치하므로, 둘 다 로컬로 통일.
- 임베딩 모델 호출부는 `EmbeddingEngineFactory`로 추상화하여 향후 다른 로컬 모델로 교체 가능하게 만들 것. **단, 교체 시 기존 벡터 DB 인덱스는 호환되지 않으므로 반드시 4단계 재실행(전체 재인덱싱)이 필요하다는 점을 클래스 docstring에 명시**할 것. 단순 호출부 교체로는 해결되지 않는다는 점을 분명히 남길 것.
- 5단계 코드 상단에 다음 주석을 정확히 남길 것:
  ```python
  # TODO(latency): 로컬 임베딩 적용 후에도 실제 50ms 실측은 아직 진행되지 않았음.
  # 이번 스켈레톤 단계에서는 성능 튜닝/캐싱을 시도하지 않음.
  ```

---

## 2. 세부 구현 지시

### 2.1 라벨 SSOT(Single Source of Truth) 모듈 신설

- 경로: `server/rag/shared/labels.py`
- 3단계 탐지 클래스명을 Enum 또는 상수로 정의 (`kickboard`, `bollard`, `braille_damaged`, `stairs`, `crosswalk`, `manhole`, `grating` 등 — 설계서 3단계의 분리 클래스 목록 기준)
- 4단계 메타데이터 생성 코드, 5단계 쿼리 생성 코드, `fallback.py`의 `FALLBACK_RULES` 딕셔너리 키 **모두가 이 모듈을 import해서 사용**하도록 강제. 클래스명 문자열 하드코딩 금지.
- 작업 후 "3단계 클래스 전체 목록과 1:1로 비교했는지"를 완료보고에 포함할 것.

### 2.2 파일 구조 (그대로 생성 — 원본 설계서의 파일 분리 유지)

```
server/rag/
├── shared/
│   └── labels.py                  # 라벨 SSOT
├── build/                          # 4단계
│   ├── frame_extractor.py          # 프레임 추출 (db_builder가 호출)
│   ├── dedup_phash.py              # pHash 중복 제거 (db_builder가 호출)
│   ├── gemini_captioner.py         # VLM 캡셔닝
│   └── db_builder.py               # 위 3개를 오케스트레이션 + ChromaDB 저장
├── vector_db_factory.py            # 5단계 — DB 엔진 추상화 (2.5절)
├── embedding_engine_factory.py     # 5단계 — 임베딩 엔진 추상화 (1.3절, 신규)
├── retriever.py                    # 5단계 — 검색
└── fallback.py                     # 5단계 — 룰 기반 안전망

tests/
├── test_frame_extractor.py
├── test_dedup_phash.py
├── test_gemini_captioner.py        # Gemini API mock
├── test_db_builder.py
├── test_vector_db_factory.py
├── test_embedding_engine_factory.py
├── test_retriever.py
├── test_fallback.py
└── test_e2e_pipeline.py            # 4→5단계 전체 흐름 더미데이터 통과 확인
```

> `frame_extractor.py`와 `dedup_phash.py`를 `db_builder.py`에 합치지 말 것 — 각각 독립적으로 단위테스트가 가능해야 합니다.

### 2.3 메타데이터 스키마

```python
metadata = {
    "scene_type": ...,            # shared/labels.py 기준
    "risk_level": ...,            # "high" | "mid" | "low"
    "objects": ...,               # shared/labels.py 기준 리스트
    "guidance_template": ...,     # 인간 검수 안전 수칙 텍스트
}
```

### 2.4 필수 가드 및 독립 실행 조건

- `frame_extractor.py`: 비디오 디코딩 실패 가드
- `gemini_captioner.py`: API 네트워크/인증 오류 (`GOOGLE_API_KEY` 미설정 시 명확한 에러 메시지)
- `db_builder.py`: 디스크 쓰기 권한/경로 오류(`PermissionError`)
- `vector_db_factory.py`: DB 손상/경로 부재(`FileNotFoundError`)
- `retriever.py`: 검색 실패/타임아웃 시 빈 문자열 반환 후 `fallback.py`로 이어지도록(중단 금지)
- **모든 파일**: 최상단에 `from dotenv import load_dotenv; load_dotenv()` 호출 + 하단 `if __name__ == "__main__":` 블록에서 실제 함수를 더미 데이터로 호출하는 스모크 테스트 포함

### 2.5 두 개의 독립된 팩토리 (책임 분리)

- `vector_db_factory.py`: **DB 엔진**만 담당 (`chroma` ↔ `qdrant` 핫스왑, 설계서 5단계 요구사항). 임베딩 모델은 외부에서 주입받는 구조로 만들 것(직접 생성하지 말 것).
- `embedding_engine_factory.py`: **임베딩 엔진**만 담당 (현재는 Ollama 고정, 추후 다른 로컬 모델 교체 가능). `vector_db_factory.py`는 이 팩토리가 만든 임베딩 객체를 받아서 쓰는 구조로 설계.

---

## 3. 더미 데이터 규칙 (★ 통일된 태그 규격)

사용자가 실제로 채워야 하는 모든 데이터는 **즉시 실행 가능한 하드코딩 더미 값**으로 대체하고, 예외 없이 아래 형식의 주석을 남길 것:

```python
# [✅ DUMMY DATA] 설명: <무엇을, 어떤 자료형/포맷으로 넣어야 하는지> / 주의: <라벨 명칭 일치 등 특별히 주의할 점>
```

최소한 다음 항목에 적용:

| 위치 | 더미 데이터 내용 | 주석에 명시할 내용 |
|---|---|---|
| `tests/`, `__main__` 블록용 | OpenCV로 생성한 1~2초 합성 비디오 | "실제 위험 상황 비디오/이미지 100건 이상(킥보드, 볼라드, 파손 점자블록 등). 자료형: mp4/jpg 경로 문자열" |
| `gemini_captioner.py` 테스트 mock | 고정된 가짜 한글 캡션 문자열 3~5개 | "실제 Gemini Vision API 응답(한글 상황 묘사 1~2문장)" |
| `db_builder.py` 입력 `captions_data` | guidance_template에 임시 안전 수칙 텍스트 | "전문가 검수를 거친 실제 안전 대처 수칙 텍스트. **objects/scene_type 값은 반드시 shared/labels.py의 상수와 일치해야 함**" |
| `retriever.py` 테스트 입력 | 더미 `detect_info` dict | "실제 3단계 YOLO 추론 결과(`class_name`은 shared/labels.py 기준이어야 함, 임의 문자열 금지)" |
| `fallback.py`의 `FALLBACK_RULES` | MVP 3~5개 클래스만 채움 | "shared/labels.py 전체 클래스 확장 시 라벨별 안전수칙 추가 필요. 키 이름은 shared/labels.py에서 import해서 사용, 직접 타이핑 금지" |
| `.env.sample` | `GOOGLE_API_KEY=YOUR_KEY_HERE` | "실제 Gemini API 키 — 절대 커밋 금지" |

---

## 4. 테스트 작성 가이드 (pytest + 즉시 실행 스모크 테스트 병행)

- `pytest` 사용. **Gemini API 호출은 기본 mock 처리**(`unittest.mock.patch`). 실제 키가 있을 때만 동작하는 통합 테스트는 `@pytest.mark.integration`으로 분리, 기본 실행에서 skip.
- ChromaDB는 `tmp_path` fixture로 임시 디렉토리에 실제 생성하여 진짜 인덱싱/검색 흐름을 검증.
- 로컬 임베딩(Ollama)은 실제 호출 가능. 단, CI/테스트 환경에 Ollama가 없을 경우 graceful skip 처리.
- `test_e2e_pipeline.py`: 더미 비디오 → 프레임 추출 → dedup → (mock)캡셔닝 → `db_builder`로 더미 ChromaDB 생성 → `retriever`로 더미 `detect_info` 검색 → 결과가 빈 문자열이 아님을 assert. 추가로 무관한 쿼리를 줘서 `fallback.py`가 정상 개입하는지도 검증.
- 위 pytest와 별개로, **각 파일의 `if __name__ == "__main__":` 블록은 더미 데이터를 실제로 호출해서 콘솔에 결과를 출력**하도록 작성(사람이 바로 실행해서 흐름을 눈으로 확인하는 용도).

---

## 5. 코드 스타일

- 함수 단위로 "왜 이렇게 짰는지" 설명하는 한국어 주석 포함(발표 시 설명 가능한 수준)
- 기존 함수 시그니처·타입힌트 최대한 유지
- 파일 상단 UTF-8 인코딩 선언부(`sys.stdout.reconfigure`) + `load_dotenv()` 유지

---

## 6. 하지 말 것 (Out of scope)

- 실제 모델 학습/파인튜닝 로직, 캡셔닝/검색 프롬프트 세부 최적화
- 50ms 성능 튜닝 또는 캐싱으로 기준을 "맞춘 것처럼" 보이게 하는 행위
- 실제 API 키를 코드/커밋에 포함
- 3·6·7단계 코드 수정
- `frame_extractor.py`/`dedup_phash.py`를 다른 파일에 합치는 구조 변경

---

## 7. 완료 보고 형식

1. 생성/수정된 파일 전체 목록
2. `pytest` 실행 결과 (통과/스킵 항목 구분) + `__main__` 스모크 테스트 실행 로그
3. `# TODO(human-decision):` 주석을 남긴 위치와 이유
4. `shared/labels.py`의 클래스 목록을 3단계 설계서 전체 클래스와 1:1로 비교했는지 여부
5. 더미 데이터 중 라벨 일치 위험이 있는 항목 별도 표시
6. 다음 단계로 넘어가기 전에 사람이 결정해야 할 사항(로컬 임베딩 모델 최종 확정, VLM 캡셔닝 prompt 확정, 50ms 실측 방법 등)
