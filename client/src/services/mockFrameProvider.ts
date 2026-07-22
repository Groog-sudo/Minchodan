/**
 * Mock Frame Provider (시뮬레이터 전용).
 * 카메라 하드웨어가 없는 iOS 시뮬레이터에서 번들된 샘플 JPEG를
 * TFLite 입력 텐서(640x640x3 CHW, 정규화 0~1)로 변환해 공급한다.
 *
 * 파이프라인:
 *   번들 JPEG --resolveAssetSource--> URI
 *          --fetch(base64 data URI fallback)--> Uint8Array
 *          --jpeg-js(useTArray)--> RGBA Uint8Array --normalize--> Float32Array CHW
 *
 * expo-file-system 의존 없음: 순수 fetch + atob 로만 동작 (Blob 미사용).
 * 디코딩은 샘플당 1회만 수행 후 캐시하여 재사용(반사 10fps + 인지 2fps 루프 대응).
 */

import { Image } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import jpeg from "jpeg-js";

import { FRAME_SIZE, type FrameProvider } from "./frameProvider";

const SAMPLE_REQUIRES: number[] = [
  require("../../assets/samples/frame_01_clear_sidewalk.jpg"),
  require("../../assets/samples/frame_02_obstacle_center_far.jpg"),
  require("../../assets/samples/frame_03_obstacle_center_near.jpg"),
  require("../../assets/samples/frame_04_obstacle_left_near.jpg"),
  require("../../assets/samples/frame_05_obstacle_right_near.jpg"),
];

export class MockFrameProvider implements FrameProvider {
  private index = 0;
  private lastDelivered: number = SAMPLE_REQUIRES[0];
  private readonly cache = new Map<number, Float32Array>();
  private readonly uris: (string | null)[] = SAMPLE_REQUIRES.map(() => null);
  // Base64 로컬 캐시: URI → base64 string (FileSystem 의존 없이 1회 다운로드 보관)
  private readonly b64Cache = new Map<string, string>();

  constructor() {
    SAMPLE_REQUIRES.forEach((req, i) => {
      const resolved = Image.resolveAssetSource(req);
      this.uris[i] = resolved?.uri ?? null;
    });
    console.log(
      `[MockFrameProvider] 샘플 ${SAMPLE_REQUIRES.length}장 로드. (카메라 Mock 모드)`,
    );
  }

  public getPreviewSource(): number {
    return this.lastDelivered;
  }

  public async getFrame(): Promise<Float32Array> {
    this.lastDelivered = SAMPLE_REQUIRES[this.index];
    const cached = this.cache.get(this.index);
    if (cached) {
      const out = cached;
      this.advance();
      return out;
    }

    const uri = this.uris[this.index];
    if (!uri) {
      console.warn("[MockFrameProvider] URI 해석 실패, 검은 프레임 반환");
      this.advance();
      return new Float32Array(FRAME_SIZE * FRAME_SIZE * 3);
    }

    try {
      const bytes = await this.fetchBytes(uri);
      const decoded = jpeg.decode(bytes, {
        useTArray: true,
        formatAsRGBA: true,
        tolerantDecoding: true,
      });
      const tensor = this.rgbaToHwc(
        decoded.data as Uint8Array,
        decoded.width,
        decoded.height,
      );
      this.cache.set(this.index, tensor);
      this.advance();
      return tensor;
    } catch (err) {
      console.error("[MockFrameProvider] 디코딩 오류:", err);
      this.advance();
      return new Float32Array(FRAME_SIZE * FRAME_SIZE * 3);
    }
  }

  private advance(): void {
    this.index = (this.index + 1) % SAMPLE_REQUIRES.length;
  }

  /**
   * URI 로부터 Uint8Array 바이트를 획득한다.
   * expo-file-system 을 사용하지 않고 FileSystem.readAsStringAsync 로
   * 로컬 번들 에셋을 Base64 로 읽은 뒤 atob 로 변환한다.
   * Metro 번들러 에셋 URI (http://localhost:8081/assets/...) 는
   * FileSystem.downloadAsync 없이 직접 읽을 수 없으므로
   * 최초 1회 FileSystem.downloadAsync(legacy) 로 캐시 디렉터리에 저장하고
   * 이후 FileSystem.readAsStringAsync(legacy) 로 Base64 추출 후 b64Cache 에 보관한다.
   * b64Cache 가 채워진 이후에는 FileSystem 호출 없이 atob 만 사용한다.
   */
  private async fetchBytes(uri: string): Promise<Uint8Array> {
    // 1. b64Cache 히트 시 FileSystem 호출 없이 즉시 변환
    const cached = this.b64Cache.get(uri);
    if (cached) {
      return this.base64ToUint8(cached);
    }

    // 2. 캐시 미스: legacy FileSystem 으로 1회만 다운로드 후 Base64 추출
    const filename = uri.split("/").pop()?.split("?")[0] ?? "temp.jpg";
    const localUri = (FileSystem.cacheDirectory ?? "") + filename;

    try {
      await FileSystem.downloadAsync(uri, localUri);
      const base64 = await FileSystem.readAsStringAsync(localUri, {
        encoding: FileSystem.EncodingType.Base64,
      });
      void FileSystem.deleteAsync(localUri, { idempotent: true });
      // b64Cache 에 저장해 이후 FileSystem 호출 차단
      this.b64Cache.set(uri, base64);
      return this.base64ToUint8(base64);
    } catch (err) {
      console.error("[MockFrameProvider] fetchBytes 오류:", err);
      throw err;
    }
  }

  /** Base64 문자열을 Uint8Array 로 변환 (atob 사용). */
  private base64ToUint8(base64: string): Uint8Array {
    const bin = atob(base64);
    const len = bin.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = bin.charCodeAt(i);
    }
    return bytes;
  }

  /**
   * RGBA Uint8Array(W x H)를 HWC float32(0~1 정규화)로 변환.
   * 입력이 640x640 이 아니면 좌상단 기준 crop.
   * 정규화: /255 (Ultralytics YOLO 표준, Python PT/TFLite 교차 검증 완료).
   */
  private rgbaToHwc(rgba: Uint8Array, w: number, h: number): Float32Array {
    if (w !== FRAME_SIZE || h !== FRAME_SIZE) {
      console.warn(
        `[MockFrameProvider] 샘플 해상도 ${w}x${h} != ${FRAME_SIZE}. 좌상단 crop 시도`,
      );
    }
    const useW = Math.min(w, FRAME_SIZE);
    const useH = Math.min(h, FRAME_SIZE);
    const out = new Float32Array(FRAME_SIZE * FRAME_SIZE * 3);

    for (let y = 0; y < useH; y++) {
      for (let x = 0; x < useW; x++) {
        const srcIdx = (y * w + x) * 4;
        const dstIdx = (y * FRAME_SIZE + x) * 3;
        out[dstIdx] = rgba[srcIdx] / 255;             // R (표준 정규화)
        out[dstIdx + 1] = rgba[srcIdx + 1] / 255;   // G
        out[dstIdx + 2] = rgba[srcIdx + 2] / 255; // B
      }
    }
    return out;
  }

  public dispose(): void {
    this.cache.clear();
    this.b64Cache.clear();
  }
}

export function createMockFrameProvider(): MockFrameProvider {
  return new MockFrameProvider();
}
