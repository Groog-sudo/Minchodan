/**
 * 카메라 뷰 및 WebSocket 연동 컴포넌트.
 * WS 연결 상태에 따라 이중 캡처를 시작/중지합니다.
 * react-native-vision-camera v4 API (photo prop + ref.takePhoto).
 */

import { useEffect } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Camera } from "react-native-vision-camera";

import { ConnectionStatus } from "./ConnectionStatus";
import { DEVICE_ID, TOKEN } from "../config";
import { useCamera } from "../hooks/useCamera";
import { useWebSocket } from "../hooks/useWebSocket";
import { sendFrame } from "../services/frameCapture";
import type { StreamType } from "../types/detection";

export function CameraView() {
  const { status, send } = useWebSocket(DEVICE_ID, TOKEN);
  const {
    cameraRef,
    device,
    hasPermission,
    isCapturing,
    startCapture,
    stopCapture,
  } = useCamera(10, 2);

  useEffect(() => {
    if (status === "connected" && !isCapturing) {
      startCapture((base64: string, stream: StreamType) => {
        sendFrame(base64, stream, DEVICE_ID, send);
      });
    } else if (status !== "connected" && isCapturing) {
      stopCapture();
    }
  }, [status, isCapturing, startCapture, stopCapture, send]);

  if (!hasPermission) {
    return (
      <View style={styles.container}>
        <Text style={styles.message}>카메라 권한이 필요합니다.</Text>
        <ConnectionStatus status={status} />
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.container}>
        <Text style={styles.message}>카메라를 찾을 수 없습니다.</Text>
        <ConnectionStatus status={status} />
      </View>
    );
  }

  return (
    <View
      style={styles.container}
      accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? "활성" : "비활성"}`}
    >
      <Camera
        ref={cameraRef}
        device={device}
        isActive={true}
        photo={true}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.overlay}>
        <ConnectionStatus status={status} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000000",
    justifyContent: "center",
    alignItems: "center",
  },
  message: {
    color: "#FFFFFF",
    fontSize: 16,
    marginBottom: 12,
  },
  overlay: {
    position: "absolute",
    top: 60,
    left: 16,
  },
});
