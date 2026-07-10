# 민초단 최적화 작업 체크리스트

## 1단계: Ollama 중지 + Gemini API 전환
- [x] Ollama 컨테이너 중지
- [x] `.env` LLM_PROVIDER=gemini 변경 및 GEMINI_MODEL=gemini-2.5-flash-lite 추가
- [x] `server/orchestration/llm_client_factory.py` GeminiClient 추가 및 팩토리 연동
- [x] `requirements.txt` langchain-google-genai 추가 (직접 httpx 호출하여 라이브러리 설치 불필요하게 최적화)
- [x] `docker/docker-compose.yml` Ollama 의존성 제거 및 서비스 비활성화

## 2단계: FastAPI 컨테이너 재기동 및 메모리 해방
- [x] WSL2 VM 셧다운 (`wsl --shutdown`)을 통한 6.26GB Ollama 메모리 완전 해방
- [x] `docker compose up -d fastapi redis` (Ollama 제외하고 2컨테이너만 구동)
- [x] 로그 확인 (YOLO 모델 best_20260705.pt 및 best.pt 로드 성공 검증)

## 3단계: Metro 번들러 안정화
- [x] `app.json` scheme: "minchodan" 추가
- [x] `package.json` start:android 스크립트 추가
- [x] 기존 Metro 포트 및 프로세스 충돌 해제

## 4단계: 검증 (사용자 대기)
- [x] Docker 메모리 사용량 확인 (6.6 GB -> 456 MiB로 93% 감소 완료)
- [ ] 스마트폰 앱 연결 + BBox 표시 확인
- [ ] TTS 다양한 문구 출력 확인
- [x] dg.md 업데이트
