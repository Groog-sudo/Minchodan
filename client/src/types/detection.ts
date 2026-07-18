/**
 * WebSocket 메시지 및 탐지 이벤트 타입 정의.
 * API 명세서 v0.2.0 기준.
 */

export type WSStatus = "connecting" | "connected" | "disconnected" | "fallback";

export type StreamType = "reflex" | "cognitive";

export type Direction = "front" | "left" | "right" | "stop";

export type RiskLevel = "high" | "mid" | "low";

export type HapticPattern = "short" | "double" | "continuous" | "light";

export type MessageType =
  | "hello"
  | "welcome"
  | "auth_ok"
  | "heartbeat"
  | "heartbeat_ack"
  | "detection"
  | "ack"
  | "reflex_alert"
  | "reflex_clear"
  | "guide"
  | "error"
  | "server_detection"
  | "network_probe_ack"
  | "nav_route"
  | "dial_action";

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ServerDetectionResult {
  model: "object_detection" | "segmentation";
  className: string;
  confidence: number;
  bbox: BBox;
  distanceMeters?: number | null;
  distanceSource?: "lidar" | "heuristic" | "none";
  depthSampleCount?: number;
  depthAccuracy?: "absolute" | "relative";
}

export interface WSMessage {
  type: MessageType;
  device_id?: string;
  token?: string;
  session_id?: string;
  server_time?: string;
  ts?: number;
  payload?: DetectionPayload | AckPayload | Record<string, unknown>;
  event_id?: string;
  frame_id?: number;
  // 서버 ack 메시지는 decode_ms를 payload가 아닌 최상위 필드로 전송한다 (server/api/ws_router.py 참조)
  decode_ms?: number;
  alert_id?: string;
  direction?: Direction;
  risk_level?: RiskLevel;
  clip?: string;
  haptic?: boolean;
  panning?: number;
  distance?: number;
  beep_interval_ms?: number;
  haptic_pattern?: HapticPattern | string;
  /** 2026-07-18 거리 정책 SSOT: reflex_alert/reflex_clear 출처 구분 (server/detection/schemas.py ReflexAlert.alert_source와 동일 값). */
  alert_source?: "object" | "head_level" | "surface" | string;
  /** reflex_alert 전용: Near episode 상태("enter"=새 episode 시작, "update"=같은 episode 지속). */
  event_state?: "enter" | "update" | string;
  /** reflex_alert 전용: distance_policy 파생 거리(m). 레거시 distance 필드와 동일 값. */
  estimated_distance_m?: number;
  /** reflex_alert/reflex_clear 공통: 서버·단말 정책 버전 불일치 감지용. */
  policy_version?: string;
  /** reflex_clear 전용: 해제 대상 track_id (surface 등 track이 없으면 null). */
  track_id?: string | null;
  /** reflex_clear 전용: 해제 사유 ("zone_exit" | "track_lost"). */
  reason?: string;
  guidance_text?: string;
  /** guide 구조화 필드 (Phase 2): 시계 방향. 음성 텍스트와 분리. */
  clock_direction?: string;
  /** guide 구조화 필드: near/medium/far (반사 reflex_alert의 미터 distance와 별개). */
  distance_class?: "near" | "medium" | "far" | string;
  /** guide 구조화 필드: 한국어 주 탐지 객체명. */
  object_ko?: string;
  /** guide 오디오 전송 방식. "binary"면 이 메시지 직후 WS 바이너리 프레임으로 WAV 원본이 이어진다(2026-07-09 도입). */
  transport?: "binary" | "none";
  duration_ms?: number;
  /** network_probe_ack 메시지: 앱/스크립트에서 보낸 probe 식별자 */
  probe_id?: string;
  /** network_probe_ack 메시지: probe 페이로드 크기 */
  payload_bytes?: number;
  /** network_probe_ack 메시지: 서버 수신 시각(epoch ms) */
  server_received_ts?: number;
  /** network_probe_ack 메시지: 서버 송신 시각(epoch ms) */
  server_sent_ts?: number;
  detections?: ServerDetectionResult[];
  /** nav_route 메시지: 하단 지도 패널의 경로 폴리라인용 좌표 목록 (빈 배열 = 경로 해제) */
  waypoints?: { lat: number; lon: number }[];
  /** nav_route 메시지: TMap JS API appKey (서버 환경변수 재사용) */
  app_key?: string;
  /** dial_action: 전화 연결 대상 */
  contact_name?: string;
  phone_number?: string;
  delay_ms?: number;
}

export interface DetectionPayload {
  event_id: string;
  device_id: string;
  ts: number;
  frame_id: number;
  stream: StreamType;
  thumbnail_jpeg_b64: string;
}

export interface AckPayload {
  event_id: string;
  frame_id: number;
  decode_ms: number;
}

export interface DetectionEvent {
  type: "detection";
  payload: DetectionPayload;
}

export interface AlertReflexPayload {
  event_id: string;
  alert_id: string;
  direction: Direction;
  risk_level: "high";
  clip: string;
  haptic: boolean;
  panning?: number;
  distance?: number;
  beep_interval_ms?: number;
  haptic_pattern?: HapticPattern | string;
  ts: number;
}

export interface GuidePayload {
  event_id: string;
  risk_level: "mid" | "low";
  guidance_text: string;
  clock_direction?: string;
  distance_class?: "near" | "medium" | "far" | string;
  object_ko?: string;
  transport?: "binary" | "none";
  duration_ms?: number;
  ts: number;
}
