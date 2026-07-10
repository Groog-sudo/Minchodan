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
  | "guide"
  | "error"
  | "server_detection";

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
  guidance_text?: string;
  audio_mp3_b64?: string;
  duration_ms?: number;
  detections?: ServerDetectionResult[];
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
  audio_mp3_b64?: string;
  duration_ms?: number;
  ts: number;
}
