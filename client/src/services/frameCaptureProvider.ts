/**
 * 카메라 프레임 캡처 계층 공통 인터페이스.
 * docs/mobile/ios_android_bifurcation_contract.md §4 기준 - 플랫폼별 구현은
 * frameCaptureProviderSelect.ios.ts / frameCaptureProviderSelect.android.ts로 물리 분리한다.
 */

import type { Camera, PhotoFile } from "react-native-vision-camera";
import * as FileSystem from "expo-file-system/legacy";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import type { StreamType } from "../types/detection";
import { audioEngine } from "./audioEngine";

export interface FrameData {
  float32: Float32Array;
  stream: StreamType;
  // CoreML 네이티브 브릿지 호출용 (RN 구 브릿지는 JSON 직렬화 가능 타입만 인자로 받으므로 base64 유지 필요)
  base64: string | null;
  // 서버 WS 전송용 raw JPEG 바이트 (base64 미경유, 바이너리 프레임으로 직접 전송)
  jpegBytes: Uint8Array | null;
}

export interface FrameCaptureController {
  /** true면 <Camera>가 frameProcessor(연속 스트림)로 구동돼야 한다. */
  readonly supportsStream: boolean;
  /** supportsStream이 true일 때만 값이 있다. <Camera frameProcessor={...}>에 그대로 전달한다. */
  readonly frameProcessor: unknown | undefined;
  /** 단발 촬영 기반 캡처 (supportsStream=false 플랫폼의 기본 경로, 또는 폴백용). */
  capturePhoto(stream: StreamType): Promise<FrameData | null>;
}

export interface FrameCaptureProviderParams {
  cameraRef: React.RefObject<Camera | null>;
  /** worklet(별도 JS 컨텍스트)에서 안전하게 최신 간격을 읽기 위한 SharedValue. */
  intervalSharedValue: { value: number };
  lastCaptureTsShared: { value: number };
  /** 스트림 경로가 프레임을 획득했을 때 호출하는 콜백 (반사+N번째 인지 재전달은 상위에서 처리). */
  onStreamFrameBase64: (base64: string) => void;
}

/**
 * takePhoto() 기반 캡처 (플랫폼 공통 로직). react-native-vision-camera의 단발 촬영
 * API는 iOS/Android 동일하므로 크롭·리사이즈 수학은 여기 한 곳에만 둔다. 플랫폼별로
 * 다른 파일 읽기 방식(예: Android의 File.bytes() 우회)만 각 platform select 파일에서
 * readJpegBytes로 주입한다.
 */
export async function captureViaTakePhoto(
  cameraRef: React.RefObject<Camera | null>,
  isCapturingRef: { current: boolean },
  stream: StreamType,
  readJpegBytes: (uri: string) => Promise<Uint8Array>,
): Promise<FrameData | null> {
  if (!cameraRef.current) {
    console.warn(`[Camera/Real] ${stream} 캡처 실패: cameraRef 없음`);
    return null;
  }
  if (isCapturingRef.current) {
    // 이미 캡처가 진행 중이면 중복 방지를 위해 즉시 무시 (drop)
    return null;
  }
  isCapturingRef.current = true;
  try {
    const photo: PhotoFile = await cameraRef.current.takePhoto({
      flash: "off",
      enableShutterSound: false,
    });
    const path = photo.path.startsWith("file://")
      ? photo.path
      : `file://${photo.path}`;

    // 카메라 미리보기(<Camera resizeMode="cover"> 기본값)는 종횡비를 유지한 채
    // 화면에 꽉 차도록 중앙 크롭하여 보여준다. 미리보기와 동일하게 중앙 정사각형
    // 크롭 후 리사이즈해야 bbox 좌표가 정합한다.
    //
    // photo.width/height는 EXIF PixelXDimension/Dimension(센서 원본, 항상 landscape
    // 배치) 기준이라 회전 반영 전 값이다. expo-image-manipulator는 크롭보다 먼저
    // ImageFixOrientationTransformer로 EXIF 회전을 이미지에 반영하므로, 세로로 촬영해
    // 90/270도 보정이 필요한 경우(orientation === landscape-left/right) 크롭 좌표계에서는
    // 가로/세로 축이 서로 뒤바뀐다. 이를 보정하지 않으면 크롭 영역이 이미지 경계를 벗어난다.
    const isRotated90 =
      photo.orientation === "landscape-left" ||
      photo.orientation === "landscape-right";
    const correctedWidth = isRotated90 ? photo.height : photo.width;
    const correctedHeight = isRotated90 ? photo.width : photo.height;
    const cropSize = Math.min(correctedWidth, correctedHeight);
    const originX = Math.floor((correctedWidth - cropSize) / 2);
    const originY = Math.floor((correctedHeight - cropSize) / 2);

    // expo-image-manipulator 기기 네이티브 GPU 가속 크롭/리사이징/압축 기동
    const manipResult = await manipulateAsync(
      path,
      [
        { crop: { originX, originY, width: cropSize, height: cropSize } },
        { resize: { width: 640, height: 640 } },
      ],
      { compress: 0.5, format: SaveFormat.JPEG, base64: true },
    );

    const base64 = manipResult.base64 ?? "";
    // 실기기 실행 시 JS CPU 100% 점유로 인한 iOS Watchdog SIGKILL (code 9) 차단을 위해 온디바이스 디코딩 루프 생략
    // (실기기에서는 서버로 raw JPEG 바이트만 전송하여 GPU 추론 서버에서 디코딩 및 검출을 전담 처리함)
    const float32 = new Float32Array(0);

    const jpegBytes = await readJpegBytes(manipResult.uri);

    if (!audioEngine.isGuidePlaying) {
      console.log(`[Camera/Real] ${stream} 프레임 압축완료: 원본경로=${path} -> JPEG bytes=${jpegBytes.length} base64len(CoreML용)=${base64.length} float32len=${float32.length}`);
    }

    // 디바이스 임시 스토리지 고갈 방지를 위해 촬영된 원본 및 리사이징 임시 파일 청소
    void FileSystem.deleteAsync(path, { idempotent: true }).catch(() => {});
    void FileSystem.deleteAsync(manipResult.uri, { idempotent: true }).catch(() => {});

    return { float32, stream, base64, jpegBytes };
  } catch (err) {
    console.error(`[Camera/Real] ${stream} 캡처 오류:`, err);
    return null;
  } finally {
    isCapturingRef.current = false;
  }
}

/** 기본 파일 읽기 구현: new File(uri).bytes() (iOS에서 정상 동작 확인됨). */
export async function readJpegBytesDefault(uri: string): Promise<Uint8Array> {
  const { File } = await import("expo-file-system");
  return await new File(uri).bytes();
}

/** base64 문자열을 Uint8Array로 변환한다. */
export function base64ToUint8(b64: string): Uint8Array {
  const bin = globalThis.atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i) & 0xff;
  return bytes;
}

export { useFrameCaptureProvider } from "./frameCaptureProviderSelect";
