# Changelog - dg2

> 이 파일은 **dg2**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-07-16 | 2단계 | camera_rendering_fix

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 카메라 렌더링 문제를 해결하기 위해 supportsStream 프록시 감지 우회 및 ArrayBuffer 바이너리 폴백 대응 추가
- **관련 파일**: 없음
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

### 2026-07-17 | 공통 | tailscale_server_ip_update

- **커밋**: `config: update tailscale server ip to 100.85.229.93`
- **변경 내용**:
  - Tailscale 서버 IP 변경에 따라 클라이언트 및 관련 설정 파일의 IP 주소를 100.85.229.93으로 최신화
- **관련 파일**: `client/.env`, `client/src/config/index.ts`, `client/ios/Minchodan/AppDelegate.swift`, `docs/ops/tailscale_connection_guide.md`
- **검증 결과**: 파일 변경 내용이 정확하게 반영됨.

### 2026-07-17 | 관제 콘솔 | dynamic_camera_rotation

- **커밋**: `feat: support dynamic camera rotation based on device platform`
- **변경 내용**:
  - 관제 콘솔의 실시간 카메라 피드(LiveCameraFeed) 회전 기능을 하드코딩(0도)에서 연결된 모바일 기기의 플랫폼 종류(iOS, Android)에 따라 동적으로 설정되도록 구조 개선
  - Android 기기 연결 시 90도 회전을 적용하고 그에 따른 BBox 바운딩 박스 정렬 보정 함수(getDisplayBBox)도 rotateDeg에 연동되도록 수정
- **관련 파일**: `console/src/components/LiveCameraFeed.tsx`, `console/src/pages/DashboardPage.tsx`
- **검증 결과**: `tsc --noEmit && vite build`를 실행하여 컴파일 및 타입 검사 정상 통과 완료

