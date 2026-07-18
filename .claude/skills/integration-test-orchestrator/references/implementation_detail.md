# 통합 테스트 환경 오케스트레이션 — 상세 구현 레퍼런스

> 본 문서는 [`SKILL.md`](../SKILL.md)의 "로그 우선 디버깅" 절이 참조하는 계층별 트러블슈팅 상세 표입니다. 아래 실측 사례는 실제 세션에서 재현·해결된 것을 근거로 정리했습니다.

---

## 1. 계층 분리 진단 원칙

이상 발견 시 아래 순서로 계층을 하나씩 격리합니다. 한 계층이 정상 확인되면 그 계층을 원인 후보에서 제외하고 다음 계층으로 넘어갑니다.

```mermaid
flowchart LR
    A["단말(iOS)"] --> B["네트워크"]
    B --> C["Docker/FastAPI"]
    C --> D["DB(MariaDB/Redis)"]
    D --> E["호스트 Ollama"]
    E --> F["GPU/추론"]
```

| 순서 | 확인 명령 | 정상 신호 |
| :---: | :--- | :--- |
| 1 | `curl -sf http://localhost:${WS_PORT:-8000}/health` | `{"status":"healthy",...}` |
| 2 | `docker ps --format "table {{.Names}}\t{{.Status}}"` | 3개 컨테이너 모두 `Up` |
| 3 | `docker exec minchodan-mariadb mariadb -u... -e "SHOW TABLES;"` | 기대 테이블 목록 출력 |
| 4 | `curl -sf ${OLLAMA_BASE_URL:-http://localhost:11434}/api/tags` | 모델 목록 JSON |
| 5 | Metro 로그에 `[WS] 연결 시도 주소` 및 서버 로그에 `[accepted]`/`welcome 송신 완료` 동시 확인 | 단말↔서버 핸드셰이크 성공 |

---

## 2. 계층별 트러블슈팅 표

| 증상 | 계층 | 원인 | 조치 |
| :--- | :--- | :--- | :--- |
| `docker ps`가 "Cannot connect to the Docker daemon" | Docker | Docker Desktop이 실행 중이 아님(데몬 소켓 없음) | `open -a Docker` 후 최대 60초 폴링(`until docker info >/dev/null 2>&1; do sleep 2; done`) |
| `SHOW TABLES;` 결과에 최근 마이그레이션 테이블이 없음 | DB | `docker-entrypoint-initdb.d`는 **최초 빈 볼륨 생성 시에만** 실행됨 — 기존에 떠 있던 볼륨은 이후 추가된 `server/db/migrations/*.sql`을 자동 반영하지 않음 | `server/db/migrations/` 파일명 타임스탬프 순으로 `docker exec -i minchodan-mariadb mariadb ... < migration.sql` 수동 적용 |
| 서버는 `healthy`인데 실기기가 연결 안 됨 | 네트워크 | `client/.env`의 `EXPO_PUBLIC_WIFI_HOST`/`EXPO_PUBLIC_LAN_IP`가 현재 Mac의 실제 LAN IP와 다름(DHCP 재할당 등) | `ipconfig getifaddr en0`(또는 실제 활성 인터페이스, `en1`일 수 있음)로 현재 IP 확인 후 `client/.env` 갱신 |
| Metro 로그에 `연결 종료 code=1006 ... after 10000ms` 반복, 이후 다른 후보로 재시도 | 네트워크 | `expandWsUrlCandidates()`가 LAN/Tailscale 등 여러 후보를 순환하는데, 도달 불가능한 후보(Tailscale 등)가 매 재연결마다 10초씩 소모 | `useWebSocket.ts`의 후보 쿨다운(`candidateCooldownUntilRef`, 2026-07-18 추가)이 정상 동작하는지 확인. 없다면 도달 불가 후보를 `client/.env`에서 임시 제거 |
| `xcodebuild`/`launch_app_device`가 "device was not, or could not be, unlocked" | 단말 | 실기기가 잠금 상태 | 사용자에게 잠금 해제 요청 후 `launch_app_device`만 재시도(재빌드 불필요) |
| 서버 로그에 `Cannot call "send" once a close message has been sent` | 서버↔단말 경합 | 클라이언트가 `hello` 전송 직후, 서버가 `auth_ok`를 보내기 전에 연결을 끊는 타이밍(재연결 후보 전환 중 흔함) | `except Exception`으로 이미 안전하게 처리됨(세션 정리까지 수행) — 재발 빈도가 비정상적으로 높으면 클라이언트 재연결 로직(후보 전환 주기)을 먼저 의심 |
| 서버 코드(`server/`)를 수정했는데 컨테이너에 반영 안 됨 | Docker | `docker-compose*.yml`이 `server/`를 볼륨 마운트하지만, `uvicorn`이 `--reload` 없이 떠 있어 프로세스가 이미 임포트한 모듈은 재로딩되지 않음 | `docker restart minchodan-fastapi`(재빌드 불필요 - 이미지에는 `server/`가 `COPY`되지 않고 볼륨으로만 전달됨, `docker/Dockerfile` 하단 주석 참조) |
| `requirements.txt`/`Dockerfile` 미변경 서버 코드 수정 후 재빌드 여부 | Docker | 이미지 레이어 중 `server/`는 존재하지 않음(볼륨 마운트 전용) | `docker build` 불필요. `docker restart`만으로 충분 |
| iOS index.html(내비 지도 iframe) 관련 코드 수정 후 반영 안 됨 | 정적 파일 서빙 | `server/navigation/server.py`의 `get_index()`가 매 요청마다 파일을 새로 읽으므로 서버 재시작은 불필요하나, **이미 로드된 iframe은 예전 JS를 메모리에 유지**함 | 콘솔 브라우저에서 해당 iframe을 포함한 페이지를 강력 새로고침(또는 지도 토글 off/on으로 iframe 재마운트) |
| React Native LogBox 알림이 화면 하단 버튼을 계속 가림 | 클라이언트 UI | 이미 원인이 파악되고 안전 처리(catch)되는 경고가 반복 `console.warn`되어 LogBox 토스트가 재노출됨 | 근본 원인을 고치는 것이 원칙이나, 확인된 무해 경고는 `App.tsx`의 `LogBox.ignoreLogs([...])`에 화이트리스트로 추가(새로운 유형 경고는 계속 노출되어야 하므로 패턴을 넓게 잡지 않음) |
| `pointerEvents="none"`인 부모 아래 버튼이 안 눌림 | 클라이언트 UI | React Native에서 `"none"`은 자신뿐 아니라 하위 서브트리 전체를 터치 타깃에서 제외함(`"box-none"`과의 핵심 차이 - 자식에 `"box-none"`을 다시 걸어도 무효) | 터치가 필요한 버튼/인터랙티브 요소는 `pointerEvents="none"` 컨테이너 **밖에** 별도 `pointerEvents="box-none"` 형제로 배치 |
| iframe에서 `postMessage` 콜백마다 새 WebSocket 연결이 쌓임 | 클라이언트(웹) | 재연결 함수에 "이미 연결돼 있으면 재사용" 가드가 없어 매 호출마다 `new WebSocket()` | 연결 함수 진입부에 `if (ws && (ws.readyState === OPEN || CONNECTING)) return;` 가드 추가 |

---

## 3. 세션 디렉토리 로그 대조 예시

여러 로그를 동시에 보며 원인을 좁힐 때, 타임스탬프를 기준으로 아래처럼 교차 대조합니다.

```text
$LOG_DIR/metro.log:        [WS] 연결 시도 주소: ws://172.30.1.100:8000/... (후보 1/2)
$LOG_DIR/fastapi.log:      INFO: ... "WebSocket /ws/detect?device_id=dev-001" [accepted]
$LOG_DIR/fastapi.log:      [WS] welcome 송신 완료 - device_id: dev-001
$LOG_DIR/device_console.log: [DEBUG_WS] welcome 송신 완료 - device_id: dev-001
```

세 로그의 타임스탬프가 수백 ms 이내로 일치하면 핸드셰이크는 정상이며, 이후 문제는 애플리케이션 로직(탐지/가이드 생성) 계층으로 좁혀집니다.

---

## 4. 백그라운드 로그 모니터링 시 주의사항

- `docker logs -f`를 필터 없이 그대로 tail하면 `DEBUG` 레벨 `httpcore`/`httpx` 로그(외부 API 호출)에 묻혀 정작 중요한 `ERROR`/연결 상태 로그를 놓치기 쉽습니다. `grep -iE "ERROR|Traceback|Exception|CRITICAL|connection open|connection closed|\[accepted\]"` 수준으로 좁혀서 모니터링합니다.
- 실사용 테스트(버튼 조작, 화면 전환) 중에는 반사/인지 가이드 로그가 초당 여러 건 발생할 수 있습니다. 이런 정상 트래픽까지 전부 알림으로 받으면 노이즈가 커지므로, 오류·연결 상태 변화만 필터링 대상으로 유지합니다.
- 재연결 폭주(초당 여러 건 `[accepted]`)가 관측되면 즉시 원인을 찾기 전에 먼저 컨테이너를 재시작해 누적된 좀비 연결을 정리하고, 그 다음 클라이언트/iframe 쪽 재연결 가드 로직을 점검합니다.
