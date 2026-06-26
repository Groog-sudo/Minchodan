# Changelog - dg (대근)

> 이 파일은 **dg(대근)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-26 | 4·5단계 | RAG 기본 틀 구현 및 모듈 리팩토링 완료

- **커밋**: `feat: 4·5단계 RAG 파이프라인 구현 및 모듈 리팩토링 완료`
- **변경 내용**:
  - 4단계: 비디오 프레임 1fps 분할 추출, pHash 기반 이미지 중복 제거, Gemini VLM 한글 캡셔닝, ChromaDB 오프라인 적재 전체 DB 빌더 파이프라인 구현
  - 5단계: vector_db_factory, embedding_engine_factory, retriever, fallback 모듈을 server/rag/ 하위 패키지로 구현 및 결합도 제거
  - 5단계: RAG 검색 실패 또는 예외 발생 시 시스템 중단을 차단하고 즉시 룰 기반 안전 가이드를 제공하는 Fallback 안전망 설계
  - 테스트: 4·5단계 기능 단위 검증 및 E2E 시나리오 pytest 통과 확인 (41 passed, 1 skipped)
  - 리팩토링: vector_db_factory, embedding_engine_factory, retriever, fallback 모듈을 server/에서 server/rag/ 패키지 하위로 이동하고 내부 임포트 경로 전수 동기화
  - 문서화: 입문용 폴더/파일 가이드, 단계별 단위 테스트 실행 가이드, 실데이터 교체 가이드 마크다운 문서 3건 작성 완료
- **관련 파일**: `server/rag/build/frame_extractor.py`, `server/rag/build/dedup_phash.py`, `server/rag/build/gemini_captioner.py`, `server/rag/build/db_builder.py`, `server/rag/shared/labels.py`, `server/rag/embedding_engine_factory.py`, `server/rag/vector_db_factory.py`, `server/rag/retriever.py`, `server/rag/fallback.py`, `tests/test_db_builder.py`, `tests/test_e2e_pipeline.py`, `tests/test_embedding_engine_factory.py`, `tests/test_fallback.py`, `tests/test_retriever.py`, `tests/test_vector_db_factory.py`, `docs/stage4_5_directory_guide.md`, `docs/stage4_5_test_guide.md`, `docs/stage4_5_data_replacement_guide.md`
- **검증 결과**: pytest 단위 테스트 41건 통과 (Ollama 미연동 1건 자동 스킵) 및 개별 Retriever/Fallback 스모크 테스트 실행 확인
