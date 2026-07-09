# 안드로이드 스마트폰 연동 실행 가이드

> **작성일**: 2026-07-09
> **버전**: v2.0.0
> **대상**: Minchodan 프로젝트 Android 실기기 테스트 담당자 (입문자 기준)
> **목적**: iOS 스마트폰과 PC 연동 구동 방식과 동일하게 Android 스마트폰과 PC를 연동하여 Minchodan 프로그램을 실행하기

---

## 1. PC 서버 실행 방법 (전체 단계)

### 1단계: 기존 Docker 컨테이너 완전 삭제 (포트 충돌 예방)

학원 PC와 같이 공용 환경에서는 이전 사용자의 컨테이너가 포트를 점유하고 있을 수 있습니다.

```bash
# 현재 컨테이너 목록 확인
docker ps -a

# 모든 컨테이너 강제 삭제
docker rm -f $(docker ps -aq)
```

---

### 2단계: 환경 변수 파일 .env 설정

```powershell
# 템플릿 복사
Copy-Item .env.example .env
```

`.env` 파일을 열어 **맨 아랫줄에** 다음 항목들을 추가합니다.

```ini
# --- Docker 내부 통신 주소 재설정 ---
REDIS_URL=redis://redis:6379
OLLAMA_BASE_URL=http://ollama:11434

# --- 구글 Gemini API 키 (RAG 데이터베이스 구축용) ---
GOOGLE_API_KEY=AIzaSy... (본인의 실제 구글 API 키 입력)

# --- ngrok 터널 보안 인증 토큰 ---
NGROK_AUTHTOKEN=여기에_본인의_ngrok_토큰_입력

# --- 데이터베이스 (DB 미구성 환경 임시 우회용) ---
DATABASE_URL=sqlite+aiosqlite:///./data/minchodan_temp.db
```

> **주의**: `DATABASE_URL` 항목은 MariaDB 서버가 없는 환경에서 FastAPI 서버가 크래시 없이 기동되도록 하기 위한 임시 설정입니다.

---

### 3단계: Docker 백엔드 서비스 기동 및 AI 모델 설치

1. **Docker Desktop 실행**

2. **시작 스크립트 실행 (PowerShell 권장)**:
   ```powershell
   docker\windows_docker_start.bat
   ```
   - 하드웨어 선택 프롬프트가 뜨면 **`2`** (CPU Only Mode) 입력 후 엔터
   - 완료 후 브라우저에서 `http://localhost:8000/docs` 접속하여 Swagger 화면 확인

3. **Ollama AI 모델 컨테이너 내부 다운로드**:
   ```bash
   docker exec -it minchodan-ollama ollama pull gemma4:e4b
   docker exec -it minchodan-ollama ollama pull llava
   docker exec -it minchodan-ollama ollama pull nomic-embed-text
   ```

4. **RAG 데이터베이스(ChromaDB) 빌드** (venv 활성화 상태에서):
   ```bash
   python scripts/build_safety_db.py
   ```
   - 103개 문서가 ChromaDB에 인덱싱되어 `data/chroma_db/`에 저장됩니다.

---

### 4단계: ngrok 보안 터널 기동 및 모바일 주소 연동

공용 PC 터미널 이력에 토큰이 평문으로 남지 않도록 .env에서 동적으로 로드합니다.

**PowerShell 환경**:
```powershell
$env:NGROK_AUTHTOKEN = (Get-Content .env | Select-String "NGROK_AUTHTOKEN=" | Out-String).Split("=")[1].Trim()
npx ngrok http 8000 --authtoken $env:NGROK_AUTHTOKEN
```

**Git Bash 환경**:
```bash
export NGROK_AUTHTOKEN=$(grep NGROK_AUTHTOKEN .env | cut -d '=' -f2)
npx ngrok http 8000 --authtoken $NGROK_AUTHTOKEN
```

- ngrok이 로컬에 설치되지 않아도 `npx`가 자동 다운로드 후 실행합니다.
- 최초 실행 시 `Ok to proceed? (y)` 물음이 뜨면 `y` 입력

기동 화면에서 Forwarding 주소(`https://xxxx.ngrok-free.app`)를 복사한 뒤, [client/src/config/index.ts](../../client/src/config/index.ts) 파일 9번째 줄의 `WS_URL`을 수정합니다.

```typescript
// 정적 따옴표 문자열로 작성 (백틱 템플릿 문법 사용 금지 - Android 번들링 오류 유발)
export const WS_URL = "wss://xxxx.ngrok-free.app/ws/detect";
```

> **중요**: 백틱(`` ` ``) 템플릿 문법과 변수 조합(`\`ws://${LAN_IP}...\``)은 Android Metro 번들러에서 500 에러를 유발합니다. 반드시 일반 따옴표(`"`)로 작성합니다.

---

### 5단계: 안드로이드 기기 USB 디버깅 활성화 및 PC 연결

1. 스마트폰 **설정 > 휴대전화 정보 > 소프트웨어 정보**에서 **빌드 번호**를 7번 연속 터치하여 개발자 모드 활성화
2. **설정 > 개발자 옵션**에서 **USB 디버깅** 스위치를 켬
3. USB 데이터 케이블로 PC와 연결 후 폰 화면의 **디버깅 허용** 팝업 승인
4. 연결 상태 확인:
   ```bash
   adb devices
   # 기기 ID 옆에 "device"가 표시되어야 정상
   ```

---

### 6단계: Metro 포트 터널 설정 및 앱 빌드

```bash
# USB를 통한 Metro 번들러 포트 터널 설정 (필수)
adb reverse tcp:8081 tcp:8081

# WebSocket 서버 포트 터널 설정
adb reverse tcp:8000 tcp:8000
```

```bash
# client 폴더에서 앱 빌드 및 설치
cd client
npm run android
```

- 빌드 완료 후 폰에 앱이 자동 설치됩니다.
- 폰 화면에 **카메라 권한 팝업**이 뜨면 반드시 **허용**을 터치합니다.
- 앱 첫 실행 시 번들 로딩에 30~60초 소요됩니다. 검은 화면 유지 시 대기합니다.

---

## 2. 오류 발생 시 대처 방법

### 오류 A: `bash: docker\windows_docker_start.bat: command not found`

**원인**: Git Bash 환경에서 윈도우 배치 파일의 백슬래시(`\`) 문법을 인식하지 못함

**해결**: PowerShell 터미널을 열어 동일 명령 실행

```powershell
docker\windows_docker_start.bat
```

또는 Docker Compose를 직접 실행:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

---

### 오류 B: `minchodan-fastapi` 컨테이너가 계속 재시작됨 (Restarting)

**원인**: `.env` 파일에 MariaDB 환경 변수(`DB_HOST`, `DB_PORT` 등)가 누락되어 서버 기동 시 `RuntimeError` 발생

**해결**: `.env` 파일 맨 아랫줄에 아래 한 줄 추가 후 컨테이너 재기동

```ini
DATABASE_URL=sqlite+aiosqlite:///./data/minchodan_temp.db
```

```bash
docker restart minchodan-fastapi
docker ps  # STATUS가 "Up"인지 확인
```

---

### 오류 C: `bash: scripts/build_chroma.sh: No such file or directory`

**원인**: RAG 빌드 스크립트 파일명이 변경됨 (`.sh` 쉘 스크립트 -> `.py` 파이썬 스크립트)

**해결**: 올바른 명령어로 교체

```bash
# 잘못된 명령어
bash scripts/build_chroma.sh

# 올바른 명령어
python scripts/build_safety_db.py
```

---

### 오류 D: `bash: ngrok: command not found`

**원인**: 로컬 PC에 ngrok이 직접 설치되어 있지 않음

**해결**: `ngrok` 앞에 `npx`를 붙여 즉시 실행 (설치 불필요)

```bash
npx ngrok http 8000 --authtoken $NGROK_AUTHTOKEN
```

최초 실행 시 `Ok to proceed? (y)` 문구가 뜨면 `y` 입력

---

### 오류 E: `CommandError: Failed to get properties for device ... adb.exe: device offline`

**원인**: 스마트폰이 절전 모드 진입 또는 USB 연결이 순간 끊겨 adb가 기기를 인식하지 못함

**해결**:

```bash
adb kill-server
adb start-server
adb devices  # "device" 상태인지 확인
```

확인 후 폰 화면을 켜두고 `npm run android` 재실행

---

### 오류 F: `adb: failed to install app-debug.apk` (non-zero code: 1)

**원인**: 스마트폰에 이전 버전 앱이 남아있어 서명 충돌 발생

**해결**:

```bash
# 1. adb로 강제 삭제 시도
adb uninstall com.minchodan.app
adb uninstall com.minchodan.client

# 2. 스마트폰에서 직접 삭제
# 홈 화면 > Minchodan 앱 아이콘 길게 누르기 > 삭제(Uninstall)

# 3. 재빌드
npm run android
```

빌드 중 폰 화면을 주시하다가 **보안 팝업**이 뜨면 **"허용"** 또는 **"무시하고 설치"** 터치

---

### 오류 G: 스마트폰 화면에 `"The development server returned response error code: 500"`

**원인**: Metro 번들러가 자바스크립트 조립 중 패키지 누락 또는 구문 오류 발생

**확인**: `npm run android` 실행 중인 PC 터미널에서 빨간색 에러 메시지 확인

| 에러 내용 | 해결 방법 |
| :--- | :--- |
| `Unable to resolve "expo-image-manipulator"` | `npm install` 재실행 |
| `Unable to resolve "jpeg-js"` | `npm install jpeg-js` 실행 |
| `WS_URL` 백틱 템플릿 구문 오류 | `index.ts`에서 일반 따옴표 문자열로 수정 |

수정 후 `npm run android` 재실행

---

### 오류 H: `Unable to load script. Make sure you're running Metro...`

**원인**: 스마트폰이 PC의 Metro 번들러 서버(포트 8081)에 접근하지 못함

**해결**: USB 포트 역방향 터널 설정 후 폰에서 RELOAD

```bash
adb reverse tcp:8081 tcp:8081
adb reverse tcp:8000 tcp:8000
```

명령 완료 후 스마트폰 화면의 **RELOAD** 버튼 터치

---

### 오류 I: 스마트폰 앱 화면이 검은 화면으로 유지됨

**원인 및 해결**:

| 원인 | 확인 방법 | 해결 방법 |
| :--- | :--- | :--- |
| 카메라 권한 미승인 | 설정 > 앱 > Minchodan > 권한 | 카메라 권한 **허용**으로 변경 |
| 번들 로딩 중 | PC 터미널에 `Bundling...` 표시 | 30~60초 대기 |
| JS 런타임 에러 | 폰을 흔들어 개발자 메뉴 열기 | 에러 내용 확인 후 조치 |
| Metro 서버 미연결 | PC 터미널에 서버 종료 메시지 | `adb reverse tcp:8081 tcp:8081` 재실행 |

---

### 오류 J: 앱 화면에 `WS: fallback` 및 `폴백 모드` 배너 표시

**원인**: WebSocket 서버(FastAPI)에 연결 실패

**확인**:

```bash
docker ps  # minchodan-fastapi STATUS가 "Up"인지 확인
docker logs minchodan-fastapi --tail 20  # 에러 로그 확인
```

**해결**:

```bash
docker restart minchodan-fastapi
```

재기동 후 앱 강제 종료 및 재실행

---

### 참고: `DETECTOR_TYPE=mock` 환경 변수에 대하여

`.env` 파일의 `DETECTOR_TYPE=mock` 설정은 **현재 서버 코드에서 읽히지 않는 죽은 변수(Dead Variable)**입니다. 서버는 이 설정과 무관하게 항상 실제 YOLO AI 모델(`server/models/yolo26n/`)을 로드하여 추론을 실행합니다.

---

> 이 문서에서 해결되지 않는 새로운 오류가 발생하면, 에러 메시지 전문을 복사하여 팀원 또는 AI 에이전트에게 문의하십시오.
