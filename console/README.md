# Minchodan Operator Console

> **작성일**: 2026-07-06
> **버전**: v0.1.0

---

## 목적

React 기반 운영자 관제 콘솔입니다. 1차 MVP는 백엔드 SSE 엔드포인트(`/api/v1/monitor/stream`)를 구독하여 시스템 메트릭, 위험 이벤트, 단말 세션, 탐지 메타데이터를 표시합니다.

---

## 실행

```powershell
cd console
npm install
npm run dev
```

기본 SSE 주소는 `http://localhost:8000/api/v1/monitor/stream`입니다.
다른 서버를 사용할 경우 `.env`에 다음 값을 설정합니다.

```txt
VITE_MONITOR_STREAM_URL=http://localhost:8000/api/v1/monitor/stream
```

---

## TH 하드코딩 기준

이번 콘솔 작업은 **TH 하드코딩 80% / AI 보조 20%**를 기준으로 진행합니다.

| 구분 | 담당 | 설명 |
| --- | --- |
| 프로젝트 설정 | AI | Vite, TypeScript, 폴더 구조, 빌드 스크립트 |
| 기본 레이아웃 | AI | 화면 배치와 최소 CSS |
| SSE 연결 | TH | `EventSource` 생성, onopen/onmessage/onerror/cleanup |
| 이벤트 분기 | TH | `event_type` 기준 switch 분기 |
| 상태 관리 | TH | system 덮어쓰기, risks/detections 누적, sessions upsert |
| 테이블 렌더링 | TH | RiskEventLog, SessionStatus, DetectionFeed 직접 구현 |
| 발표 설명 | TH | SSE를 쓰는 이유와 상태 분리 기준 설명 |

---

## 직접 작성 우선 파일

| 파일 | TH 직접 작성 내용 |
| --- | --- |
| `src/api/useMonitorStream.ts` | `EventSource` 연결, `event_type` 분기, React 상태 업데이트 |
| `src/components/RiskEventLog.tsx` | 위험 이벤트 누적 테이블 |
| `src/components/SessionStatus.tsx` | 단말 연결 상태 목록 |
| `src/components/SystemMetrics.tsx` | GPU/RTT/Queue 카드 |
| `src/components/DetectionFeed.tsx` | 탐지 메타데이터 목록 |

---

## 1차 MVP 범위

| 화면 | 상태 |
| --- | --- |
| SSE 연결 상태 | 구현 완료 |
| SystemMetrics 카드 | 구현 완료 |
| RiskEventLog 테이블 | 구현 완료 |
| SessionStatus 단말 목록 | 구현 완료 |
| DetectionFeed 텍스트 메타데이터 | 구현 완료 |
| AI Pipeline Monitor | 구현 완료 |
| 샘플 이벤트 주입 버튼 | 구현 완료 |

---

## 현재 상태

| 항목 | 설명 |
| --- | --- |
| 1차 화면 구성 | 운영자 콘솔 5개 패널과 SSE 연결 상태 라인이 동작합니다. |
| 샘플 시연 | 백엔드가 꺼져 있어도 버튼 한 번으로 각 패널을 채워 발표/데모가 가능합니다. |
| 실데이터 연동 | `/api/v1/monitor/stream` 구독 구조는 연결되어 있으나, 실제 SSE 이벤트명과 payload 필드는 최종 정합 검증이 남아 있습니다. |
| 하드코딩 원칙 | `useMonitorStream.ts`의 이벤트 분기와 상태 설계는 TH 직접 설명 가능 영역으로 유지합니다. |

---

## 백엔드 이벤트 근거

| 콘솔 이벤트 | 현재 코드 근거 | 상태 |
| --- | --- | --- |
| `connection_established` | `server/api/monitor.py`에서 SSE 연결 직후 직접 전송 | 실제 확인 |
| `ping` | `server/api/monitor.py`에서 1초 timeout keep-alive로 직접 전송 | 실제 확인 |
| `gpu_status` 등 MCP 메트릭 | `server/mcp/manager.py`가 Redis Stream `mcp:metrics`의 `event_type`을 중계 | producer 추가 확인 필요 |
| `risk_event`, `detection_event` | `useMonitorStream.ts` 데모 이벤트 및 화면 확장 계약 | 실제 SSE producer 추가 확인 필요 |
| `llm_status`, `rag_result`, `tts_status`, `stt_status` | `useMonitorStream.ts` 데모 이벤트 및 AI Pipeline Monitor 표시 계약 | 실제 SSE producer 추가 확인 필요 |

`server/api/ws_router.py`와 `server/detection/consumer.py` 기준 실제 단말 WebSocket 메시지는 `welcome`, `auth_ok`, `ack`, `reflex_alert`, `guide`가 확인됩니다. 이 메시지는 모바일 단말용 WS 계약이며, 현재 콘솔 SSE 이벤트명과는 별도입니다.

---

## 2차 범위

| 기능 | 필요 조건 |
| --- | --- |
| 실제 카메라 프레임 썸네일 | 백엔드 썸네일 이벤트 또는 별도 이미지 API |
| BBox / Segmentation 오버레이 | 좌표 및 마스크 메타데이터 SSE 계약 |
| RTT / inference_ms 그래프 | 시계열 이벤트 누적 및 차트 컴포넌트 |
