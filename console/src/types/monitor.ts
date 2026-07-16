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
  // 이벤트 발생 시점 프레임 이미지 상대 경로 (서버 data/event_frames/ 기준).
  // NULL이면 이미지 미보존 (STT 이벤트, 저장 실패, 보존 기간 만료 등).
  frame_path: string | null;
  false_positive: boolean | null;
  // 스테이지별 처리 지연(ms) JSON 문자열. 반사 경로는 decode/inference/total만,
  // 인지 경로는 rag/llm/tts까지, STT 경로는 stt/llm/tts까지 포함한다(경유한 스테이지만 존재).
  latency_json: string | null;
  // 관리자 콘솔용 파이프라인 중간 텍스트(STT 전사, RAG, LLM/패스트레인 등).
  // REST 응답에서는 MariaDB JSON 컬럼 특성상 객체로 내려올 수 있어 string | object 허용.
  pipeline_debug_json: string | PipelineDebug | null;
  created_at: string;
}

// pipeline_debug_json 파싱 결과 - 경로별 디버그 텍스트 표시용.
export interface PipelineDebug {
  path?: "reflex" | "cognitive" | "stt";
  stt_transcript?: string;
  bridge_source?: string;
  generation_mode?: string;
  rag_query?: string;
  rag_context?: string;
  rag_results?: unknown[];
  llm_text?: string | null;
  template_text?: string;
  response_text?: string;
  response_skipped?: boolean;
  skip_reason?: string;
  llm_provider?: string;
  used_fast_lane?: boolean;
  fast_lane_cache_key?: string;
  l3_verified?: boolean;
  validation_errors?: string[];
  used_static_fallback?: boolean;
  retry_count?: number;
  used_fallback_llm?: boolean;
  clock_direction?: string;
  distance_class?: string;
  object_ko?: string;
  l1_risk_level?: string;
  pipeline_risk_hint?: string;
  detected_classes_ko?: string[];
  detections_summary?: Array<Record<string, unknown>>;
  surfaces_summary?: Array<Record<string, unknown>>;
  navigation_guidance?: string;
  is_departing?: boolean;
  is_departing_confirmed?: boolean;
  braille_direction?: string;
  l2_drafts?: string[];
  inference_ms?: number;
  alert_id?: string;
  clip?: string;
  direction?: string;
  class_name?: string;
  distance?: string;
  risk_level?: string;
  hit_count?: number;
  track_id?: string;
}

// latency_json 파싱 결과 - 콘솔에서만 쓰는 화면 표시용 타입.
export interface LatencyStages {
  decode_ms?: number;
  inference_ms?: number;
  rag_ms?: number;
  llm_ms?: number;
  tts_ms?: number;
  stt_ms?: number;
  db_save_ms?: number;
  total_ms?: number;
}

// server/detection/consumer.py._broadcast_latency_event / ws_router.py._process_stt_audio가
// /ws/console/live-feed로 실시간 푸시하는 레이턴시 이벤트. db_save_ms는 이 시점엔 아직
// 미확정이라 없다(REST 폴링된 DetectionGuidanceLogRow.latency_json에는 포함됨).
export interface LiveLatencyEvent {
  type: "latency_event";
  event_id: string | null;
  stream_type: "reflex" | "cognitive" | "unknown";
  latency: LatencyStages;
  ts: number;
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
  navigation_status?: "IDLE" | "WAITING_FOR_DESTINATION" | "NAVIGATING";
  awaiting_free_question?: boolean;
  awaiting_intent?: boolean;
}

export interface AudioValidationStatus {
  alert_id: string;
  is_valid: boolean;
  error_reasons: string[];
  ttfb_ms: number;
  sample_rate: number;
  channels: number;
  duration_sec: number;
  byte_size: number;
}

export interface CacheSuppressionStatus {
  suppressed_keys: string[];
  ttl_seconds: number;
  details?: Array<{
    key: string;
    device_id: string;
    alert_id: string;
    ttl_seconds: number;
  }>;
}

export interface AccessibilityValidationStatus {
  alert_id: string;
  is_valid: boolean;
  similarity_score: number;
  warnings: string[];
  details?: {
    guidance_text: string;
    synthesized_text: string;
    similarity_score: number;
    is_aligned: boolean;
    missing_directions: string[];
    warnings: string[];
  };
}

export interface LangsmithTraceStatus {
  from_node: string;
  to_node: string;
  latency_ms: number;
  project: string;
  enabled: boolean;
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
  // 신규 MCP 관제 검증 상태
  audio_validation?: AudioValidationStatus | null;
  cache_suppression?: CacheSuppressionStatus | null;
  accessibility_validation?: AccessibilityValidationStatus | null;
  langsmith_trace?: LangsmithTraceStatus | null;
}

// 회원 관리 화면(server/api/admin_member_router.py) 타입 - 서버 DTO와 필드 1:1.
export interface UserDeviceRow {
  device_id: number;
  user_id: number;
  device_uuid: string;
  platform: "ios" | "android" | "unknown";
  is_active: boolean;
}

export interface AppUserRow {
  user_id: number;
  name: string;
  phone: string;
  disability_severity: string;
  birth_date: string | null;
  guardian_phone: string | null;
  address: string | null;
  status: "active" | "inactive" | "deleted";
  devices: UserDeviceRow[];
  is_anonymous: boolean;
}

export interface MemberRegisterPayload {
  device_uuid: string;
  name: string;
  phone: string;
  disability_severity: string;
  birth_date?: string;
  guardian_phone?: string;
  address?: string;
}

// detected_objects_json 파싱 결과 - 반사/인지 경로 공용.
// 서버 consumer.py의 log_detections dict 구조와 1:1 매칭.
export interface TrackedObject {
  track_id?: string | null;
  class_name: string;
  hit_count?: number;
  direction?: string | null;
  risk_level?: string;
  confidence?: number;
  distance?: number;
  alert_id?: string;
  bbox?: { x: number; y: number; w: number; h: number };
}

// 발화 추적 타임라인 행 (DetectionGuidanceLogRow에서 파생하여 화면 표시용으로 가공).
// 한 로그 행에 여러 탐지 객체가 있을 수 있으나, 발화 추적에서는
// "대표 객체 1개(신뢰도 최대 또는 첫 번째)"를 기준으로 행을 구성한다.
export interface GuidanceTraceRow {
  log_id: number;
  detected_at: string;
  stream_type: "reflex" | "cognitive" | "unknown";
  track_id: string | null;
  class_name: string;
  hit_count: number;
  direction: string;
  risk_level: string;
  // 발화 트리거 원인 (화면 표시용 자동 추론):
  // "근접+연속히트" / "연속히트" / "접근" / "이탈" / "노면/기타"
  trigger_reason: string;
  tts_text: string;
}
