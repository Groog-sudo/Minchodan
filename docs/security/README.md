# Minchodan 보안 문서 인덱스

> **작성일**: 2026-07-19
> **버전**: v1.0.0
> **상태**: 운영 보안 기준 및 팀 반영 절차 관리
> **적용 범위**: 서버, 관제 콘솔, 모바일 클라이언트, Docker, Redis, MariaDB, Python·npm 의존성, GPU 실행 환경

---

## 1. 목적

이 폴더는 Minchodan 프로젝트에서 수행한 보안 점검, 예방 조치, 팀 적용 절차, 검증 결과와 남은 위험을 한곳에서 관리한다. 보안 설정은 코드만 병합해서 완료되는 작업이 아니므로, 각 팀원은 자신의 운영체제와 담당 영역에 맞는 후속 절차까지 수행해야 한다.

보안 문서는 실제 비밀값을 보관하는 장소가 아니다. 토큰, 비밀번호, 개인 IP, Tailscale 주소, 인증서 개인키, 단말 식별값과 운영 데이터는 문서에 기록하지 않는다.

---

## 2. 문서 목록

| 문서 | 상태 | 주요 독자 | 설명 |
| :--- | :--- | :--- | :--- |
| [보안 강화 및 팀 반영 가이드](security_hardening_and_team_adoption_guide.md) | **현재 기준** | 전 팀원 | 수정 전 취약점, 예상 피해, 구현한 예방 조치, 운영체제별 반영 순서, 검증 명령, 잔여 위험을 설명한다. |

---

## 3. 보안 문서 작성 원칙

| 원칙 | 필수 기준 | 금지 사항 |
| :--- | :--- | :--- |
| **비밀값 비기록** | 환경 변수 이름과 플레이스홀더만 기록한다. | 실제 토큰, 비밀번호, API 키, 개인 IP, Tailscale 주소를 기록하지 않는다. |
| **코드 근거 명시** | 정책을 구현한 파일과 검증 경로를 함께 적는다. | 구현되지 않은 계획을 완료 상태로 표현하지 않는다. |
| **검증 수준 분리** | 정적 검사, 자동 테스트, 컨테이너 설정, 실장 서버, 실기기 결과를 분리한다. | 단위 테스트 통과를 종단간 운영 검증 완료로 확대 해석하지 않는다. |
| **팀 반영 절차 포함** | 비밀값 생성, 서비스 재기동, 토큰 재발급, 앱 재빌드, 검증 순서를 작성한다. | 코드 병합만으로 보안 전환이 끝났다고 표현하지 않는다. |
| **잔여 위험 공개** | 미해결 CVE와 구조적 한계를 위험도·대응책과 함께 남긴다. | 알려진 위험을 누락하거나 근거 없이 안전하다고 단정하지 않는다. |
| **문서 교차 검증** | `docs/README.md`, 루트 `README.md`, 환경 변수·배포·테스트 문서와 함께 갱신한다. | 보안 문서만 단독 수정해 기존 운영 문서와 충돌하게 두지 않는다. |

---

## 4. 문서를 갱신해야 하는 시점

| 변경 유형 | 반드시 확인할 내용 | 함께 갱신할 문서 |
| :--- | :--- | :--- |
| 인증·인가 정책 변경 | JWT 클레임, 토큰 만료, 역할별 권한, 부트스트랩 절차 | `docs/design/api_specification.md`, `docs/ops/environment_variables.md` |
| WebSocket·REST 계약 변경 | 인증 메시지 순서, 업로드 제한, 오류 코드, 재연결 정책 | `docs/design/api_specification.md`, `docs/ops/test_specification.md` |
| Docker·DB·Redis 변경 | 바인딩 주소, 비밀번호 필수 여부, 마운트 권한, 헬스체크 | `docs/ops/deployment_guide.md`, `docs/design/architecture.md` |
| 모바일 네트워크 정책 변경 | `ws`/`wss`, ATS, Android cleartext, 단말 JWT 전달 방식 | `docs/ops/wireless_test_guide.md`, `client/.env.example` |
| 의존성·GPU 기준 변경 | CVE, PyTorch·CUDA 호환성, RTX 5090, MPS·CPU 폴백 | `requirements.txt`, `docs/ops/ai_model_hardware_setup.md` |
| 검증 결과 변경 | 테스트 수, 감사 결과, 실장 서버·실기기 완료 여부 | `docs/ops/code_quality_guide.md`, `docs/ops/test_specification.md` |

---

## 5. 빠른 독해 순서

| 순서 | 대상 | 읽을 절 |
| :---: | :--- | :--- |
| 1 | 전 팀원 | 상세 가이드의 **요약**, **금지 사항**, **팀 공통 반영 순서** |
| 2 | 백엔드 담당 | **인증·인가**, **업로드·요청 제한**, **API 노출 축소** |
| 3 | 모바일 담당 | **단말 인증**, **TLS**, **iOS·Android 네이티브 재빌드** |
| 4 | 콘솔 담당 | **토큰 저장소**, **REST·SSE·WebSocket 인증 방식** |
| 5 | 인프라 담당 | **비밀값**, **Docker·Redis·MariaDB**, **GPU·OS 호환성** |
| 6 | QA 담당 | **검증 명령**, **배포 승인 기준**, **잔여 위험** |

---

## 6. 절대 저장하지 않는 정보

| 정보 유형 | 안전한 문서 표현 | 실제 보관 위치 |
| :--- | :--- | :--- |
| JWT 서명 키 | `JWT_SECRET_KEY=[32자 이상 임의값]` | Git에서 제외된 루트 `.env` 또는 조직 비밀관리 시스템 |
| 최초 관리자 토큰 | `ADMIN_BOOTSTRAP_TOKEN=[1회용 임의값]` | Git에서 제외된 루트 `.env`; 사용 후 회전 또는 제거 |
| Redis·DB 비밀번호 | 환경 변수 이름만 기재 | Git에서 제외된 `.env` 또는 배포 비밀 저장소 |
| 단말 JWT | `EXPO_PUBLIC_DEVICE_TOKEN=[발급된 단말 JWT]` | 개발 단말의 로컬 환경 파일; 운영 배포는 안전한 프로비저닝 경로 |
| 개인·사내 네트워크 주소 | `[TAILSCALE_HOST]`, `[SERVER_HOST]` | Git에서 제외된 내부 운영 문서 또는 승인된 비밀 저장소 |
| 사용자 개인정보 | 데이터 종류와 보존 정책만 기재 | 접근 통제가 적용된 운영 DB |

---

## 7. 현재 핵심 잔여 위험

| 위험 | 현재 상태 | 임시 통제 | 후속 과제 |
| :--- | :--- | :--- | :--- |
| ChromaDB 의존성 공개 취약점 | `chromadb==1.5.9`에 수정 버전이 없는 공개 취약점이 남아 있다. | 외부 서비스 모드가 아닌 로컬 `PersistentClient`로 사용하고 접근 경계를 제한한다. | 수정 버전 발표 후 즉시 업데이트하고 RAG 회귀 테스트를 수행한다. |
| 요청 제한의 단일 프로세스 범위 | 현재 슬라이딩 윈도우 제한기는 프로세스 메모리를 사용한다. | 단일 서버 배포에서는 유효하며 앞단 네트워크 접근도 제한한다. | 다중 워커·다중 서버 배포 전 Redis 기반 분산 제한기로 교체한다. |
| 운영 데이터의 필드 단위 암호화 | DB 접근 통제는 강화했으나 개인정보 필드 암호화는 별도 과제다. | DB 계정·네트워크·권한을 최소화하고 로그에서 개인정보를 제거한다. | 암호화 키 관리, 필드 암호화, 보존·파기 정책을 설계한다. |
| 단말 JWT 즉시 폐기 | 만료와 서명 키 회전은 가능하지만 개별 토큰 폐기 목록은 없다. | 단말 JWT 수명을 제한하고 분실 시 서명 키 또는 발급 정책을 회전한다. | 단말별 `jti` 폐기 목록과 관리 API를 구현한다. |
| 실장 환경 검증 | 정적·자동 검증은 완료했으나 모든 운영체제와 실기기 종단 검증은 별도 수행이 필요하다. | 병합 후 운영체제별 체크리스트를 완료하기 전 운영 배포를 승인하지 않는다. | Ubuntu·Windows RTX 5090, macOS, iOS·Android 실기기 검증 결과를 기록한다. |

---

## 8. 관련 문서

| 문서 | 연결 목적 |
| :--- | :--- |
| [`../ops/environment_variables.md`](../ops/environment_variables.md) | 보안 관련 환경 변수의 단일 명세 |
| [`../ops/deployment_guide.md`](../ops/deployment_guide.md) | Docker·Redis·MariaDB 배포 절차 |
| [`../ops/code_quality_guide.md`](../ops/code_quality_guide.md) | Ruff, Bandit, mypy, pip-audit, npm audit 실행 기준 |
| [`../ops/test_specification.md`](../ops/test_specification.md) | 보안 회귀 테스트를 포함한 검증 기준 |
| [`../design/api_specification.md`](../design/api_specification.md) | 관리자·단말·WebSocket 인증 계약 |
| [`../design/architecture.md`](../design/architecture.md) | Tailscale 기반 네트워크 경계와 시스템 구조 |
