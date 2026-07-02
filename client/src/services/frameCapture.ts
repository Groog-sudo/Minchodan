<<<<<<< HEAD
// client/src/services/frameCapture.ts
=======
/**
 * 프레임 캡처 및 전송 서비스.
 * 캡처한 base64 프레임을 detection 이벤트로 조립하여 WS 전송.
 * API 명세서 v0.2.0 기준 페이로드 구성.
 */

import { DEVICE_ID } from "../config";
import type { DetectionEvent, StreamType } from "../types/detection";

>>>>>>> dev
let frameCounter = 0;

export function generateEventId(): string {
  const ts = Date.now();
<<<<<<< HEAD
  const rand = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
  return `evt-${ts}-${rand}`;
}

export function buildDetectionEvent(base64: string, deviceId: string, stream: 'reflex' | 'cognitive') {
  frameCounter += 1;
  return {
    type: 'detection',
    payload: {
      event_id: generateEventId(),
      device_id: deviceId,
      timestamp: new Date().toISOString(),
      frame_id: frameCounter,
      stream: stream,
      thumbnail_jpeg_b64: base64,
      detections: [],
=======
  const rand = Math.floor(Math.random() * 1000)
    .toString()
    .padStart(3, "0");
  return `evt-${ts}-${rand}`;
}

export function buildDetectionEvent(
  base64: string,
  deviceId: string,
  stream: StreamType,
): DetectionEvent {
  frameCounter += 1;
  return {
    type: "detection",
    payload: {
      event_id: generateEventId(),
      device_id: deviceId,
      ts: Date.now(),
      frame_id: frameCounter,
      stream,
      thumbnail_jpeg_b64: base64,
>>>>>>> dev
    },
  };
}

<<<<<<< HEAD
export function sendFrame(base64: string, stream: 'reflex' | 'cognitive', deviceId: string, send: (data: object) => void) {
  // =========================================================================
  // 👨‍💻 담당자 직접 코딩 영역 시작 👨‍💻
  // 1. buildDetectionEvent 함수를 호출하여 event 객체를 만드세요.
  // 2. 전달받은 send() 함수를 이용해 event 객체를 서버로 전송하세요.
  // 3. console.log 를 찍어 프레임이 잘 전송되었는지 로깅해 보세요. (크기도 계산해보면 좋습니다: base64.length * 0.75 / 1024)
  // =========================================================================

  // 1. buildDetectionEvent 함수를 호출하여 event 객체를 만드세요.
  const event = buildDetectionEvent(base64, deviceId, stream);

  // 2. 전달받은 send() 함수를 이용해 event 객체를 서버로 전송하세요.
  send(event)

  // 3. 로깅
  const sizeKb = Math.round(base64.length * 0.75 / 1024);

  console.log(
    `[전송] stream=${stream}, frame_id=${event.payload.frame_id}, size=${sizeKb}KB`
  );
  // =========================================================================
  // 👨‍💻 담당자 직접 코딩 영역 끝 👨‍💻
  // =========================================================================
=======
export function sendFrame(
  base64: string,
  stream: StreamType,
  deviceId: string = DEVICE_ID,
  send: (data: object) => void,
): void {
  const event = buildDetectionEvent(base64, deviceId, stream);
  send(event);
  const sizeKB = Math.round((base64.length * 0.75) / 1024);
  console.log(
    `[Frame] stream=${stream}, frame_id=${frameCounter}, size≈${sizeKB}KB`,
  );
>>>>>>> dev
}
