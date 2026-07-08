import { useEffect, useMemo, useState } from "react";

import type {
  DetectionFeedItem,
  MonitorEvent,
  MonitorState,
  RiskEvent,
  SessionStatus,
} from "../types/monitor";

const DEFAULT_STREAM_URL = "http://localhost:8000/api/v1/monitor/stream";

/*
 * 실제 백엔드 코드 기준으로 직접 확인된 SSE 이벤트:
 * - server/api/monitor.py: connection_established, ping
 *
 * 그 외 system_metrics / risk_event / detection_event / llm_status 등은
 * 현재 콘솔 데모/확장 계약으로 해석해야 합니다.
 * 즉, 프론트 분기는 먼저 준비되어 있지만 producer 위치는 추가 확인이 필요합니다.
 */
const CONFIRMED_SSE_EVENTS = ["connection_established", "ping"] as const;

/*
 * 1차 MVP 콘솔에서 화면/데모를 위해 먼저 받아두는 확장 이벤트 묶음.
 * 실제 SSE producer가 아직 확정되지 않은 이벤트도 포함됩니다.
 * 단, system_status는 server/mcp/manager.py의 기본 fallback event_type이라
 * manager 기준으로는 실제 들어올 수 있는 이름입니다.
 */
const CONSOLE_DEMO_OR_EXTENDED_EVENTS = [
  "system_metrics",
  "gpu_status",
  "system_status",
  "system_error",
  "risk_event",
  "session_status",
  "detection_event",
  "llm_status",
  "rag_result",
  "tts_status",
  "stt_status",

] as const;

/*
 * 발표/면접 대응 포인트:
 * - 운영자 콘솔은 단말에 명령을 보내는 화면이 아니라 서버 상태를 "구독"하는 화면입니다.
 * - 그래서 양방향 WebSocket보다 서버 -> 브라우저 단방향 스트리밍인 SSE(EventSource)가 단순하고 적합합니다.
 * - WebSocket은 모바일 단말의 실시간 프레임 송수신에 쓰고, SSE는 관제 콘솔의 모니터링에 분리 적용합니다.
 */
const initialState: MonitorState = {
  connection: "disconnected",
  last_event_at: null,
  system: null,
  risks: [],
  sessions: [],
  detections: [],
  ai: null,
  raw_events: [],
};

export function useMonitorStream(streamUrl?: string) {
  /*
   * 발표/면접 대응 포인트:
   * - 기본값은 로컬 FastAPI 서버의 `/api/v1/monitor/stream`입니다.
   * - 배포나 팀원 PC 환경에서는 `VITE_MONITOR_STREAM_URL`로 서버 주소만 바꿔 재사용할 수 있습니다.
   * - URL을 코드 곳곳에 흩뿌리지 않고 이 훅 한 곳에서 결정해 유지보수를 쉽게 합니다.
   */
  const resolvedUrl = useMemo(
    () => streamUrl || import.meta.env.VITE_MONITOR_STREAM_URL || DEFAULT_STREAM_URL,
    [streamUrl],
  );
  const [state, setState] = useState<MonitorState>(initialState);

  /*
   * TH HARDCODE AREA 1: SSE 연결
   *
   * 여기부터는 담당자가 직접 작성합니다.
   *
   * 직접 구현할 것:
   * 1. useEffect 안에서 new EventSource(resolvedUrl) 생성 
   * 2. source.onopen에서 connection="connected" 처리
   * 3. source.onmessage에서 JSON.parse(message.data) 처리
   * 4. source.onerror에서 connection="error" 처리
   * 5. cleanup에서 source.close() 처리
   *
   * 발표 포인트:
   * - 관제 콘솔은 서버 상태를 단방향으로 구독하므로 WebSocket보다 SSE가 단순합니다.
   * - EventSource는 브라우저 기본 API라 별도 라이브러리 없이 실시간 수신이 가능합니다.
   */

  useEffect(() => {
    // 1. useEffect 안에서 new EventSource(resolvedUrl) 생성 
    setState((current) => ({
      ...current,
      connection: "connecting",
    }));

    /*
     * 발표/면접 대응 포인트:
     * - EventSource는 브라우저 내장 SSE 클라이언트입니다.
     * - 별도 라이브러리 없이 HTTP 연결을 유지하며 서버 이벤트를 계속 수신합니다.
     * - 연결 생성은 컴포넌트 생명주기에 맞춰 useEffect 안에서 한 번 수행합니다.
     */
    const source = new EventSource(resolvedUrl);
    
    // 2. source.onopen에서 connection="connected" 처리
    source.onopen = () => {
      /*
       * 발표/면접 대응 포인트:
       * - onopen은 SSE 연결이 실제로 열린 순간입니다.
       * - 이 값을 화면 상단 연결 상태 배지와 연결하면 관제자가 서버 연결 여부를 즉시 확인할 수 있습니다.
       */
      setState((current) => ({
        ...current,
        connection : "connected",
      }));
    };

    // 3. source.onmessage에서 JSON.parse(message.data) 처리
    source.onmessage = (message) => {
      /*
       * 발표/면접 대응 포인트:
       * - 백엔드 monitor.py는 SSE의 data 필드에 JSON 문자열을 실어 보냅니다.
       * - 여기서는 그 문자열을 MonitorEvent 계약으로 파싱한 뒤 applyEvent로 넘깁니다.
       * - 다음 개선 포인트는 try/catch를 추가해 파싱 실패도 system_error로 관측하는 것입니다.
       */


      try {
        const parsed = JSON.parse(message.data) as MonitorEvent;
        applyEvent(parsed);
      } catch (error) {
        applyEvent({
          event_type: "system_error",
          timestamp: new Date().toISOString(),
          payload: {
            error_message:
              error instanceof Error ? error.message : "SSE payload parse failed",
          },
        });
      }
    };

    // 4. source.onerror에서 connection="error" 처리
    source.onerror = () => {
      /*
       * 발표/면접 대응 포인트:
       * - SSE 연결 실패, 서버 중단, CORS 문제는 onerror로 들어옵니다.
       * - 콘솔은 장애 상황을 숨기지 않고 connection="error"로 표시해야 운영자가 즉시 알아챌 수 있습니다.
       */
      setState((current) => ({
        ...current ,
        connection : "error",
      }));
    };

    // 5. cleanup에서 source.close() 처리
    return () => {
      /*
       * 발표/면접 대응 포인트:
       * - React 컴포넌트가 unmount되거나 URL이 바뀌면 기존 SSE 연결을 반드시 닫아야 합니다.
       * - 닫지 않으면 브라우저에 오래된 연결이 남아 중복 이벤트와 메모리 누수가 발생할 수 있습니다.
       */
      source.close();

      setState((current) => ({
        ...current ,
        connection : "disconnected" ,
      }));
    };

  }, [resolvedUrl])

  /*
   * TH HARDCODE AREA 2: 이벤트 분기
   *
   * 직접 구현할 것:
   * - event.event_type === "system_metrics" 또는 "gpu_status"이면 system 덮어쓰기
   * - event.event_type === "risk_event"이면 risks 배열 앞에 누적
   * - event.event_type === "session_status"이면 device_id 기준으로 upsert
   * - event.event_type === "detection_event"이면 detections 배열 앞에 누적
   * - event.event_type === "llm_status" / "rag_result" / "tts_status" / "stt_status"이면 ai 상태 갱신
   *
   * 상태 관리 기준:
   * - 최신 상태성 데이터: system, ai
   * - 누적 로그성 데이터: risks, detections, raw_events
   * - 식별자 갱신 데이터: sessions
   */
  function applyEvent(event: MonitorEvent) {
    const payload = event.payload ?? {};
    const receivedAt = event.timestamp ?? new Date().toISOString(); // 단순화한 확장 ISO 형식(ISO 8601)의 문자열을 반환

    setState((current) => {
      /*
       * 발표/면접 대응 포인트:
       * - raw_events는 디버깅용 원본 이벤트 로그입니다.
       * - 모든 이벤트를 무한 저장하면 브라우저 메모리가 계속 늘어나므로 최근 40개만 유지합니다.
       * - 실제 운영 화면에서는 raw_events보다 system, risks, sessions처럼 목적별로 정규화한 상태를 사용합니다.
       */
      const raw_events = [event, ...current.raw_events].slice(0, 40);

      /*
       * 발표/면접 대응 포인트:
       * - CONFIRMED_SSE_EVENTS는 실제 backend SSE 코드에서 직접 확인된 이벤트 묶음입니다.
       * - CONSOLE_DEMO_OR_EXTENDED_EVENTS는 화면 선구현용 확장 이벤트 묶음입니다.
       * - 지금 switch는 두 범주를 함께 처리하지만, 해석은 동일선상에 두지 않는 것이 중요합니다.
       */
      switch(event.event_type){
        case "connection_established":
            /*
             * 발표/면접 대응 포인트:
             * - 백엔드 SSE 연결 직후 최초로 보내는 연결 확인 이벤트입니다.
             * - onopen은 브라우저 관점의 연결 성공이고, connection_established는 서버 애플리케이션 관점의 준비 완료입니다.
             */
            return {
              ...current,
              connection: "connected",
              last_event_at : receivedAt,
              raw_events,
            };

        case "ping":
            /*
             * 발표/면접 대응 포인트:
             * - ping은 실데이터가 없어도 SSE 연결을 유지하기 위한 keep-alive 이벤트입니다.
             * - 화면의 마지막 수신 시간만 갱신해서 연결이 살아 있음을 보여줍니다.
             */
            return {
              ...current,
              last_event_at : receivedAt,
              raw_events,
            };

        case "system_metrics": 
        case "gpu_status":
        case "system_status":
        case "system_error":
          /*
           * 발표/면접 대응 포인트:
           * - system 계열 이벤트는 최신 상태성 데이터입니다.
           * - 위험 이벤트처럼 배열에 누적하지 않고, 현재 GPU/RTT/Queue 상태를 덮어씁니다.
           * - 이 방식은 대시보드 카드가 항상 최신 서버 상태만 보여주게 합니다.
           * - 특히 system_status는 server/mcp/manager.py에서 event_type 누락 시 붙는 fallback 이름입니다.
           */
          return {
            ...current,
            last_event_at : receivedAt,
            raw_events,
            system: {
              gpu_usage_pct:
                typeof payload.gpu_usage_pct === "number"
                  ? payload.gpu_usage_pct 
                  : current.system?.gpu_usage_pct,
              // 메모리는 GPU 사용률과 다른 지표라 memory_used_mb 필드만 사용합니다.
              memory_used_mb:
                typeof payload.memory_used_mb === "number"
                  ? payload.memory_used_mb
                  : current.system?.memory_used_mb,
              current_provider:
                typeof payload.current_provider === "string"
                  ? payload.current_provider
                  : current.system?.current_provider,
              network_rtt_ms:
                typeof payload.network_rtt_ms === "number"
                  ? payload.network_rtt_ms
                  : current.system?.network_rtt_ms,
              queue_depth:
                typeof payload.queue_depth === "number"
                  ? payload.queue_depth
                  : current.system?.queue_depth,
              dropped_frames:
                typeof payload.dropped_frames === "number"
                  ? payload.dropped_frames
                  : current.system?.dropped_frames,
              last_error:
                typeof payload.error_message === "string"
                  ? payload.error_message
                  : current.system?.last_error,

            }, 
          };

          case "risk_event" : {
            /*
             * 발표/면접 대응 포인트:
             * - risk_event는 최신 상태가 아니라 사건 기록입니다.
             * - 따라서 system처럼 덮어쓰지 않고 배열 앞에 누적합니다.
             * - high 위험은 Reflex Path, mid/low는 Cognitive Path로 이어졌는지 나중에 이 로그로 검증할 수 있습니다.
             */
            // RiskEvent 타입을 명시해 risk_level이 정해진 네 값만 갖도록 고정합니다.
            const risk: RiskEvent = {
              id: `${payload.event_id ?? "risk"}-${receivedAt}`,
              event_id:
              typeof payload.event_id === "string"
                ? payload.event_id
                : "unknown",
              risk_level:
              payload.risk_level === "high" ||
              payload.risk_level === "mid" ||
              payload.risk_level === "low"
                ? payload.risk_level
                : "unknown",
              class_name:
                typeof payload.class_name === "string"
                  ? payload.class_name
                  : "unknown",
              confidence:
                typeof payload.confidence === "number"
                  ? payload.confidence
                  : undefined,
              direction:
                typeof payload.direction === "string"
                  ? payload.direction
                  : undefined,
              guidance_text:
                typeof payload.guidance_text === "string"
                  ? payload.guidance_text
                  : undefined,
              ts: receivedAt,
            };

            return {
              ...current,
              last_event_at: receivedAt,
              raw_events,
              risks: [risk, ...current.risks].slice(0, 80),
            };
          }

          case "session_status": {
            // device_id 기준으로 sessions 배열 upsert

            /*
            * 발표/면접 대응 포인트:
            * - 세션 상태는 로그처럼 계속 쌓는 데이터가 아니라 device_id 기준 최신 상태를 보여주는 데이터입니다.
            * - 같은 device_id가 다시 들어오면 기존 행을 갱신하고, 처음 보는 device_id면 새 행을 추가합니다.
            * - 이 패턴은 upsert라고 설명할 수 있습니다.
            * - SessionStatus["status"]로 타입을 고정한 이유는 connected/disconnected/unknown 외 문자열이 화면 상태에 섞이지 않게 하기 위해서입니다.
             */ 
            const device_id = 
                  typeof payload.device_id === "string"
                    ? payload.device_id 
                    : "unknown-device";

            const sessionsStatus: SessionStatus["status"] = 
                  payload.status === "connected" || payload.status === "disconnected"
                    ? payload.status
                    : "unknown"

            const session: SessionStatus =  {
              device_id: device_id,
              platform:
                typeof payload.platform === "string"
                ? payload.platform
                : undefined,
              status: sessionsStatus,
              rtt_ms:
              typeof payload.rtt_ms === "number"
                ? payload.rtt_ms
                : undefined,
              last_seen: receivedAt,
            };


            const exists = current.sessions.some(
              (item) => item.device_id === device_id
            );

            return {
              ...current,
              last_event_at: receivedAt,
              raw_events,
              sessions: exists
                ? current.sessions.map((item) => item.device_id === device_id ? session : item, )
                : [session, ...current.sessions],
            };
            // risk_event = 누적 로그라 배열 앞에 계속 추가
            // system_metrics = 최신 상태라 덮어쓰기
            // session_status = device_id 기준으로 있으면 갱신, 없으면 추가
          }

          case "detection_event": {
            // detections 배열 앞에 누적
            // detection_event는 텍스트 기반 DetectionFeed 1차 MVP
            // 실제 이미지/박스/마스크는 아직 2차
            // stream 값으로 reflex와 cognitive를 구분해서 이중 경로 흐름을 콘솔에서 볼 수 있음
            // 배열은 무한 증가 방지를 위해 최근 80개만 유지

            /* 
            * 발표 및 면접 대응 포인트:
            * - DetectionFeed는 1차 MVP에서 실제 카메라 이미지를 띄우지 않습니다.
            * - 대신 서버가 보내는 탐지 메타데이터(event_id, stream, class_name, confidence, inference_ms)를 먼저 표시합니다.
            * - stream이 reflex이면 반사 경로, cognitive이면 인지 경로로 흘러간 이벤트라 설명할 수 있습니다.
            * - 2차에서 이 event_id를 기준으로 썸네일, BBox, Segmentation Overlay를 붙일 수 있습니다.
            * - DetectionFeedItem["stream"]으로 타입을 고정해 reflex/cognitive/unknown 외 값이 화면에 섞이지 않게 막습니다.
            */
            const stream: DetectionFeedItem["stream"]  =
              payload.stream === "reflex" || payload.stream === "cognitive"
              ? payload.stream
              : "unknown";

            const detection : DetectionFeedItem = {
              id: `${payload.event_id ?? "detection" } ${ receivedAt }`,
              event_id :
                typeof payload.event_id === "string"
                    ?  payload.event_id 
                    : "unknown" ,
              device_id : 
                typeof payload.device_id === "string"
                    ? payload.device_id
                    : "unknown-device",
              stream,
              class_name:
                typeof payload.class_name === "string"
                  ? payload.class_name 
                  : "unknown",
              
              confidence : 
                typeof payload.confidence === "number"
                  ? payload.confidence 
                  : undefined ,
              
              inference_ms:
                typeof payload.inference_ms === "number"
                  ? payload.inference_ms 
                  : undefined ,

              surface :
                typeof payload.surface === "string"
                  ? payload.surface 
                  : "unknown" ,

              ts : receivedAt
            };

            return {
              ...current,
              last_event_at: receivedAt,
              raw_events,
              detections: [detection, ...current.detections].slice(0, 80)
              
            }
          }
          // 💡 [면접 대비 주석 - 프론트 주도 데모 계약]
          // Q. 백엔드에서 아직 안 쏴주는 이벤트(llm_status 등)를 프론트에서 먼저 정의한 이유는?
          // A. "애자일 개발을 위해 프론트-백엔드 간 '데모/확장 계약'을 먼저 체결했습니다.
          //    백엔드 Producer(6, 7단계)가 아직 없지만 프론트는 주입(Inject) 함수로 UI를 미리 검증할 수 있습니다."

          case "llm_status" : 
          case "rag_result" :
          case "tts_status" :
          // case "stt_status" : {  // ❌ STT는 7단계 파이프라인 범위 밖이므로 제외 (삭제)
          {
            /*
             * 발표/면접 대응 포인트:
             * - AI 파이프라인 상태는 누적 로그보다 최신 상태 확인이 중요합니다.
             * - LLM/RAG/TTS/STT 이벤트를 한 구역에 묶어 콘솔에서 불안한 AI 계층을 한눈에 점검하려는 구조입니다.
             * - 현재는 TH 하드코딩 1차 구간이라 raw_events와 last_event_at만 갱신하고, 다음 단계에서 ai 객체 필드를 직접 채웁니다.
             */

            /*
             * 발표/면접 대응 포인트:
             * - current.ai는 최초 상태에서 null일 수 있으므로 previousAi라는 빈 객체 fallback을 먼저 만듭니다.
             * - nextAi는 기존 AI 상태를 보존한 뒤, 이번 SSE 이벤트에 포함된 필드만 덮어쓴 결과입니다.
             * - 이렇게 분리하면 바깥 return의 ...current와 ai 내부 상태 보존이 서로 다른 계층이라는 점을 설명하기 쉽습니다.
             */
            const previousAi = current.ai ?? {};

            const nextAi = {
              ...previousAi,
              llm_provider:
                typeof payload.llm_provider === "string"
                  ? payload.llm_provider
                  : previousAi.llm_provider,
              rag_query:
                typeof payload.rag_query === "string"
                  ? payload.rag_query
                  : previousAi.rag_query,
              rag_score:
                typeof payload.rag_score === "number"
                  ? payload.rag_score
                  : previousAi.rag_score,
              tts_engine:
                typeof payload.tts_engine === "string"
                  ? payload.tts_engine
                  : previousAi.tts_engine,
              tts_status:
                typeof payload.tts_status === "string"
                  ? payload.tts_status
                  : previousAi.tts_status,
              stt_status:
                typeof payload.stt_status === "string"
                  ? payload.stt_status
                  : previousAi.stt_status,
              last_guidance:
                typeof payload.last_guidance === "string"
                  ? payload.last_guidance
                  : typeof payload.guidance_text === "string"
                    ? payload.guidance_text
                    : previousAi.last_guidance,
              reflex_bypass:
                typeof payload.reflex_bypass === "boolean"
                  ? payload.reflex_bypass
                  : previousAi.reflex_bypass,
              llm_verified:
                typeof payload.llm_verified === "boolean"
                  ? payload.llm_verified
                  : previousAi.llm_verified,
              llm_retry_count:
                typeof payload.llm_retry_count === "number"
                  ? payload.llm_retry_count
                  : previousAi.llm_retry_count,
            };

            return {
              ...current,
              last_event_at: receivedAt,
              raw_events,
              ai: nextAi,
              /*
              AI 파이프라인 상태는 위험 이벤트처럼 누적 로그가 아니라 최신 상태를 보는 목적입니다. LLM, RAG, TTS, STT는 각각 독립 이벤트로 들어올 수 있어서 
              기존 ai 상태를 펼친 뒤 들어온 필드만 갱신합니다. 그래서 한 이벤트가 들어와도 다른 필드가 사라지지 않습니다. 
              */ 
            };
          }
          default: 
            return {
              ...current,
              last_event_at: receivedAt,
              raw_events,
            };
         
      }
  // connection_established와 ping은 연결 상태 이벤트라 화면 상태만 갱신합니다.
  // system_metrics와 gpu_status는 최신 시스템 상태이므로 배열에 누적하지 않고 system 객체를 덮어씁니다.
  // raw_events는 디버깅용 원본 로그라 최근 40개만 유지합니다.
    });
  }

  /*
   * TH HARDCODE AREA 3: 샘플 이벤트 주입
   *
   * 백엔드 서버가 꺼져 있어도 발표 연습이 가능하도록,
   * 담당자가 직접 system_metrics, risk_event, session_status 샘플을 만들어 applyEvent에 넣습니다.
   */
  function injectDemoEvents() {
    /*
     * 발표/면접 대응 포인트:
     * - 아래 주입 이벤트는 CONSOLE_DEMO_OR_EXTENDED_EVENTS 화면 검증용 샘플입니다.
     * - connection_established만 실제 SSE 최초 연결 이벤트와 이름이 같고,
     *   나머지는 "현재 콘솔에서 이렇게 쓰고 있다"는 데모 계약으로 봐야 합니다.
     */
    applyEvent({
      event_type: "connection_established",
      timestamp: new Date().toISOString(),
      payload: { status: "ok" },
    });

    applyEvent({
      event_type: "system_metrics",
      timestamp: new Date().toISOString(),
      payload: {
        gpu_usage_pct: 41,
        memory_used_mb: 6144,
        current_provider: "ollama(gemma4-e4b)",
        network_rtt_ms: 74,
        queue_depth: 3,
        dropped_frames: 1,
      },
    });

    applyEvent({
      event_type: "session_status",
      timestamp: new Date().toISOString(),
      payload: {
        device_id: "ios-demo-01",
        platform: "ios",
        status: "connected",
        rtt_ms: 68,
      },
    });

    applyEvent({
      event_type: "detection_event",
      timestamp: new Date().toISOString(),
      payload: {
        event_id: "det-demo-001",
        device_id: "ios-demo-01",
        stream: "cognitive",
        class_name: "bollard",
        confidence: 0.93,
        inference_ms: 47,
        surface: "sidewalk",
      },
    });

    applyEvent({
      event_type: "risk_event",
      timestamp: new Date().toISOString(),
      payload: {
        event_id: "risk-demo-001",
        risk_level: "mid",
        class_name: "bollard",
        confidence: 0.93,
        direction: "left",
        guidance_text: "왼쪽 볼라드 우회",
      },
    });

    applyEvent({
      event_type: "llm_status",
      timestamp: new Date().toISOString(),
      payload: {
        llm_provider: "ollama(gemma4-e4b)",
        llm_verified: true,
        llm_retry_count: 0,
      },
    });

    applyEvent({
      event_type: "rag_result",
      timestamp: new Date().toISOString(),
      payload: {
        rag_query: "bollard avoidance",
        rag_score: 0.88,
        guidance_text: "왼쪽 볼라드 우회",
        reflex_bypass: true,
      },
    });

    applyEvent({
      event_type: "tts_status",
      timestamp: new Date().toISOString(),
      payload: {
        tts_engine: "piper",
        tts_status: "ok",
        last_guidance: "왼쪽 볼라드 우회",
      },
    });

    applyEvent({
      event_type: "stt_status",
      timestamp: new Date().toISOString(),
      payload: {
        stt_status: "idle",
      },
    });
  }

  return {
    state,
    streamUrl: resolvedUrl,
    injectDemoEvents,
  };
}
