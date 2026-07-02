/**
 * 프레임 캡처 및 전송 서비스.
 * 캡처한 base64 프레임을 detection 이벤트로 조립하여 WS 전송.
 * API 명세서 v0.2.0 기준 페이로드 구성.
 */

import { DEVICE_ID } from "../config";
import type { DetectionEvent, StreamType } from "../types/detection";

let frameCounter = 0;

export function generateEventId(): string {
  const ts = Date.now();
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
    },
  };
}

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
}
