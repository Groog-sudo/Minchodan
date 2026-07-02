/**
 * 카메라 뷰 및 WebSocket 연동 컴포넌트.
 * WS 연결 상태에 따라 이중 캡처를 시작/중지합니다.
 * react-native-vision-camera v4 API (photo prop + ref.takePhoto).
 */

import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
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
    permissionStatus,
    isCapturing,
    startCapture,
    stopCapture,
    requestCameraPermission,
  } = useCamera(10, 2);

  const [debugInfo, setDebugInfo] = useState<string[]>([]);

  useEffect(() => {
    if (status === "connected" && !isCapturing && device) {
      startCapture((base64: string, stream: StreamType) => {
        sendFrame(base64, stream, DEVICE_ID, send);
      });
    } else if (status !== "connected" && isCapturing) {
      stopCapture();
    }
  }, [status, isCapturing, startCapture, stopCapture, send, device]);

  useEffect(() => {
    const info: string[] = [];
    info.push(`권한: ${permissionStatus}`);
    info.push(`카메라: ${device ? device.id : "없음"}`);
    info.push(`연결: ${status}`);
    info.push(`캡처: ${isCapturing ? "ON" : "OFF"}`);
    setDebugInfo(info);
  }, [permissionStatus, device, status, isCapturing]);

  if (!hasPermission) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>카메라 권한 필요</Text>
        <Text style={styles.message}>권한 상태: {permissionStatus}</Text>
        <Pressable
          style={styles.button}
          onPress={() => requestCameraPermission()}
        >
          <Text style={styles.buttonText}>권한 요청하기</Text>
        </Pressable>
        <View style={styles.debugBox}>
          {debugInfo.map((line, i) => (
            <Text key={i} style={styles.debugText}>{line}</Text>
          ))}
        </View>
        <ConnectionStatus status={status} />
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>카메라 로딩 중...</Text>
        <Text style={styles.message}>권한: {permissionStatus}</Text>
        <Text style={styles.message}>디바이스를 검색하고 있습니다.</Text>
        <Pressable
          style={styles.button}
          onPress={() => requestCameraPermission()}
        >
          <Text style={styles.buttonText}>권한 다시 요청</Text>
        </Pressable>
        <View style={styles.debugBox}>
          {debugInfo.map((line, i) => (
            <Text key={i} style={styles.debugText}>{line}</Text>
          ))}
        </View>
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
      <View style={styles.debugOverlay}>
        {debugInfo.map((line, i) => (
          <Text key={i} style={styles.debugOverlayText}>{line}</Text>
        ))}
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
    padding: 20,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 12,
  },
  message: {
    color: "#CCCCCC",
    fontSize: 14,
    marginBottom: 8,
  },
  button: {
    backgroundColor: "#007AFF",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  debugBox: {
    marginTop: 20,
    padding: 12,
    backgroundColor: "#1A1A1A",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#333333",
  },
  debugText: {
    color: "#00FF00",
    fontSize: 12,
    fontFamily: "monospace",
  },
  overlay: {
    position: "absolute",
    top: 60,
    left: 16,
  },
  debugOverlay: {
    position: "absolute",
    bottom: 40,
    left: 16,
    right: 16,
    padding: 8,
    backgroundColor: "rgba(0,0,0,0.7)",
    borderRadius: 8,
  },
  debugOverlayText: {
    color: "#00FF00",
    fontSize: 11,
    fontFamily: "monospace",
  },
});
