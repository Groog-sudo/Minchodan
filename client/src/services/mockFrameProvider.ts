/**
 * Mock Frame Provider (시뮬레이터 전용).
 * 카메라 하드웨어가 없는 iOS 시뮬레이터에서 번들된 샘플 JPEG를
 * TFLite 입력 텐서(640x640x3 CHW, 정규화 0~1)로 변환해 공급한다.
 *
 * 파이프라인:
 *   번들 JPEG --resolveAssetSource--> URI --fetch+blob--> ArrayBuffer
 *          --jpeg-js(useTArray)--> RGBA Uint8Array --normalize--> Float32Array CHW
 *
 * 디코딩은 샘플당 1회만 수행 후 캐시하여 재사용(반사 10fps + 인지 2fps 루프 대응).
 */

import { Image } from "react-native";
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

  constructor() {
    SAMPLE_REQUIRES.forEach((req, i) => {
      const resolved = Image.resolveAssetSource(req);
      this.uris[i] = resolved?.uri ?? null;
    });
    console.log(
      `[MockFrameProvider] 샘플 ${SAMPLE_REQUIRES.length}장 로드. (카메라 Mock 모드)`,
    );
  }

  /** 가장 최근에 전달한 프레임의 preview용 require id 반환. */
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
      const tensor = this.rgbaToChw(
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

  private async fetchBytes(uri: string): Promise<Uint8Array> {
    const resp = await fetch(uri);
    const blob = await resp.blob();
    const ab = await blob.arrayBuffer();
    return new Uint8Array(ab);
  }

  /**
   * RGBA Uint8Array(640x640)를 CHW float32(정규화 0~1)로 변환.
   * 입력 크기가 640이 아니면 좌상단 기준 crop/pad 없이 에러 로그 후 검은 텐서.
   */
  private rgbaToChw(
    rgba: Uint8Array,
    w: number,
    h: number,
  ): Float32Array {
    if (w !== FRAME_SIZE || h !== FRAME_SIZE) {
      console.warn(
        `[MockFrameProvider] 샘플 해상도 ${w}x${h} ≠ ${FRAME_SIZE}. 좌상단 crop 시도`,
      );
    }
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

  public dispose(): void {
    this.cache.clear();
  }
}

export function createMockFrameProvider(): MockFrameProvider {
  return new MockFrameProvider();
}
