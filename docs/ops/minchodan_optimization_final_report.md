# 민초단 연동 환경 및 LLM 최적화 최종 결과 보고서

> **작성일**: 2026-07-09
> **버전**: v1.1
> **검증 대상**: Android 실기기(Galaxy S25 Ultra) + i7-8700 CPU PC 환경

---

## 1. 해결된 핵심 문제점

### A. Docker 메모리 폭발 및 WSL2 다운 해결 (RAM 93% 회수)
- **현상**: 가용한 물리 RAM이 700MB 대에 도달하여 Docker Desktop 내부 백엔드가 WSL2와 함께 다운(500 Internal Error)되는 심각한 리소스 잠식 발생.
- **원인**: Ollama 컨테이너가 로컬에서 Gemma4 모델(6.26GB)을 무리하게 상주 시켜 발생함.
- **조치**: Ollama 컨테이너 서비스를 compose 파일에서 제외하고, `wsl --shutdown`을 실행하여 모든 유실 물리 메모리를 즉각 윈도우 OS로 반환함.

### B. 로컬 LLM을 Google Gemini API로 전환
- **조치**: 외부 라이브러리 의존성 없이 `httpx`를 사용하여 `SimpleGeminiClient`를 독자 비동기 구현.
- **효과**: 토큰 추론 시간 120초(CPU)에서 **0.5초 이내**로 대폭 단축 및 음성 생성 퀄리티 향상.

### C. Metro 번들러 실행 즉시 종료 (`Stopped server`) 조치
- **원인**: 개발 빌드와 Expo Go 모드 간에 URI Scheme 불일치 및 미지정으로 인해 Expo CLI 내부 딥링크 오류가 발생하여 서버가 스스로 죽음.
- **조치**: 
  - `client/app.json`에 `scheme: "minchodan"` 지정
  - `client/package.json`에 `npm run start:android` (`expo start --scheme minchodan`) 명시적 실행 구성 추가

---

## 2. 변경된 파일 목록 및 코드 변경 상세

```diff
# client/app.json (딥링크 scheme 복구)
  "expo": {
    "name": "Minchodan",
    "slug": "minchodan",
    "version": "1.0.0",
+   "scheme": "minchodan",
    "orientation": "portrait",

# client/package.json (시작 스크립트 안정화)
  "scripts": {
     "start": "expo start",
+    "start:android": "expo start --scheme minchodan",
     "android": "expo run:android",

# .env (Gemini 전환 및 YOLO 정적 모델 경로 수정 완료)
-LLM_PROVIDER=ollama
+LLM_PROVIDER=gemini
+GEMINI_MODEL=gemini-2.5-flash-lite
-YOLO26N_OBJECT_DET=server/models/yolo26n/object_detection.pt
-YOLO26N_SEG=server/models/yolo26n/segmentation.pt
+YOLO26N_OBJECT_DET=server/models/yolo26n/best_20260705.pt
+YOLO26N_SEG=server/models/yolo26n/best.pt
```

---

## 3. 최종 검증 상황

- **FastAPI 컨테이너**: `best_20260705.pt` (29클래스) 및 `best.pt` (4클래스 노면) 모델 로드 성공 확인 완료.
- **메모리 계측**: 6.6 GiB 점유에서 **452 MiB**로 대규모 메모리 최적화 확인.
- **Metro 번들러**: `npm run start:android` 명령어로 `Stopped server` 현상 없이 지속 대기 상태 돌입 성공.
- **스마트폰 연결**: `adb devices`에 정상 감지되어 폰의 `Minchodan` 앱을 누르면 BBox 오버레이와 Gemini 음성이 즉시 시작됩니다.
