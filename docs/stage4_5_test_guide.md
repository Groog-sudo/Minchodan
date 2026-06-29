# Minchodan RAG 백엔드(4·5단계) 단위 테스트 실행 가이드북

> **작성일**: 2026-06-26
> **버전**: v1.1.0
> **설계 기준**: `docs/minchodan_design_note.md` 4·5단계
> **코딩 패턴 기준**: `docs/course_codebase_guide.md`

본 문서는 Minchodan RAG 백엔드(4·5단계) 모듈의 정상 작동 여부를 개발자가 직접 검증하고, 변경한 소스코드가 기존 시스템에 미치는 영향을 확인하기 위한 단위 테스트(pytest) 및 개별 모듈별 즉시 실행형 스모크 테스트 수행 방법을 단계별로 상세히 안내합니다.

---

## 1. [1단계] 터미널 환경 설정 및 가상환경 활성화

테스트를 수행하기 전 반드시 로컬 가상환경을 활성화하고 필요한 의존성 패키지를 확인해야 합니다. 모든 명령어는 프로젝트 루트 디렉토리(`d:\2025_langchain_ydg\TeamProject\Minchodan`) 기준의 터미널(PowerShell 또는 cmd)에서 실행합니다.

1. **프로젝트 루트로 이동**: 터미널을 열고 프로젝트 루트 폴더인 `Minchodan`으로 이동합니다.
2. **Windows PowerShell 가상환경 활성화**:
   ```powershell
   venv\Scripts\activate
   ```
   *만약 `스크립트 실행 권한` 에러가 발생하는 경우, 관리자 권한으로 PowerShell을 열어 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`를 실행한 후 다시 시도하십시오.*
3. **cmd 가상환경 활성화**:
   ```cmd
   venv\Scripts\activate.bat
   ```
4. **의존성 패키지 동기화**: `requirements.txt`에 기록된 라이브러리 버전을 가상환경에 완전하게 동기화합니다.
   ```bash
   pip install -r requirements.txt
   ```

---

## 2. [2단계] pytest 단위 테스트 전체 구동하기

`pytest` 테스트 프레임워크를 사용하여 RAG 모듈들과 데이터 파이프라인의 연계 테스트를 수행합니다.

### 2.1 테스트 실행 명령어 목록

개발자가 수행하고자 하는 목적에 따라 알맞은 명령을 선택해 터미널에 입력합니다.

| 대상 범위 | 실행 명령어 | 설명 및 기대 결과 |
| :--- | :--- | :--- |
| **전체 테스트 일괄 실행** | `venv\Scripts\python -m pytest tests/ -v` | 프로젝트 내 모든 테스트 파일들을 수집하여 구동합니다. 초록색 `PASSED` 사인이 출력되어야 합니다. |
| **RAG 모듈만 선별 테스트** | `venv\Scripts\python -m pytest tests/test_db_builder.py tests/test_dedup_phash.py tests/test_e2e_pipeline.py tests/test_embedding_engine_factory.py tests/test_fallback.py tests/test_frame_extractor.py tests/test_gemini_captioner.py tests/test_retriever.py tests/test_vector_db_factory.py -v` | 3단계 YOLO 탐지 모듈을 제외한 4·5단계 핵심 기능만 집중 검증합니다. |
| **특정 파일만 테스트** | `venv\Scripts\python -m pytest tests/test_retriever.py -v` | 수정 중인 `retriever.py` 파일의 정합성만 빠르게 확인합니다. |

---

## 3. [3단계] 개별 모듈 즉시 실행 스모크 테스트

각 소스코드 파일 최하단에 마련된 `if __name__ == "__main__":` 블록을 활용하여, pytest 프레임워크를 거치지 않고 개별 스크립트 형태로 단위 기능과 동작 결과를 콘솔 로그로 직접 확인할 수 있습니다.

| 대상 모듈 | 실행 명령어 | 검증 기능 내용 및 예상 콘솔 출력 예시 |
| :--- | :--- | :--- |
| **4단계 프레임 추출** | `venv\Scripts\python -m server.rag.build.frame_extractor` | 임시 가짜 동영상 파일을 생성한 뒤 지정한 fps 간격으로 이미지가 정상 분리 저장되는지 검증합니다.<br/>*예상 출력: `가짜 비디오 생성 완료`, `프레임 추출 완료`* |
| **4단계 pHash 중복제거** | `venv\Scripts\python -m server.rag.build.dedup_phash` | 픽셀 차이에 따른 이미지 해시 비교를 통해 동일 이미지 차단 및 고유 이미지 잔존 여부를 검증합니다.<br/>*예상 출력: `중복 필터링 테스트 성공`* |
| **4단계 VLM 캡셔너** | `venv\Scripts\python -m server.rag.build.gemini_captioner` | API Key 미설정 및 API 네트워크 오류 시 예외 전파 가드레일 정상 작동 여부를 검증합니다.<br/>*예상 출력: `API Key 누락 예외 정상 검증 완료`* |
| **4단계 DB 전체 빌더** | `venv\Scripts\python -m server.rag.build.db_builder` | 프레임 분할부터 중복제거, Mock 캡셔닝을 거쳐 ChromaDB(코사인 유사도 공간) 생성 완료까지의 전 흐름을 검증합니다.<br/>*예상 출력: `빌드 성공 여부 확인: True`* |
| **5단계 Retriever 검색** | `venv\Scripts\python -m server.rag.retriever` | 인덱싱된 임시 ChromaDB를 기반으로 사물 라벨과 1:1 매칭되는 행동 수칙 조회 결과 확인 및 라벨 불일치 가드를 검증합니다.<br/>*예상 출력: `RAG 매칭 검색 결과: 킥보드를 조심히 피해서 돌아가세요.`* |
| **5단계 Fallback 안전망** | `venv\Scripts\python -m server.rag.fallback` | RAG 미적중 또는 예외 발생 시 사물 라벨 딕셔너리 안전 접근을 거쳐 즉시 하드코딩 룰 기반 안전 가이드가 출력되는지 검증합니다.<br/>*예상 출력: `[kickboard] 가이드: 전방에 방치된 전동 킥보드가 있습니다. ...`* |

---

## 4. [4단계] 외부 서비스 및 환경 변수 연동 테스트

코드가 외부 API나 로컬 데몬 서비스에 의존할 때의 수동 검증 요령입니다.

### 4.1 로컬 Ollama 연동 유무에 따른 테스트 동작 기준
* **Ollama nomic-embed-text 탑재 환경**:
  로컬 호스트(http://localhost:11434)에 Ollama 서비스가 켜져 있고 nomic-embed-text 모델이 설치되어 있으면 실시간 API 호출 검증이 통과됩니다.
* **Ollama 미탑재 / CI 빌드 환경**:
  Ollama 포트 연결이 실패하면 `test_embedding_engine_factory.py` 테스트 코드가 자연스럽게 해당 테스트 항목을 **Skip(스킵)** 처리하므로, 로컬 데몬이 꺼져 있더라도 전체 테스트 파이프라인이 중단되거나 빨간 줄(실패)을 반환하지 않습니다.
* **결정론적 Mocking 지원**:
  `MockEmbeddingEngine`이 쿼리 키워드 분석을 거쳐 동일한 범주에 결정론적 해시 가중치 벡터를 할당하므로, 로컬 Ollama 모델 없이도 유사도 검색 로직이 정상 작동합니다.

### 4.2 구글 제미나이 VLM 실서버 통합 테스트 진행 요령
제미나이 캡셔너 모듈의 실서버 VLM 이미지 분석 및 한글 캡션 생성 기능을 테스트하려면 다음과 같이 수동으로 진행합니다.

1. 프로젝트 루트의 `.env` 파일에 유효한 구글 API 키를 임시 기입합니다.
   ```env
   GOOGLE_API_KEY=AIzaSy... (실제 본인의 Gemini API 키 입력)
   ```
2. API 요금 및 쿼터 보존을 위해 기본 스킵 설정되어 있는 제미나이 통합 테스트 케이스를 명시적으로 지목하여 강제 실행합니다.
   ```powershell
   venv\Scripts\python -m pytest tests/test_gemini_captioner.py -k test_generate_caption_real_integration -v
   ```
3. 테스트 완료 후에는 커밋 방지를 위해 `.env` 파일의 API 키를 제거하거나 원상 복구합니다.
