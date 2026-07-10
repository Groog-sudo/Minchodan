export type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

export interface MonitorEvent {
  event_type: string;
  timestamp?: string;
  status?: string;
  payload?: Record<string, unknown>;
}

export interface SystemMetrics {
  gpu_usage_pct?: number;
  memory_used_mb?: number;
  current_provider?: string;
  network_rtt_ms?: number;
  queue_depth?: number;
  dropped_frames?: number;
  last_error?: string;
}

export interface RiskEvent {
  id: string;
  event_id: string;
  risk_level: "high" | "mid" | "low" | "unknown";
  class_name: string;
  confidence?: number;
  direction?: string;
  guidance_text?: string;
  ts: string;
}

export interface SessionStatus {
  device_id: string;
  platform?: string;
  status: "connected" | "disconnected" | "unknown";
  rtt_ms?: number;
  last_seen?: string;
}

export interface DetectionFeedItem {
  id: string;
  event_id: string;
  device_id: string;
  stream: "reflex" | "cognitive" | "unknown";
  class_name: string;
  confidence?: number;
  inference_ms?: number;
  surface?: string;
  ts: string;
}

// 발표/면접 포인트:
// - DetectionGuidanceLogRow는 detection_guidance_logs 테이블/응답 컬럼 구조를
//   React에서 그대로 받기 위한 최소 타입입니다.
// - 지금 단계에서는 화면 가공용 별도 DTO를 만들지 않고,
//   백엔드 컬럼명과 1:1로 맞춰 추후 조회 API 연결 시 수정 범위를 줄입니다.
export interface DetectionGuidanceLogRow {
  log_id: number;
  event_id: string | null;
  user_id: number | null;
  device_id: number | null;
  detected_at: string;
  stream_type: "reflex" | "cognitive" | "unknown";
  detected_objects_json: string;
  tts_text: string;
  created_at: string;
}

export interface AiPipelineStatus {
  reflex_bypass?: boolean;
  llm_provider?: string;
  llm_verified?: boolean;
  llm_retry_count?: number;
  last_guidance?: string;
  rag_query?: string;
  rag_score?: number;
  tts_engine?: string;
  tts_status?: string;
  stt_status?: string;
}

export interface MonitorState {
  connection: ConnectionState;
  last_event_at: string | null;
  system: SystemMetrics | null;
  risks: RiskEvent[];
  sessions: SessionStatus[];
  detections: DetectionFeedItem[];
  ai: AiPipelineStatus | null;
  raw_events: MonitorEvent[];
}
