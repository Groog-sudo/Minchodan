/**
 * Real Frame 디코더 (실기기 전용 유틸).
 * 입력 포맷: NCHW [1, 3, 640, 640] float32, 값 범위 0~1 (정규화)
 * - iPhone 원본(4224x2376)을 중앙 crop 후 640x640 bilinear 리사이즈
 * - CHW 채널 우선 배치 (R plane, G plane, B plane 순)
 * - 정규화: /255 (Ultralytics YOLO 표준, Python PT/TFLite 교차 검증 완료)
 *   주: /5 는 bus.jpg 교차 검증에서 탐지 품질 저하를 일으켜 제거함.
 */

import jpeg from "jpeg-js";

const FRAME_SIZE = 640;

export function decodeBase64JpegToChw(base64: string): Float32Array {
  try {
    const jpegBytes = base64ToUint8(base64);
    const decoded = jpeg.decode(jpegBytes, {
      useTArray: true,
      formatAsRGBA: true,
      tolerantDecoding: true,
    });
    const { data, width: w, height: h } = decoded;
    const cropSize = Math.min(w, h);
    const cropX = Math.floor((w - cropSize) / 2);
    const cropY = Math.floor((h - cropSize) / 2);
    return bilinearResizeCHW(data as Uint8Array, w, cropX, cropY, cropSize);
  } catch (err) {
    console.error("[RealFrame] 디코딩 오류:", err);
    return new Float32Array(FRAME_SIZE * FRAME_SIZE * 3);
  }
}

/**
 * RGBA → center crop → bilinear 640x640 → CHW float32
 * CHW: [R(640x640), G(640x640), B(640x640)]
 */
function bilinearResizeCHW(
  rgba: Uint8Array,
  srcW: number,
  cropX: number,
  cropY: number,
  cropSize: number,
): Float32Array {
  const dst = FRAME_SIZE;
  const plane = dst * dst;
  const out = new Float32Array(plane * 3); // CHW
  const scale = cropSize / dst;

  for (let dy = 0; dy < dst; dy++) {
    for (let dx = 0; dx < dst; dx++) {
      const sx = cropX + dx * scale;
      const sy = cropY + dy * scale;
      const x0 = Math.floor(sx);
      const y0 = Math.floor(sy);
      const x1 = Math.min(x0 + 1, cropX + cropSize - 1);
      const y1 = Math.min(y0 + 1, cropY + cropSize - 1);
      const fx = sx - x0;
      const fy = sy - y0;

      const i00 = (y0 * srcW + x0) * 4;
      const i10 = (y0 * srcW + x1) * 4;
      const i01 = (y1 * srcW + x0) * 4;
      const i11 = (y1 * srcW + x1) * 4;

      const dstPx = dy * dst + dx;
      for (let c = 0; c < 3; c++) {
        const v =
          rgba[i00 + c] * (1 - fx) * (1 - fy) +
          rgba[i10 + c] * fx * (1 - fy) +
          rgba[i01 + c] * (1 - fx) * fy +
          rgba[i11 + c] * fx * fy;
        out[plane * c + dstPx] = v / 255; // CHW, Ultralytics 표준 정규화 (0~1)
      }
    }
  }
  return out;
}

function base64ToUint8(b64: string): Uint8Array {
  const bin =
    typeof globalThis.atob === "function"
      ? globalThis.atob(b64)
      : fallbackAtob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i) & 0xff;
  return bytes;
}

function fallbackAtob(b64: string): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const clean = b64.replace(/[^A-Za-z0-9+/]/g, "");
  let out = "";
  for (let i = 0; i < clean.length; i += 4) {
    const c0 = chars.indexOf(clean[i]);
    const c1 = chars.indexOf(clean[i + 1]);
    const c2 = chars.indexOf(clean[i + 2]);
    const c3 = chars.indexOf(clean[i + 3]);
    const n =
      (c0 << 18) | (c1 << 12) |
      ((c2 >= 0 ? c2 : 0) << 6) |
      (c3 >= 0 ? c3 : 0);
    out += String.fromCharCode((n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff);
  }
  return out;
}
