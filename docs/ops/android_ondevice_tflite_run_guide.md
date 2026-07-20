I will view the `.env` file that you currently have open to verify the exact variable names, comments, and how `GOOGLE_API_KEY` is configured.

Viewed .env:1-68

학원 PC와 같은 공용 환경에서 **기존 Docker 컨테이너의 완전 삭제 방법**과 파일에 보이지 않는 **`GOOGLE_API_KEY` 추가 방법**을 포함하여, 입문자가 최종적으로 안드로이드폰과 PC를 정상 연동하여 테스트할 수 있도록 전체 실행 가이드를 상세히 개정하였습니다.

---

## 1단계: 기존 Docker 컨테이너 정리 및 완전 삭제 (학원 PC 필수)

학원 PC에서 이전에 생성되었거나 실행 중인 다른 실습용 컨테이너들이 포트(`8000`, `6379`, `11434` 등)를 점유하고 있으면 새 컨테이너가 기동되지 않습니다. 깨끗이 정리하고 시작해야 합니다.

1. **현재 PC의 모든 컨테이너 목록 확인**:
   - 터미널(PowerShell 또는 CMD)을 열고 아래 명령을 입력하여 모든 컨테이너(정지된 것 포함)를 조회합니다.
     ```bash
     docker ps -a
     ```

2. **기존 컨테이너 강제 종료 및 완전 삭제**:
   - 특정 컨테이너를 강제 삭제하려면 다음 명령어를 실행합니다.
     ```bash
     docker rm -f <컨테이너_이름_또는_ID>
     ```
   - **[권장]** 학원 PC에 있는 가동 중이거나 멈춰 있는 모든 컨테이너를 한 번에 일괄 강제 중지하고 삭제하려면 아래 명령을 입력합니다. (이 작업을 수행하면 포트 충돌 문제가 근본적으로 해결됩니다.)
     ```bash
     docker rm -f $(docker ps -aq)
     ```

---

## 2단계: 환경 변수 파일 생성 및 `GOOGLE_API_KEY` 추가

1. **환경 변수 파일 복사**:
   - 프로젝트 루트 디렉토리(`d:\2025_langchain_ydg\TeamProject\Minchodan`) 터미널에서 아래 명령을 실행합니다.
     ```powershell
     Copy-Item .env.example .env
     ```

2. **`.env` 파일에 `GOOGLE_API_KEY` 직접 추가 및 설정**:
   - 텍스트 에디터로 생성된 `.env` 파일을 엽니다.
   - 템플릿 파일에는 `GOOGLE_API_KEY` 항목이 기본적으로 누락되어 있으므로, **파일의 가장 맨 아랫줄에 직접 텍스트를 타이핑하여 추가**해 줍니다.
     ```ini
     # --- 구글 Gemini API 키 (RAG 캡셔닝 빌드 필수) ---
     GOOGLE_API_KEY=AIzaSy... (여기에 본인의 실제 구글 API 키 입력)
     ```
   - 더불어, Docker 컨테이너 간의 네트워크 이름 인식 통신을 위해 아래 주소 값들도 동일하게 변경하고 저장합니다.
     ```ini
     REDIS_URL=redis://redis:6379
     OLLAMA_BASE_URL=http://ollama:11434
     ```

---

## 3단계: Docker 기반 백엔드 인프라 실행

1. **Docker Desktop 구동**:
   - PC에 깔린 **Docker Desktop** 프로그램을 실행합니다.

2. **시작 스크립트 실행**:
   - 프로젝트 루트 터미널에서 배치 파일을 구동시킵니다.
     ```powershell
     docker\windows_docker_start.bat
     ```
   - 최종 완료 후 웹 브라우저에서 `http://localhost:8000/docs` 주소로 접속해 FastAPI API 문서(Swagger)가 뜨는지 확인합니다.

3. **Ollama 모델 다운로드**:
   - PC 호스트의 Ollama에 LLM과 임베딩 모델을 준비합니다. 이미지 캡셔닝은 Gemini 경로이므로 `llava`는 필요하지 않습니다.
     ```bash
     ollama pull gemma4:e4b
     ollama pull nomic-embed-text
     ```

4. **RAG 의미 검색 데이터베이스(ChromaDB) 구축**:
   - 위에서 등록한 `GOOGLE_API_KEY`를 활용해 이미지를 캡셔닝하고 벡터 DB를 빌드합니다.
     ```bash
     python scripts/build_safety_db.py
     ```

---

## 4단계: Tailscale 연결 및 모바일 설정 연동

1. **Tailscale 연결 확인**:
   - 서버 PC와 Android 단말을 같은 tailnet에 연결합니다.
     ```bash
     tailscale status
     tailscale ip -4
     ```

2. **모바일 환경변수 설정**:
   - `client/.env`에 Tailscale Serve 인증서와 일치하는 서버 MagicDNS 이름을 입력합니다.
     ```ini
     EXPO_PUBLIC_NETWORK_MODE=tailscale
     EXPO_PUBLIC_TAILSCALE_HOST=[SERVER_MAGICDNS_NAME].ts.net
     EXPO_PUBLIC_SERVER_PORT=443
     EXPO_PUBLIC_WS_SCHEME=wss
     ```

---

## 5단계: 안드로이드폰 USB 디버깅 활성화 및 PC 연결

1. **스마트폰 세팅**:
   - 스마트폰의 **설정 > 휴대전화 정보 > 소프트웨어 정보**에서 **빌드 번호** 항목을 연속으로 7번 터치하여 개발자 옵션을 활성화합니다.
   - **설정 > 개발자 옵션**으로 돌아와 **USB 디버깅** 스위치를 켭니다.
2. **연결 상태 확인**:
   - 폰을 USB 선으로 PC에 연결하고 화면에 뜨는 디버깅 승인 허용을 터치합니다.
   - PC 터미널에서 다음 명령을 수행해 기기가 정상 인식되었는지 확인합니다.
     ```bash
     adb devices
     ```
     *(기기 ID 문자열이 출력되어야 합니다.)*

---

## 6단계: 안드로이드폰에 앱 설치 및 연동 구동 검증

1. **안드로이드 앱 설치**:
   - `client` 폴더(`d:\2025_langchain_ydg\TeamProject\Minchodan\client`) 경로에서 터미널을 열고 아래 빌드 명령어를 실행합니다.
     ```bash
     npm run android
     ```
   - 컴파일 빌드가 완료되어 폰에 앱이 켜지면 **카메라 권한**을 승인해 줍니다.

2. **실시간 통신 및 햅틱 오디오 테스트**:
   - 폰 카메라로 전방을 비추었을 때 PC 서버의 FastAPI 컨테이너 로그(`docker logs -f minchodan-fastapi`)에 카메라 프레임 수신 이력이 실시간으로 찍히는지 모니터링합니다.
   - 장애물이 카메라 시야의 근접 거리에 진입하면 스마트폰에서 비프 경고음 재생 및 햅틱 진동이 의도대로 긴박하게 고속 핑퐁으로 연동하여 작동하는지 확인합니다.
