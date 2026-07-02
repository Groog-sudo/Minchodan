/**
 * Real Frame 디코더 (실기기 전용 유틸).
 * useCamera의 takePhoto 결과(base64 JPEG)를 TFLite 입력 텐서로 변환한다.
 * 시뮬레이터에서는 사용되지 않는다.
 */

import jpeg from "jpeg-js";

import { FRAME_SIZE } from "./frameProvider";

/**
 * base64 JPEG 문자열을 640x640x3 CHW 정규화 float32 텐서로 변환.
 * 입력 이미지가 640x640이 아니면 좌상단 기준 crop (중앙 crop 미적용, 단순화).
 */
export function decodeBase64JpegToChw(base64: string): Float32Array {
  try {
    const jpegBytes = base64ToUint8(base64);
    const decoded = jpeg.decode(jpegBytes, {
      useTArray: true,
      formatAsRGBA: true,
      tolerantDecoding: true,
    });
    return rgbaToChw(
      decoded.data as Uint8Array,
      decoded.width,
      decoded.height,
    );
  } catch (err) {
    console.error("[RealFrame] 디코딩 오류:", err);
    return new Float32Array(FRAME_SIZE * FRAME_SIZE * 3);
  }
}

function base64ToUint8(b64: string): Uint8Array {
  const bin = typeof globalThis.atob === "function"
    ? globalThis.atob(b64)
    : fallbackAtob(b64);
  const len = bin.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = bin.charCodeAt(i) & 0xff;
  }
  return bytes;
}

function fallbackAtob(b64: string): string {
  // RN 일부 환경 대비 최소 폴백 (Buffer 미사용).
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const clean = b64.replace(/[^A-Za-z0-9+/]/g, "");
  let out = "";
  for (let i = 0; i < clean.length; i += 4) {
    const c0 = chars.indexOf(clean[i]);
    const c1 = chars.indexOf(clean[i + 1]);
    const c2 = chars.indexOf(clean[i + 2]);
    const c3 = chars.indexOf(clean[i + 3]);
    const n = (c0 << 18) | (c1 << 12) | ((c2 >= 0 ? c2 : 0) << 6) | (c3 >= 0 ? c3 : 0);
    out += String.fromCharCode((n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff);
  }
  return out;
}

function rgbaToChw(rgba: Uint8Array, w: number, h: number): Float32Array {
  const useW = Math.min(w, FRAME_SIZE);
  const useH = Math.min(h, FRAME_SIZE);
  const plane = FRAME_SIZE * FRAME_SIZE;
  const out = new Float32Array(plane * 3);
  for (let y = 0; y < useH; y++) {
    for (let x = 0; x < useW; x++) {
      const srcIdx = (y * w + x) * 4;
      const dstIdx = y * FRAME_SIZE + x;
      out[dstIdx] = rgba[srcIdx] / 255; // R
      out[plane + dstIdx] = rgba[srcIdx + 1] / 255; // G
      out[plane * 2 + dstIdx] = rgba[srcIdx + 2] / 255; // B
    }
  }
  return out;
}
