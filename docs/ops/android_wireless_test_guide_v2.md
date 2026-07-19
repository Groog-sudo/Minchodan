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

### 4단계: Tailscale 연결 및 모바일 주소 연동

서버 PC와 Android 단말을 같은 tailnet에 연결하고 서버 주소를 확인합니다.

**PowerShell 환경**:
```powershell
tailscale status
tailscale ip -4
```

**Git Bash 환경**:
```bash
tailscale status
tailscale ip -4
```

`client/.env`에 서버 Tailscale 주소를 설정합니다.

```ini
EXPO_PUBLIC_NETWORK_MODE=tailscale
EXPO_PUBLIC_TAILSCALE_HOST=[SERVER_TAILSCALE_IP_OR_MAGICDNS]
EXPO_PUBLIC_SERVER_PORT=8000
```

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

### 오류 C: RAG 빌드 스크립트 경로 오류 (`build_chroma.sh` 등)

**원인**: 구버전 쉘 스크립트(`build_chroma.sh`) 참조. 현재는 Python 빌더 사용.

**해결**:

```bash
python scripts/build_safety_db.py
# 선택: python scripts/build_convenience_db.py
```

---

### 오류 D: `tailscale: command not found`

**원인**: 로컬 PC에 Tailscale CLI가 설치되어 있지 않거나 PATH에 등록되지 않음

**해결**: 운영체제용 Tailscale 앱을 설치하고 로그인한 뒤 `tailscale status`로 연결 상태를 확인합니다. 상세 절차는 [tailscale_connection_guide.md](tailscale_connection_guide.md)를 따릅니다.

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

### 오류 K: adb reverse 실행 시 무한 렉(명령어 행 걸림)이 발생하거나, adb devices 실행 시 아웃풋이 전혀 없는 경우

**원인**: 윈도우 OS 백그라운드에 여러 버전의 `adb.exe` 프로세스가 좀비 상태로 중복 구동되어 5037 포트(ADB 기본 통신 포트)를 선점 및 교착상태(Deadlock)에 빠뜨려 adb 명령이 응답하지 못함. 이로 인해 Metro 번들러 연결 세션이 끊겨 폰 화면에 검은 화면만 유지되고 PC 터미널에 `No apps connected`가 지속됨.

**해결**:
1. PC 터미널에서 아래 명령어를 실행하여 백그라운드에서 교착 상태에 빠진 모든 `adb.exe` 프로세스를 강제 종료:
   ```powershell
   taskkill /f /im adb.exe
   ```
2. 스마트폰의 **USB 연결 선을 뽑았다가 3초 후 다시 연결**.
3. 아래 명령으로 ADB 데몬 서버를 클린 재기동하고 연결 기기 상태를 확인:
   ```bash
   adb start-server
   adb devices  # 기기 ID 옆에 device가 정상 표기되는지 확인
   ```
4. Metro 포트 바인딩 터널을 다시 활성화:
   ```bash
   adb reverse tcp:8081 tcp:8081
   ```
5. 단말에서 앱을 완전히 종료하고 수동으로 재실행하여 연동을 확인.

---

### 번들러 연결 해제(No apps connected) 재발 방지책 및 행동 수칙

코드 수정 후 저장하거나 단말 연결이 끊겨 'No apps connected' 오류가 빈번하게 재발할 때의 영구 방지책과 발생 시의 행동 수칙입니다.

#### 1. 원천 방지 및 우회 방안
- **무선 디버깅(Wireless Debugging) 활성화**:
  - USB 연결 단자의 노후화나 접촉 불량으로 인한 adb reverse 연결 해제를 방지하기 위해 스마트폰 개발자 옵션에서 '무선 디버깅'을 켜고 PC와 무선으로 페어링해 두면 연결 해제 빈도를 대폭 줄일 수 있습니다.
- **단말기에서 수동 리로드 수행**:
  - PC 터미널에서 'r' 키를 눌러 명령을 전송하면 Metro 서버가 기기 세션을 먼저 검색하므로 에러가 날 확률이 높습니다.
  - 대신 스마트폰을 흔들어 Expo 개발자 메뉴를 연 뒤 **[Reload]**를 직접 터치해 주면 단말기가 Metro 서버를 찾아가므로 포트 꼬임이 덜 발생합니다.

#### 2. 원클릭 복구 배치파일(reverse.bat) 활용
- 디바이스 재연결로 포트 터널링이 끊겼을 때 매번 타이핑하지 않고 한 번에 복구할 수 있는 원클릭 배치파일을 생성해 두었습니다.
- **경로**: `client/reverse.bat`
- **사용법**: 'No apps connected' 에러 발생 시, 해당 배치파일을 **더블 클릭하여 실행**하기만 하면 자동으로 adb 상태를 체크하고 8081/8000 포트를 일괄 재바인딩해 줍니다.

#### 3. 발생 시 고정 행동 수칙 (체크리스트)
1. 스마트폰 화면을 켜고 민초단 앱을 전면에 띄웁니다.
2. `client/reverse.bat` 파일을 실행하여 터널을 재연동합니다.
3. 스마트폰 화면을 흔들어 개발자 메뉴에서 **[Reload]**를 직접 터치합니다.
4. 만약 여전히 로딩되지 않는다면, 폰에서 앱을 아예 강제 종료한 뒤 다시 켜고 터미널에서 `npm run android`를 재실행합니다.

---

### 오류 L: Metro 번들러 실행 중 `index.ts (1 module)` 상태로 멈추며 로딩되지 않거나, `unauthorized/uninitialized` 기기로 감지되어 adb 연동이 차단되는 현상

**1. `index.ts (1 module)` 멈춤 현상**
- **원인**:
  - `src/services/frameProvider.ts`와 `realFrameProvider.ts` 간의 고질적인 순환 참조(Require cycle) 경고 및 번들러 캐시의 심각한 오염으로 인해 모듈 컴파일이 1개에서 중단됨.
- **해결**:
  - **순환 참조 제거**: `realFrameProvider.ts` 내에 `FRAME_SIZE` 상수를 내부 선언으로 수정하여 순환 의존성을 완전히 제거 완료했습니다.
  - **캐시 클리어 실행**: 터미널을 완전히 종료하고, 아래 명령으로 Metro 번들러 캐시만 소거하며 번들러를 띄웁니다. 앱이 이미 한 번 설치된 상태라면 굳이 expo run:android를 재실행하지 않고 번들러만 띄우는 것이 가장 빠르고 꼬이지 않습니다:
    ```bash
    npm start -- --clear
    ```
    또는
    ```bash
    npx expo start -c
    ```

**2. `unauthorized` 또는 `uninitialized` 디바이스 경고 현상**
- **원인**: PC에 상주하는 여러 버전의 adb 데몬이 꼬이거나 단말의 USB 보안 서명(인증 토큰) 락이 깨져 통신이 유효하지 않게 됨.
- **해결**:
  1. 기기의 **USB 연결 케이블을 해제**합니다.
  2. 스마트폰 설정 > 개발자 옵션 > **"USB 디버깅 권한 승인 취소"** 버튼을 클릭하여 저장된 PC 인증 정보를 초기화합니다.
  3. USB 케이블을 스마트폰에 **다시 연결**합니다.
  4. 스마트폰 화면에 다시 노출되는 **"USB 디버깅을 허용하시겠습니까? (이 컴퓨터에서 항상 허용)"** 팝업 창에서 **반드시 항상 허용 체크 후 [확인]**을 누릅니다.
  5. `client/reverse.bat`를 재실행하고 번들러를 켭니다.

---

### 참고: `DETECTOR_TYPE=mock` 환경 변수에 대하여

`.env` 파일의 `DETECTOR_TYPE=mock` 설정은 **현재 서버 코드에서 읽히지 않는 죽은 변수(Dead Variable)**입니다. 서버는 이 설정과 무관하게 항상 실제 YOLO AI 모델(`server/models/yolo26n/`)을 로드하여 추론을 실행합니다.

---

> 이 문서에서 해결되지 않는 새로운 오류가 발생하면, 에러 메시지 전문을 복사하여 팀원 또는 AI 에이전트에게 문의하십시오.
