# dev 8b2f606 개선 실행 계획서

> **작성일**: 2026-07-11
> **버전**: v1.0.1 (2026-07-11 kb 병합 시 정합 노트 추가 - 원본 본문 무변경)
> **기준선**: 원격 dev 브랜치 커밋 8b2f606 감사 결과
> **목적**: 감사에서 확인된 위험을 안전성, 파이프라인 정합성, 품질 게이트, 운영 문서 순서로 해결하기 위한 실행 기준입니다.

> **2026-07-11 정합 노트 (kb 병합 시 추가)**: 본 계획서의 기준선은 dev `8b2f606`이며,
> 이후 kb 브랜치에서 일부 항목이 이미 진행되었습니다. (1) §5 "설계 원본 갱신"의
> Llava/Kokoro·Coqui/base64 MP3/expo-av 구기술 표현 교체는 `architecture.md` v0.4.x와
> `AGENTS.md` v0.3.2에서 상당 부분 완료. (2) §2 "인증 기본값 제거", §2 "반사 억제
> 재설계", §5 "환경변수 단일 명세"는 [`docs/research/mitos_improvement_roadmap.md`](../research/mitos_improvement_roadmap.md)
> (Mitos 보완 로드맵)와 스코프가 겹치므로 착수 전 두 문서를 함께 확인할 것.
> (3) §4의 Ruff/mypy 등 품질 수치는 8b2f606 기준으로, kb 병합 후 재측정이 필요합니다.

---

## 1. 개선 목표

| 목표 | 완료 기준 | 우선순위 |
| --- | --- | --- |
| 실제 YOLO 실행 상태를 명확히 보장 | 커스텀 탐지 29클래스와 노면 4클래스 가중치가 모두 확인되지 않으면 yolo 모드 기동 실패 | P0 |
| 반사 경로 안전성 보장 | 서버와 단말의 고위험 클래스, 억제 조건, 재경보 조건이 하나의 기준으로 일치 | P0 |
| 인지 경로의 데이터 계약 확정 | Redis 소비형 또는 직접 호출형 중 하나로 코드와 설계를 일치 | P0 |
| RAG 검색 정합성 복구 | 29개 객체와 4개 노면 라벨의 Top-5 회귀 테스트 및 E2E 통과 | P0 |
| 운영 가능한 품질 기준 복구 | dev push에서 Python, Client, Console, 문서 검증이 모두 통과 | P1 |

---

## 2. 1차 개선: 안전성과 실행 기준선

| 작업 | 구현 방향 | 검증 방법 | 담당 영역 |
| --- | --- | --- | --- |
| YOLO 가중치 fail-closed | DETECTOR_TYPE=yolo에서 탐지·분할 커스텀 가중치가 모두 없으면 서버 시작을 중단합니다. COCO 기본 모델과 Mock 자동 대체는 데모 모드에서만 허용합니다. | 가중치 누락 시 기동 실패, 정상 가중치에서 클래스 수와 출력 shape 확인 | TH, YOLO |
| 모델 manifest | 파일명, SHA-256, 객체/노면 클래스 수, 학습 데이터 기준, 배포일을 manifest로 관리합니다. | 서버 시작 시 manifest와 실제 파일 대조 | TH, YOLO |
| health 실상태 공개 | requested_detector와 loaded_detector, weights_path, class_count를 분리해 표시합니다. | Mock, YOLO, 가중치 누락 상태 각각 확인 | TH, Backend |
| 반사 위험도 SSOT | 서버 Gate와 모바일 온디바이스의 고위험 클래스·거리·방향 규칙을 공통 데이터 계약으로 통일합니다. | 동일 입력 프레임에서 서버/단말 위험 등급 비교 | TH, Mobile |
| 반사 억제 재설계 | 고위험은 device_id + track_id + alert_type 기준 0.5~3초 debounce를 적용하고 위험 영역 재진입 시 즉시 재경보합니다. | 새 객체, 재진입, 연속 프레임 시나리오 테스트 | DG, TTS |
| 인증 기본값 제거 | 개발 토큰·ngrok 주소·JWT 키를 환경별 설정으로 분리하고 관리자 최초 등록은 bootstrap 절차로 제한합니다. | 외부망 설정 누락 시 기동 거부, 토큰 원문 로그 부재 확인 | JY, TH |

반사 경로에는 LLM, RAG, 실시간 TTS를 추가하지 않습니다. 고위험 즉시 경보는 고정 클립과 햅틱만 사용하고, 중·저위험은 인지 경로로 전달합니다.

---

## 3. 2차 개선: 인지 경로와 RAG 정합성

| 작업 | 구현 방향 | 검증 방법 | 담당 영역 |
| --- | --- | --- | --- |
| 인지 경로 책임 확정 | Detection에서 risk.events를 발행하고 Consumer가 RAG·LangGraph·TTS를 수행하거나, 직접 호출 구조를 공식 설계로 변경합니다. 두 구조를 혼용하지 않습니다. | 이벤트 발행부터 TTS 출력까지 trace_id 기반 추적 | Backend, JH |
| 라벨 SSOT | 학습 YAML의 객체 29개·노면 4개를 단일 기준으로 지정합니다. | 모델, RAG, 콘솔, 문서의 클래스 표 대조 | TH, JH |
| Alias 정책 | kickboard→scooter, stairs/manhole/grating→caution처럼 데이터셋과 수칙 사이의 변환표를 명시합니다. | alias별 검색 회귀 테스트 | JH, RAG |
| 수칙 데이터 통합 | dummy guidance 템플릿 의존을 제거하고 safety_guidelines JSON을 수칙 원본으로 고정합니다. | 라벨별 Top-5 hit-rate 측정 및 E2E 통과 | JH, RAG |
| 이벤트 ID 개선 | deviceId-sessionId-frameSeq-stream 조합 또는 UUID로 reflex/cognitive 충돌을 제거합니다. | 동일 밀리초 이중 전송 테스트 | TH, Mobile |

---

## 4. 3차 개선: 품질 게이트와 DB 안정성

| 작업 | 구현 방향 | 완료 기준 |
| --- | --- | --- |
| Python 품질 오류 정리 | Ruff format 21개 파일, Ruff 225건, mypy 5건, Bandit 2건을 항목별로 처리합니다. | 전체 명령이 0으로 종료 |
| pytest 수집 안정화 | DB 엔진 생성을 lifespan 또는 dependency factory로 지연하고 SQLite fixture를 기본 주입합니다. | DB 환경변수 없는 CI에서도 테스트 수집 성공 |
| 트랜잭션 경계 정리 | Repository의 개별 commit을 제거하고 Service가 사용자·기기 생성 트랜잭션을 소유합니다. | 기기 생성 실패 시 사용자 롤백 테스트 통과 |
| CI 대상 확대 | dev, main, master push에 Python 검사, pytest, Client tsc, Console build, Markdown 링크, Compose config를 적용합니다. | dev push에서 동일 품질 게이트 실행 |

---

## 5. 4차 개선: 운영 콘솔과 문서

| 작업 | 구현 방향 | 완료 기준 |
| --- | --- | --- |
| SSE 계약 정리 | 실제 producer 이벤트와 데모·확장 이벤트를 분리하고 payload 필드를 API 문서에 고정합니다. | 콘솔 UI가 실제 이벤트만으로 상태 표시 |
| 로그 조회 API | detection_guidance_logs의 인증된 조회 endpoint와 pagination 계약을 추가합니다. | 운영 콘솔 테이블이 실데이터 표시 |
| 환경변수 단일 명세 | 코드, .env.example, environment_variables 문서를 일괄 대조합니다. | 누락·미사용·중복 변수 목록 0건 |
| 설계 원본 갱신 | Llava, Kokoro/Coqui, base64 MP3, expo-av 같은 구기술 표현을 실제 구현 기준으로 교체합니다. | 설계 문서와 현재 구현의 핵심 기술 일치 |
| 링크 검사 | 문서 이동으로 깨진 상대 링크를 일괄 수정하고 CI에 링크 검사를 추가합니다. | 감사 기준 177건 해소 |

---

## 6. 단계별 완료 판정

| 단계 | 현 상태 | 개선 완료 판정 |
| --- | --- | --- |
| 1 WebSocket | 구현도 높음 | 토큰·로그 보안 보완과 DB 실패 격리 |
| 2 카메라 캡처 | 구현됨 | Android 성능 및 이벤트 ID 충돌 해소 |
| 3 탐지·게이트 | 가중치 계약이 blocker | 실제 가중치 fail-closed와 위험도 SSOT |
| 4·5 RAG | 데이터는 있으나 검색 정합 미완 | 라벨·alias 통합과 E2E, hit-rate 통과 |
| 6 LangGraph | 구현 및 호출 존재 | Redis 또는 직접 호출 책임을 문서·코드에 동일 반영 |
| 7 TTS | 기본 구현 양호 | 반사 억제 정책과 timeout 문구 정리 |

---

## 7. 검증 제한과 운영 원칙

이 계획서는 Docker 이미지 빌드, GPU, Ollama, Redis, MariaDB, TMAP, Gemini 실연결 및 iOS 네이티브 빌드 결과를 포함하지 않습니다. 각 개선 항목은 코드 수정 후 단위 테스트, 통합 테스트, 실기기 또는 컨테이너 smoke 기록으로 별도 완료 처리해야 합니다.

P0 항목은 Mock 데모만으로 완료 처리하지 않습니다. 특히 반사 경로의 물리 분리와 사용자 안전에 영향을 주는 변경은 실제 가중치·위험 시나리오·재경보 조건까지 검증해야 합니다.
