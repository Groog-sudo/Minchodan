# Minchodan RAG 실데이터 교체 및 반영 가이드북

> **작성일**: 2026-06-26
> **버전**: v1.0.0
> **설계 기준**: `docs/minchodan_design_note.md` 4·5단계
> **코딩 패턴 기준**: `docs/course_codebase_guide.md`

본 문서는 Minchodan RAG 백엔드(4·5단계) 시스템의 설계 검증을 완료한 후, 테스트용 더미(Mock) 데이터 및 시뮬레이션 환경을 실제 현업 운영용 데이터와 인공지능 엔진으로 교체하여 연동을 완료하기 위한 기술 지침서입니다.

---

## 1. 더미 데이터 교체 대상 및 필요성 요약

기본 틀에서는 외부 요금 부과를 방지하고 환경 의존성을 없애 빠른 테스트를 진행하기 위해 아래 표와 같이 임시 더미(Mock) 구성요소를 사용하고 있습니다. 실제 가이드독 운영 모드로 서비스를 개시하려면 아래 실데이터로의 교체가 반드시 필요합니다.

| 분류 | 더미(Mock) 구성요소 | 실서버 운영(Production) 구성요소 | 교체 필요성 및 주요 이유 |
| :--- | :--- | :--- | :--- |
| **비디오 입력** | 테스트용 검은 화면의 100x100 해상도 mp4 더미 파일 | 실제 전방 보행 환경 및 위험 요소가 포함된 보행 영상 (mp4) | 실제 도심 인도 환경의 시각 장애인 위험 장애물(킥보드, 파손 점자블록 등) 정보가 묘사된 프레임을 추출하기 위해 실제 주행 영상을 주입해야 합니다. |
| **VLM 이미지 분석** | 단순 단어 매핑 형태의 하드코딩 텍스트를 돌려주는 Mock 캡셔너 | 구글 Gemini 2.5 Flash API 연동을 통한 실제 VLM 이미지 분석 및 한글 묘사문 추출 | 더미 캡셔너는 다양한 실제 보행로 상의 불규칙한 장애물 배치 상태를 설명할 수 없습니다. 실제 VLM을 통해 "점자블록 오른쪽으로 킥보드가 쓰러져 막고 있습니다" 같은 정밀한 상세 지침을 생성해야 합니다. |
| **의미 임베딩** | 키워드가 포함되었는지 여부로 난수 벡터를 할당하는 Mock 임베딩 엔진 | Ollama 기반 nomic-embed-text (로컬 구동) 또는 상용 OpenAI의 text-embedding-3-small | 난수 기반의 가짜 벡터는 자연어 텍스트 문장 간의 세밀한 유사도 비교가 원천적으로 불가능합니다. 실제 고차원 의미 공간의 임베딩 모델을 통해야만 문맥적인 검색이 정상 작동합니다. |
| **저장 디렉토리** | 테스트 완료 시 자동 소멸하는 `tmp_path` 임시 폴더 | 로컬 디스크 상의 영구 저장용 벡터 저장소 폴더 (`data/chroma_db`) | 테스트 종료 후 삭제되는 임시 저장 방식 대신, 빌드된 지식 정보를 물리 디스크에 영구히 저장 및 유지하여 런타임 추론 서버가 지속적으로 읽을 수 있게 해야 합니다. |

---

## 2. 세부 교체 및 연동 절차

### 2.1 4단계: 실서버 비디오 주입 및 프레임 추출
1. **영상 준비**: 보행 환경에서 위험 요소가 골고루 나타나는 3분 이내의 안내 비디오 파일을 준비합니다.
2. **경로 배치**: 준비한 영상을 `data/raw/guidance_video.mp4` 경로로 저장합니다.
3. **코드 적용**: `db_builder.py` 및 프레임 추출기 구동 인자를 해당 비디오 경로로 지정해 구동합니다.
   * `frame_extractor.py`가 가동되면서 1초에 한 장씩 이미지를 추출해 `data/frames/`로 저장하며, `dedup_phash.py`를 통해 보행자가 멈춰 서 있는 구간 등에서 유입되는 중복 프레임 이미지가 자동으로 걸러집니다.

### 2.2 4단계: 구글 Gemini VLM API 연동 (Mock 해제)
1. **API Key 획득**: 구글 AI 스튜디오에서 유효한 제미나이 API Key를 발급받습니다.
2. **환경변수 기입**: 프로젝트 루트의 `.env` 파일에 다음과 같이 추가합니다.
   ```env
   GOOGLE_API_KEY=AIzaSy...(본인의 실제 키값)
   ```
3. **Mock 가드 해제**: 데이터베이스 빌드를 수행할 때 `force_mock_captioner` 매개변수를 `False`로 지정하여 Mock 캡셔너 폴백 작동을 멈추고 실제 VLM API가 동작하게 만듭니다.
   ```python
   # db_builder.py 호출 예시
   db = build_database(
       video_path="data/raw/guidance_video.mp4",
       output_dir="data/frames",
       db_persist_dir="data/chroma_db",
       embeddings=real_embeddings,
       force_mock_captioner=False  # 실제 VLM API 호출 활성화
   )
   ```

### 2.3 4·5단계: 실서버 의미 임베딩 엔진 활성화 (Mock 해제)
1. **Ollama 구동**: 로컬 GPU 서버에 Ollama 인프라가 켜져 있는지 확인합니다.
2. **임베딩 모델 다운로드**: Ollama 서버 터미널에서 아래 명령을 실행해 임베딩 모델을 미리 내려받습니다.
   ```bash
   ollama pull nomic-embed-text
   ```
3. **팩토리 파라미터 변경**: `embedding_engine_factory.py`에서 임베딩을 요청할 때 provider를 `"ollama"`로, model_name을 `"nomic-embed-text"`로 변경하여 호출합니다.
   ```python
   # 변경 전
   embeddings = EmbeddingEngineFactory.get_embeddings(provider="mock")
   
   # 변경 후 (Ollama 실서버 임베딩 사용)
   embeddings = EmbeddingEngineFactory.get_embeddings(
       provider="ollama", 
       model_name="nomic-embed-text"
   )
   ```

### 2.4 데이터베이스 저장 경로 변경
1. **환경변수 설정**: `.env` 파일에 ChromaDB 영구 보존 디렉토리를 바인딩합니다.
   ```env
   CHROMA_PATH=data/chroma_db
   CHROMA_COLLECTION=bidding_kb
   ```
2. **DB 팩토리 로드**: `vector_db_factory.py` 및 `retriever.py`에서 DB 디렉토리를 로드할 때 상기 환경변수 경로를 활용하도록 코드를 작성해 런타임 추론이 가능하게 만듭니다.

---

## 3. 실데이터 교체 완료 후 검증
데이터 교체가 마무리되면, `pytest`를 활용한 단위 테스트 대신 다음 두 단계를 실행하여 실서버 성능과 정합성을 검증합니다.

1. **데이터베이스 빌드 파이프라인 구동**:
   ```bash
   venv\Scripts\python -m server.rag.build.db_builder
   ```
   *출력 결과: `data/chroma_db` 디렉토리가 정상 생성되고, `collection.count()`가 실제 중복제거된 고유 프레임 개수와 동일하게 축적되었는지 확인합니다.*
2. **실시간 검색 및 Fallback 응답 실측 검증**:
   ```bash
   venv\Scripts\python -m server.rag.retriever
   ```
   *출력 결과: 실제 구축된 ChromaDB에서 코사인 유사도 연산을 거쳐 < 50ms 이내로 행동 수칙 문자열이 반환되는지 응답 시간을 측정합니다.*
