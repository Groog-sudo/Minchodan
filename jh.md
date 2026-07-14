# 2026-07-14 Commit Note

## Commit Message

style(console): 회원등록 폼 1열 세로 정렬 및 등록 버튼 높이 조정

## Staged Changes (정확 기준)

- 대상 파일: `console/src/styles.css`
- `.member-form` 레이아웃을 다열 자동 배치에서 1열 고정으로 변경
  - `grid-template-columns: 1fr`
  - `row-gap: 16px`, `column-gap: 0`
- `.member-form label` 간격을 `gap` 단일값에서 축별 값으로 조정
  - `row-gap: 14px`, `column-gap: 6px`
- 회원등록 폼 내부 등록 버튼 세로 크기 증가
  - `.member-form .refresh-btn { padding: 10px 10px; }`

## Scope

- 회원관리 페이지의 등록 폼 UI 배치 및 버튼 높이만 변경
- 비즈니스 로직/API/상태관리 변경 없음

---

## Commit Message

fix(console): localhost 하드코딩 제거 및 네트워크 URL 해석 공통화

## Pending Changes (정확 기준)

- 신규 파일 추가: `console/src/config/network.ts`
  - `resolveApiBaseUrl(apiBaseUrlFromEnv?)`:
    - `VITE_API_BASE_URL`이 없거나 파싱 실패 시 `http(s)://{현재브라우저호스트}:8000` 폴백
    - env 주소가 `localhost/127.0.0.1/::1`인데 콘솔 접속 호스트가 원격이면 현재 브라우저 호스트로 자동 치환
    - trailing slash 제거
  - `resolveServiceUrl(envUrl, pathFromApiBase, apiBaseUrlFromEnv?)`:
    - 서비스별 URL env(`VITE_MONITOR_STREAM_URL`, `VITE_NAV_MAP_URL`) 우선
    - 없거나 파싱 실패 시 API Base + 경로로 생성
    - localhost 원격접속 치환 동일 적용

- 변경 파일: `console/src/components/Login.tsx`
  - 로그인 엔드포인트를 `http://localhost:8000/api/v1/admin/login` 하드코딩에서
    `resolveApiBaseUrl(...)` 기반 `LOGIN_ENDPOINT`로 변경

- 변경 파일: `console/src/api/useMembers.ts`
  - `API_BASE_URL` 생성 로직을 공통 `resolveApiBaseUrl(...)` 사용으로 변경

- 변경 파일: `console/src/api/useDetectionLogs.ts`
  - `API_BASE_URL` 생성 로직을 공통 `resolveApiBaseUrl(...)` 사용으로 변경

- 변경 파일: `console/src/api/useLiveFeed.ts`
  - `API_BASE_URL` 생성 로직을 공통 `resolveApiBaseUrl(...)` 사용으로 변경
  - 이 값을 기반으로 WS URL(`.../ws/console/live-feed`) 유지

- 변경 파일: `console/src/api/useMonitorStream.ts`
  - `DEFAULT_STREAM_URL`을 고정 문자열에서 `resolveServiceUrl(...)` 계산값으로 변경
  - `resolvedUrl` 계산도 공통 URL 해석 함수 사용하도록 변경

- 변경 파일: `console/src/components/LiveCameraFeed.tsx`
  - `NAV_MAP_URL`을 고정 기본값 대신 `resolveServiceUrl(...)` 기반으로 변경

- 변경 파일: `console/src/components/OperatorLiveMap.tsx`
  - `NAV_MAP_URL`을 고정 기본값 대신 `resolveServiceUrl(...)` 기반으로 변경

## Scope

- 콘솔의 API/SSE/WS/지도 URL 결정 로직 공통화
- localhost 하드코딩으로 인한 원격 접속 `Failed to fetch` 재발 방지
- UI/DB 스키마/백엔드 비즈니스 로직 변경 없음
