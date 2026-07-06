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
