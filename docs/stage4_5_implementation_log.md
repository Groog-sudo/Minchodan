# Minchodan 4·5단계 RAG 백엔드 구현 및 수정 행동 이력 로그

> **작성일**: 2026-06-26
> **버전**: v1.0.0
> **설계 기준**: `docs/minchodan_design_note.md` 4·5단계
> **코딩 패턴 기준**: `docs/course_codebase_guide.md`

본 문서는 Minchodan 프로젝트 4단계 및 5단계 RAG 백엔드 시스템 구축 과정에서의 설계, 파일 생성, 수정 및 리팩토링 조치 등 모든 개발 행동 이력을 기록한 종합 로그 파일입니다.

---

## 1. 단계별 행동 이력 요약

| 단계 | 행동 항목 | 세부 수행 내용 | 결과 산출물 |
| --- | --- | --- | --- |
| **1단계** | **기술 설계서 작성** | 4·5단계 기본 설계, 임베딩 분리 원칙, 라벨 SSOT 정합 규칙 수립 | [stage4_5_rag_design.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/stage4_5_rag_design.md) |
| **2단계** | **환경 설정 및 공통 라벨 SSOT** | 의존성 패키지 명시, 환경 변수 템플릿 작성 및 라벨 불일치 방지 상수화 | [requirements.txt](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/requirements.txt)<br/>[labels.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/shared/labels.py) |
| **3단계** | **4단계 (DB 구축) 모듈 구현** | 비디오 프레임 추출, pHash 중복 필터링, Gemini VLM 연동, ChromaDB 적재 빌더 구현 | [frame_extractor.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/build/frame_extractor.py)<br/>[dedup_phash.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/build/dedup_phash.py)<br/>[gemini_captioner.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/build/gemini_captioner.py)<br/>[db_builder.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/build/db_builder.py) |
| **4단계** | **5단계 (Retriever) 모듈 구현** | DB/임베딩 추상화 팩토리 패턴 구현, 검색 가드 및 룰 기반 안전망 구축 | [vector_db_factory.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/vector_db_factory.py)<br/>[embedding_engine_factory.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/embedding_engine_factory.py)<br/>[retriever.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/retriever.py)<br/>[fallback.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/rag/fallback.py) |
| **5단계** | **단위 및 E2E 테스트 구현** | pytest 기반 개별 단위 기능 테스트 및 데이터 파이프라인 E2E 시나리오 구성 | `tests/` 하위 test_*.py 9개 파일 |
| **6단계** | **테스트 환경 파일 정리** | Windows 파일 잠금 등으로 남은 임시 DB 폴더 정리 및 이그노어 패턴 차단 | [gitignore](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/.gitignore) 수정 |
| **7단계** | **지침서 기반 종합 리팩토링** | 17.5절 공통 임포트 헤더 포맷 적용 및 13.3절 ChromaDB 코사인 유사도 연동 적용 | 18개 핵심 코드 및 테스트 파일 일괄 수정 |

---

## 2. 파일별 생성 및 수정 이력 상세

### 2.1 공통 및 4단계 모듈

#### **labels.py**
* **행동**: 신규 생성 및 헤더 리팩토링
* **설명**: 3단계 YOLO 탐지 클래스와의 1:1 라벨 비교 정합 완료. `kickboard`, `bollard`, `braille_damaged` 등 상수화.
* **수정 내역**: `course_codebase_guide.md` 17.5절 표준 헤더(`sys.stdout.reconfigure` 가드 패턴) 일치화 완료.

#### **frame_extractor.py**
* **행동**: 신규 생성 및 헤더 리팩토링
* **설명**: 1fps 간격 이미지 추출 구현. 프레임 버퍼가 `None`인 경우에 대비한 방어적 가드 적용.
* **수정 내역**: `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.

#### **dedup_phash.py**
* **행동**: 신규 생성 및 헤더 리팩토링
* **설명**: PIL Image open 예외 가드레일 설치. 임계 해밍 거리 이내 중복 프레임 제거 로직 구현.
* **수정 내역**: `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.

#### **gemini_captioner.py**
* **행동**: 신규 생성 및 헤더 리팩토링
* **설명**: API Key 미설정 및 API 호출 네트워크 실패 가드레일 설치. `gemini-2.5-flash-lite` 모델 기본 지정.
* **수정 내역**: `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.

#### **db_builder.py**
* **행동**: 신규 생성 및 리팩토링
* **설명**: 프레임 추출 -> 중복제거 -> Mock/VLM 캡션 생성 -> ChromaDB 적재의 파이프라인 흐름 오케스트레이션.
* **수정 내역**: 
  * `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.
  * `course_codebase_guide.md` 13.3절에 명시된 **코사인 유사도 방식** (`collection_metadata={"hnsw:space": "cosine"}`)을 `Chroma.from_documents` 호출 시점에 강제 설정하도록 추가 리팩토링 완료.

---

### 2.2 5단계 및 Retriever 모듈

#### **server/rag/vector_db_factory.py**
* **행동**: 신규 생성 및 리팩토링
* **설명**: 임베딩 엔진 결합을 완전히 제거하고 외부에서 임베딩을 주입받아 ChromaDB 인스턴스를 동적 생성하는 팩토리 구현.
* **수정 내역**:
  * `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.
  * ChromaDB 로딩 생성자 호출부에 `collection_metadata={"hnsw:space": "cosine"}`를 추가하여 인덱스 탐색 공간의 유사도 척도 일치화 완료.

#### **server/rag/embedding_engine_factory.py**
* **행동**: 신규 생성 및 헤더 리팩토링
* **설명**: Ollama nomic-embed-text 로컬 모델 임베딩 호출 구조 구현. 쿼리 키워드 기반 시드를 적용한 결정론적 `MockEmbeddingEngine` 클래스 추가 작성.
* **수정 내역**: `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.

#### **server/rag/retriever.py**
* **행동**: 신규 생성 및 리팩토링
* **설명**: YOLO detect_info 정보 분석을 거친 의미 검색 수행. RAG 미적중 시 또는 라벨 불일치 발생 시 중단을 차단하고 빈 문자열을 반환하는 안전 가드 설치.
* **수정 내역**:
  * `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.
  * 내부 스모크 테스트 실행용 ChromaDB 인스턴스 빌드 함수에 `collection_metadata={"hnsw:space": "cosine"}` 속성 추가 완료.

#### **server/rag/fallback.py**
* **행동**: 신규 생성 및 헤더 리팩토링
* **설명**: SSOT 라벨에 정의된 전체 사물별 대처 지침 수칙을 딕셔너리로 작성 및 방어적 dict 접근 가드 적용.
* **수정 내역**: `course_codebase_guide.md` 17.5절 표준 헤더 일치화 완료.

---

### 2.3 단위 테스트 모듈 (`tests/`)

#### **pytest 단위 테스트 9개 파일 일괄 수정**
* **행동**: 신규 생성 및 헤더 리팩토링
* **수정 내용**: `test_db_builder.py`, `test_dedup_phash.py`, `test_e2e_pipeline.py`, `test_embedding_engine_factory.py`, `test_fallback.py`, `test_frame_extractor.py`, `test_gemini_captioner.py`, `test_retriever.py`, `test_vector_db_factory.py` 전체의 첫 줄 헤더를 `course_codebase_guide.md` 17.5절의 표준 형태로 일치화 완료.
* **수정 내용**: `test_retriever.py` 내 Chroma DB 생성 지점에 `collection_metadata={"hnsw:space": "cosine"}` 추가 적용 완료.
