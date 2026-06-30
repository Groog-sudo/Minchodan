// client/src/services/frameCapture.ts
let frameCounter = 0;

export function generateEventId(): string {
  const ts = Date.now();
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
    },
  };
}

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
}
