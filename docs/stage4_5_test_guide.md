# Minchodan 4·5단계 RAG 단위 테스트 실행 가이드

> **작성일**: 2026-06-26
> **버전**: v1.0.0
> **설계 기준**: `docs/minchodan_design_note.md` 4·5단계
> **코딩 패턴 기준**: `docs/course_codebase_guide.md`

본 문서는 Minchodan 프로젝트 4단계 및 5단계 RAG 백엔드 모듈의 기능 검증을 위한 단위 테스트(pytest) 및 개별 모듈별 즉시 실행형 스모크 테스트 수행 방법을 설명합니다.

---

## 1. 사전 준비 작업

테스트를 수행하기 전 반드시 로컬 가상환경을 활성화하고 필요한 의존성 패키지를 확인해야 합니다. 모든 명령어는 프로젝트 루트 디렉토리(`d:\2025_langchain_ydg\TeamProject\Minchodan`) 기준의 터미널(PowerShell 또는 cmd)에서 실행합니다.

### 1.1 가상환경 활성화
```powershell
# Windows PowerShell 기준 가상환경 활성화
venv\Scripts\activate
```

### 1.2 의존성 패키지 동기화
```powershell
# requirements.txt 기반 최신 패키지 설치 및 동기화
pip install -r requirements.txt
```

---

## 2. pytest 단위 테스트 실행 방법

`pytest` 라이브러리를 통해 작성된 전체 시나리오 단위 테스트 및 데이터 파이프라인의 연계 테스트를 수행합니다.

### 2.1 테스트 실행 명령 목록

| 대상 범위 | 실행 명령어 | 설명 |
| --- | --- | --- |
| **전체 테스트** | `venv\Scripts\python -m pytest tests/ -v` | 프로젝트 내 모든 테스트 파일들을 상세 로그 모드로 구동 |
| **RAG 모듈만 테스트** | `venv\Scripts\python -m pytest tests/test_db_builder.py tests/test_dedup_phash.py tests/test_e2e_pipeline.py tests/test_embedding_engine_factory.py tests/test_fallback.py tests/test_frame_extractor.py tests/test_gemini_captioner.py tests/test_retriever.py tests/test_vector_db_factory.py -v` | 3단계 YOLO 탐지 테스트를 제외한 RAG 4·5단계 핵심 테스트만 선별 실행 |
| **특정 파일만 테스트** | `venv\Scripts\python -m pytest tests/test_retriever.py -v` | 지정한 특정 테스트 모듈 파일 1개만 실행 |

---

## 3. 개별 모듈 즉시 실행 스모크 테스트

각 소스코드 파일 최하단에 마련된 `if __name__ == "__main__":` 블록을 활용하여, pytest 프레임워크를 거치지 않고 개별 스크립트 형태로 단위 기능과 동작 결과를 콘솔 로그로 직접 확인할 수 있습니다.

| 대상 모듈 | 실행 명령어 | 검증 기능 내용 |
| --- | --- | --- |
| **4단계 프레임 추출** | `venv\Scripts\python -m server.rag.build.frame_extractor` | 임시 가짜 동영상 파일을 생성한 뒤 지정한 fps 간격으로 이미지가 정상 분리 저장되는지 검증 |
| **4단계 pHash 중복제거** | `venv\Scripts\python -m server.rag.build.dedup_phash` | 픽셀 차이에 따른 이미지 해시 비교를 통해 동일 이미지 차단 및 고유 이미지 잔존 여부 검증 |
| **4단계 VLM 캡셔너** | `venv\Scripts\python -m server.rag.build.gemini_captioner` | API Key 미설정 및 API 네트워크 오류 시 예외 전파 가드레일 정상 작동 여부 검증 |
| **4단계 DB 전체 빌더** | `venv\Scripts\python -m server.rag.build.db_builder` | 프레임 분할부터 중복제거, Mock 캡셔닝을 거쳐 ChromaDB(코사인 유사도 공간) 생성 완료까지의 전 흐름 검증 |
| **5단계 Retriever 검색** | `venv\Scripts\python -m server.rag.retriever` | 인덱싱된 임시 ChromaDB를 기반으로 사물 라벨과 1:1 매칭되는 행동 수칙 조회 결과 확인 및 라벨 불일치 가드 검증 |
| **5단계 Fallback 안전망** | `venv\Scripts\python -m server.rag.fallback` | RAG 미적중 또는 예외 발생 시 사물 라벨 딕셔너리 안전 접근을 거쳐 즉시 하드코딩 룰 기반 안전 가이드가 출력되는지 검증 |

---

## 4. 로컬 Ollama 연동 유무에 따른 테스트 동작 기준

* **Ollama nomic-embed-text 탑재 환경**:
  로컬 호스트(http://localhost:11434)에 Ollama 서비스가 켜져 있고 nomic-embed-text 모델이 설치되어 있으면 실시간 API 호출 검증이 통과됩니다.
* **Ollama 미탑재 / CI 빌드 환경**:
  Ollama 포트 연결이 실패하면 `test_embedding_engine_factory.py` 테스트 코드가 자연스럽게 해당 테스트 항목을 **Skip(스킵)** 처리하므로, 로컬 데몬이 꺼져 있더라도 전체 테스트 파이프라인이 중단되거나 빨간 줄(실패)을 반환하지 않습니다.
* **결정론적 Mocking 지원**:
  `MockEmbeddingEngine`이 쿼리 키워드 분석을 거쳐 동일한 범주에 결정론적 해시 가중치 벡터를 할당하므로, 로컬 Ollama 모델 없이도 유사도 검색 로직이 정상 작동합니다.

---

## 5. 구글 제미나이 VLM 실서버 통합 테스트 진행 요령

제미나이 캡셔너 모듈의 실서버 VLM 이미지 분석 및 한글 캡션 생성 기능을 테스트하려면 다음과 같이 수동으로 진행합니다.

1. 프로젝트 루트의 `.env` 파일에 유효한 구글 API 키를 작성합니다.
   ```
   GOOGLE_API_KEY=AIzaSy... (실제 본인의 Gemini API 키 입력)
   ```
2. API 요금 및 쿼터 보존을 위해 기본 스킵 설정되어 있는 제미나이 통합 테스트 케이스를 명시적으로 지목하여 강제 실행합니다.
   ```powershell
   venv\Scripts\python -m pytest tests/test_gemini_captioner.py -k test_generate_caption_real_integration -v
   ```
3. 테스트 완료 후에는 커밋 방지를 위해 `.env` 파일의 API 키를 제거하거나 원상 복구합니다.
