import { useEffect, useMemo, useState } from "react";

import type { MonitorEvent, MonitorState, RiskEvent } from "../types/monitor";

const DEFAULT_STREAM_URL = "http://localhost:8000/api/v1/monitor/stream";

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
      const parsed = JSON.parse(message.data) as MonitorEvent;
      applyEvent(parsed)
    }

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
        case "system_error":
          /*
           * 발표/면접 대응 포인트:
           * - system 계열 이벤트는 최신 상태성 데이터입니다.
           * - 위험 이벤트처럼 배열에 누적하지 않고, 현재 GPU/RTT/Queue 상태를 덮어씁니다.
           * - 이 방식은 대시보드 카드가 항상 최신 서버 상태만 보여주게 합니다.
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
    applyEvent({
      event_type: "connection_established",
      timestamp: new Date().toISOString(),
      payload: { status: "ok" },

    });
  }

  return {
    state,
    streamUrl: resolvedUrl,
    injectDemoEvents,
  };
}
