<<<<<<< HEAD
// client/src/hooks/useCamera.ts
import { useEffect, useRef, useCallback, useState } from 'react';
import { sendFrame } from '../services/frameCapture';
// import { Camera, useCameraDevice, useCameraPermission, PhotoFile } from 'react-native-vision-camera'; // 실제 RN 환경에서 주석 해제

export function useCamera(reflexFps: number = 10, cognitiveFps: number = 2) {
  // 모의 RN 환경 변수 (실제 기기 배포 전 테스트용 스캐폴딩)
  const hasPermission = true;
  const requestPermission = () => { };
  const device = {};
  const cameraRef = useRef<any>(null);

  const reflexTimerRef = useRef<any>(null);
  const cognitiveTimerRef = useRef<any>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  // 권한 요청
  useEffect(() => {
    if (!hasPermission) requestPermission();
  }, [hasPermission, requestPermission]);

  // 프레임 캡처 함수 (내부 동작은 Vibe로 처리)
  const captureFrame = useCallback(async (stream: 'reflex' | 'cognitive'): Promise<string | null> => {
    // 실제 카메라 캡처 로직 (임시로 더미 base64 문자열 반환)
    return "dummy_base64_string_representing_jpeg_image";
  }, []);

  const startCapture = useCallback((deviceId: string, sendFn: (data: object) => void) => {
    if (isCapturing) return;
    setIsCapturing(true);

    const reflexInterval = Math.floor(1000 / reflexFps);
    const cognitiveInterval = Math.floor(1000 / cognitiveFps);

    console.log(`[캡처] 이중 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`);

    // =========================================================================
    // 👨‍💻 담당자 직접 코딩 영역 시작 👨‍💻
    // [면접 대비 포인트] UI 스레드를 방해하지 않고 비동기 타이머를 어떻게 분리할 것인가?
    // 1. reflexTimerRef.current 에 setInterval을 할당하세요. 
    //    내부에서 captureFrame('reflex') 을 호출하고 결과값이 있으면 sendFrame()으로 보내세요.
    // 2. cognitiveTimerRef.current 도 동일하게 setInterval을 할당하세요. ('cognitive')
    // =========================================================================

    // 1. 반사 스트림 (8~10fps) 타이머 시작 
    reflexTimerRef.current = setInterval(async () => {
      const frame = await captureFrame('reflex');
      if (frame) {
        sendFrame(frame, 'reflex', deviceId, sendFn);
      }   // 실제로는 sendFrame 연동 (지금은 스케폴드)
    }, reflexInterval);


    // 2. 인지 스트림 (1~2fps) 타이머 시작
    cognitiveTimerRef.current = setInterval(async () => {
      const frame = await captureFrame('cognitive');
      if (frame) {
        sendFrame(frame, 'cognitive', deviceId, sendFn);
      }
    }, cognitiveInterval);

    // =========================================================================
    // 👨‍💻 담당자 직접 코딩 영역 끝 👨‍💻
    // =========================================================================
  }, [reflexFps, cognitiveFps, isCapturing, captureFrame]);

  const stopCapture = useCallback(() => {
    // =========================================================================
    // 👨‍💻 담당자 직접 코딩 영역 시작 👨‍💻
    // [면접 대비 포인트] 메모리 누수 방지(클린업) 처리
    // timerRef에 값이 있다면 clearInterval()로 타이머를 해제하고, null로 초기화하세요.
    // =========================================================================
=======
/**
 * 이중 캡처 타이머 훅.
 * 후면 카메라에서 반사(10fps)/인지(2fps) 스트림을 분리 캡처.
 * react-native-vision-camera v4 API 사용 (takePhoto + expo-file-system base64).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  type CameraDevice,
  type PhotoFile,
  useCameraDevice,
  useCameraPermission,
  useCameraDevices,
} from "react-native-vision-camera";
import * as FileSystem from "expo-file-system/legacy";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import type { StreamType } from "../types/detection";

export interface UseCameraReturn {
  cameraRef: React.RefObject<Camera | null>;
  device: CameraDevice | undefined;
  hasPermission: boolean;
  permissionStatus: string;
  isCapturing: boolean;
  startCapture: (
    onFrame: (base64: string, stream: StreamType) => void,
  ) => void;
  stopCapture: () => void;
  requestCameraPermission: () => Promise<boolean>;
}

export function useCamera(
  reflexFps: number = REFLEX_FPS,
  cognitiveFps: number = COGNITIVE_FPS,
): UseCameraReturn {
  const { hasPermission, requestPermission } = useCameraPermission();
  const backDevice = useCameraDevice("back");
  const allDevices = useCameraDevices();
  const device = backDevice || allDevices[0];
  const cameraRef = useRef<Camera | null>(null);
  const reflexTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cognitiveTimerRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const onFrameRef = useRef<
    ((base64: string, stream: StreamType) => void) | null
  >(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionRequested, setPermissionRequested] = useState(false);

  const requestCameraPermission = useCallback(async (): Promise<boolean> => {
    console.log("[Camera] 권한 요청 시작");
    const granted = await requestPermission();
    console.log("[Camera] 권한 요청 결과:", granted);
    setPermissionRequested(true);
    return granted;
  }, [requestPermission]);

  useEffect(() => {
    if (!hasPermission && !permissionRequested) {
      console.log("[Camera] 권한 없음, 자동 요청");
      requestCameraPermission();
    }
    console.log("[Camera] 상태 - hasPermission:", hasPermission, "device:", device?.id ?? "undefined", "allDevices:", allDevices.length);
  }, [hasPermission, permissionRequested, device, allDevices.length, requestCameraPermission]);

  const captureFrame = useCallback(
    async (stream: StreamType): Promise<string | null> => {
      if (!cameraRef.current) {
        console.warn(`[Camera] ${stream} 캡처 실패: cameraRef 없음`);
        return null;
      }
      try {
        const photo: PhotoFile = await cameraRef.current.takePhoto({
          flash: "off",
          enableShutterSound: false,
        });

        const path = photo.path.startsWith("file://")
          ? photo.path
          : `file://${photo.path}`;
        const base64 = await FileSystem.readAsStringAsync(path, {
          encoding: FileSystem.EncodingType.Base64,
        });

        return base64;
      } catch (err) {
        console.error(`[Camera] ${stream} 캡처 오류:`, err);
        return null;
      }
    },
    [],
  );

  const startCapture = useCallback(
    (onFrame: (base64: string, stream: StreamType) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      const reflexInterval = Math.floor(1000 / reflexFps);
      const cognitiveInterval = Math.floor(1000 / cognitiveFps);

      reflexTimerRef.current = setInterval(async () => {
        const frame = await captureFrame("reflex");
        if (frame && onFrameRef.current) {
          onFrameRef.current(frame, "reflex");
        }
      }, reflexInterval);

      cognitiveTimerRef.current = setInterval(async () => {
        const frame = await captureFrame("cognitive");
        if (frame && onFrameRef.current) {
          onFrameRef.current(frame, "cognitive");
        }
      }, cognitiveInterval);

      console.log(
        `[Camera] 이중 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`,
      );
    },
    [reflexFps, cognitiveFps, isCapturing, captureFrame],
  );

  const stopCapture = useCallback(() => {
>>>>>>> dev
    if (reflexTimerRef.current) {
      clearInterval(reflexTimerRef.current);
      reflexTimerRef.current = null;
    }
    if (cognitiveTimerRef.current) {
      clearInterval(cognitiveTimerRef.current);
      cognitiveTimerRef.current = null;
    }
<<<<<<< HEAD

    setIsCapturing(false);
    console.log('[캡처] 루프 중지');
    // =========================================================================
    // 👨‍💻 담당자 직접 코딩 영역 끝 👨‍💻
    // =========================================================================
  }, []);

  // 컴포넌트 언마운트 시 자동 정지
  useEffect(() => { return () => stopCapture(); }, [stopCapture]);

  return { cameraRef, device, hasPermission, isCapturing, startCapture, stopCapture, captureFrame };
=======
    onFrameRef.current = null;
    setIsCapturing(false);
    console.log("[Camera] 루프 중지");
  }, []);

  useEffect(() => {
    return () => stopCapture();
  }, [stopCapture]);

  return {
    cameraRef,
    device,
    hasPermission,
    permissionStatus: hasPermission ? "granted" : permissionRequested ? "denied" : "not-requested",
    isCapturing,
    startCapture,
    stopCapture,
    requestCameraPermission,
  };
>>>>>>> dev
}
