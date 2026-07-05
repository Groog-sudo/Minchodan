/**
 * 카메라 뷰 및 온디바이스 추론 오케스트레이터.
 * - MOCK_CAMERA: 번들 샘플 Image 프리뷰 + MockFrameProvider → TFLite 추론
 * - 실기기    : react-native-vision-camera 프리뷰 + takePhoto → TFLite 추론
 * 두 모델(segmentation + object_detection)을 스로틀 구동하고 Reflex Gate로 비프/햡틱 발화.
 *
 * [수정 이력]
 * - Stale Closure 완전 제거: useRef 미러링으로 항상 최신 상태를 참조한다.
 * - WS 연결 여부와 캡처 시작을 분리: 모델 로드 완료 + 권한 확보 시 즉시 구동.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Dimensions, Image, Pressable, StyleSheet, Text, View } from "react-native";
import { Camera } from "react-native-vision-camera";

import { ConnectionStatus } from "./ConnectionStatus";
import { DebugTriggerPanel } from "./DebugTriggerPanel";
import { DEVICE_ID, TOKEN } from "../config";
import { MOCK_HAPTIC } from "../config/mock";
import { useCamera, type FrameData } from "../hooks/useCamera";
import { useOnDeviceDetection, type OnDeviceDetectionResult } from "../hooks/useOnDeviceDetection";
import { useWebSocket } from "../hooks/useWebSocket";
import { getFrameProvider } from "../services/frameProvider";
import { hapticEngine } from "../services/hapticEngine";
import { audioEngine } from "../services/audioEngine";
import type { StreamType } from "../types/detection";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const FRAME_SIZE = 640;

const MOCK_DETECT_MIN_INTERVAL_MS = 1000;
const REAL_DETECT_MIN_INTERVAL_MS = 120;

export function CameraView() {
  const { status, send } = useWebSocket(DEVICE_ID, TOKEN);
  const {
    cameraRef,
    device,
    hasPermission,
    permissionStatus,
    isCapturing,
    isMockMode,
    startCapture,
    stopCapture,
    requestCameraPermission,
  } = useCamera(10, 2);
  const { isModelsLoaded, segLoaded, detLoaded, detShapeLog, detectFrame } =
    useOnDeviceDetection();

  const [debugInfo, setDebugInfo] = useState<string[]>([]);
  const [lastDetect, setLastDetect] = useState<string>("대기");
  const [hapticFlash, setHapticFlash] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<number | null>(null);
  const [detections, setDetections] = useState<OnDeviceDetectionResult[]>([]);

  // Stale Closure 방지용 useRef 미러: setInterval 콜백은 등록 시점의 값을 캡처하므로
  // 최신 상태는 반드시 ref 를 통해 읽어야 한다.
  const detectFrameRef = useRef(detectFrame);
  const isModelsLoadedRef = useRef(isModelsLoaded);
  const isMockModeRef = useRef(isMockMode);
  const sendRef = useRef(send);
  const setLastDetectRef = useRef(setLastDetect);
  const setPreviewSrcRef = useRef(setPreviewSrc);
  const setDetectionsRef = useRef(setDetections);

  useEffect(() => { detectFrameRef.current = detectFrame; }, [detectFrame]);
  useEffect(() => { isModelsLoadedRef.current = isModelsLoaded; }, [isModelsLoaded]);
  useEffect(() => { isMockModeRef.current = isMockMode; }, [isMockMode]);
  useEffect(() => { sendRef.current = send; }, [send]);

  const detectingRef = useRef(false);
  const lastDetectTsRef = useRef(0);

  // Mock 햅틱 시각 핸들러 등록
  useEffect(() => {
    if (!MOCK_HAPTIC) return;
    hapticEngine.setMockHandler(() => {
      setHapticFlash(true);
      setTimeout(() => setHapticFlash(false), 300);
    });
    return () => hapticEngine.setMockHandler(null);
  }, []);

  // ref 기반 handleFrame: 항상 최신 상태를 참조하며 stale closure 없음.
  const handleFrame = useCallback(async (frame: FrameData, _stream: StreamType) => {
    const now = Date.now();

    // 로컬 추론 엔진 적재 여부와 관계없이 서버로 base64 프레임 전송 수행 (WebSocket)
    if (frame.base64 && sendRef.current) {
      sendRef.current({
        type: "detection",
        payload: {
          event_id: `event-${now}`,
          frame_id: now,
          thumbnail_jpeg_b64: frame.base64,
          stream: frame.stream ?? "reflex",
        }
      });
    }

    if (!isModelsLoadedRef.current) return;

    const minInterval = isMockModeRef.current
      ? MOCK_DETECT_MIN_INTERVAL_MS
      : REAL_DETECT_MIN_INTERVAL_MS;

    if (detectingRef.current || now - lastDetectTsRef.current < minInterval) {
      return;
    }

    detectingRef.current = true;
    lastDetectTsRef.current = now;
    try {
      const t0 = Date.now();
      const { seg, det, benchmark } = await detectFrameRef.current(frame.float32, frame.base64) as any;
      const dt = Date.now() - t0;
      if (benchmark) {
        console.log(`[CoreMLBench] ANE 가속 지연시간 - 탐지(det): ${benchmark.det_ms?.toFixed(2) ?? 0}ms | 분할(seg): ${benchmark.seg_ms?.toFixed(2) ?? 0}ms | 총합(total): ${benchmark.total_ms?.toFixed(2) ?? 0}ms`);
      }
      // BBox 오버레이용: det + seg 상위 결과 병합
      const allDetections = [...det, ...seg].slice(0, 20);
      setDetectionsRef.current(allDetections);

      // 실시간 햅틱 및 입체 비프음 피드백 연동 (Reflex Gate)
      if (allDetections.length > 0) {
        const highHazards = ["person", "bicycle", "car", "motorcycle", "bus", "truck", "skateboard", "pothole", "caution"];
        const hasHigh = allDetections.some(d => highHazards.includes(d.className) && d.confidence > 0.45);

        if (hasHigh) {
          void hapticEngine.trigger("double");
          void audioEngine.playBeep(0.0, 300); // 긴급 충돌 위험: 300ms 빠른 경보음
        } else {
          void hapticEngine.trigger("short");
          void audioEngine.playBeep(0.0, 800); // 일반 장애물: 800ms 느린 경보음
        }
      } else {
        hapticEngine.stopContinuous();
        void audioEngine.stopBeep();
      }

      const top = [...det, ...seg][0];
      setLastDetectRef.current(
        top
          ? `${top.model}:${top.className} ${(top.confidence * 100).toFixed(0)}% (${dt}ms) seg=${seg.length} det=${det.length}`
          : `무탐지 (${dt}ms) seg=${seg.length} det=${det.length}`,
      );
      if (isMockModeRef.current) {
        const src = getFrameProvider()?.getPreviewSource?.();
        if (typeof src === "number") setPreviewSrcRef.current(src);
      }
    } catch (err) {
      console.error("[CameraView] 추론 오류:", err);
    } finally {
      detectingRef.current = false;
    }
  }, []); // 의존성 없음 - 모든 최신 상태를 ref 로 직접 참조

  // 캡처 시작: 권한 확보 즉시 구동 (로컬 모델 로딩 여부와 관계없이 서버 추론 전송을 위해 즉시 캡처 기동)
  useEffect(() => {
    if (!isMockMode && !hasPermission) return;  // 실기기: 권한 없으면 대기
    if (!isMockMode && !device) return;          // 실기기: 카메라 디바이스 없으면 대기
    if (isCapturing) return;                     // 중복 시작 방지

    startCapture((frame: FrameData) => {
      void handleFrame(frame, frame.stream ?? "reflex");
    });
    return () => stopCapture();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMockMode, hasPermission, device]);

  useEffect(() => {
    const info: string[] = [];
    info.push(`모드: ${isMockMode ? "MOCK(시뮬레이터)" : "REAL(실기기)"}`);
    info.push(`권한: ${permissionStatus}`);
    if (!isMockMode) info.push(`카메라: ${device ? device.id : "없음"}`);
    info.push(`WS: ${status}`);
    info.push(`캡처: ${isCapturing ? "ON" : "OFF"}`);
    info.push(`모델: ${segLoaded ? "seg" : "…"} / ${detLoaded ? "det" : "…"}`);
    if (detShapeLog) info.push(`det shape: ${detShapeLog}`);
    info.push(`추론: ${lastDetect}`);
    setDebugInfo(info);
  }, [isMockMode, permissionStatus, device, status, isCapturing, segLoaded, detLoaded, detShapeLog, lastDetect]);

  // --- 권한 게이트 (실기기 전용) ---
  if (!isMockMode && !hasPermission) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>카메라 권한 필요</Text>
        <Text style={styles.message}>권한 상태: {permissionStatus}</Text>
        <Pressable style={styles.button} onPress={() => requestCameraPermission()}>
          <Text style={styles.buttonText}>권한 요청하기</Text>
        </Pressable>
        <DebugBox info={debugInfo} />
        <ConnectionStatus status={status} />
      </View>
    );
  }

  if (!isMockMode && !device) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>카메라 로딩 중...</Text>
        <DebugBox info={debugInfo} />
        <ConnectionStatus status={status} />
      </View>
    );
  }

  return (
    <View
      style={styles.container}
      accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? "활성" : "비활성"}`}
    >
      {/* 1:1 카메라 스크린 기하학적 정합 프레임 */}
      <View style={styles.cameraContainer}>
        {isMockMode && previewSrc !== null ? (
          <Image
            source={previewSrc}
            style={StyleSheet.absoluteFill}
            resizeMode="cover"
          />
        ) : (
          !isMockMode && (
            <Camera
              ref={cameraRef}
              device={device!}
              isActive={true}
              photo={true}
              style={StyleSheet.absoluteFill}
            />
          )
        )}
        {hapticFlash && <View style={styles.hapticFlash} />}
        {/* BBox 오버레이: 640x640 비율과 1:1 카메라 프레임의 완벽 정합 */}
        <BBoxOverlay detections={detections} />
      </View>

      <View style={styles.overlayTop}>
        <ConnectionStatus status={status} />
      </View>

      <View style={styles.debugOverlay}>
        {debugInfo.map((line, i) => (
          <Text key={i} style={styles.debugText}>{line}</Text>
        ))}
      </View>

      <View style={styles.panelWrap}>
        <DebugTriggerPanel />
      </View>
    </View>
  );
}

function DebugBox({ info }: { info: string[] }) {
  return (
    <View style={styles.debugBox}>
      {info.map((line, i) => (
        <Text key={i} style={styles.debugText}>{line}</Text>
      ))}
    </View>
  );
}

// 간단한 스트링 해시를 통해 고유 HSL 색상 생성 (시각장애인 보행 시인성 확보)
function getClassColor(className: string): string {
  // 긴급 충돌 위험군은 빨간색 강제 고정
  const highHazards = ["person", "bicycle", "car", "motorcycle", "bus", "truck", "skateboard", "pothole", "caution"];
  if (highHazards.includes(className)) {
    return "#EF4444";
  }

  // 지면 관련 위험은 주황색 강제 고정
  const groundHazards = ["roadway"];
  if (groundHazards.includes(className)) {
    return "#F59E0B";
  }

  // 그 외 일반 장애물은 고유 해시 기반 HSL 컬러 매핑 (선명도 85%, 밝기 55%)
  let hash = 0;
  for (let i = 0; i < className.length; i++) {
    hash = className.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  return `hsl(${hue}, 85%, 55%)`;
}

/**
 * BBox 오버레이: 카메라 프리뷰 위에 탐지 박스를 그린다.
 * 박스 좌표는 640x640 기준이므로 화면 대비 비율로 변환.
 */
function BBoxOverlay({ detections }: { detections: OnDeviceDetectionResult[] }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {detections.map((d, i) => {
        const color = getClassColor(d.className);
        const leftPct = (d.bbox.x / FRAME_SIZE) * 100;
        const topPct = (d.bbox.y / FRAME_SIZE) * 100;
        const widthPct = (d.bbox.w / FRAME_SIZE) * 100;
        const heightPct = (d.bbox.h / FRAME_SIZE) * 100;
        return (
          <View
            key={`${d.model}-${i}`}
            style={{
              position: "absolute",
              left: `${leftPct}%`,
              top: `${topPct}%`,
              width: `${widthPct}%`,
              height: `${heightPct}%`,
              borderWidth: 2,
              borderColor: color,
              backgroundColor: "transparent",
            }}
          >
            <View style={[styles.bboxLabel, { backgroundColor: color }]}>
              <Text style={styles.bboxText}>
                {d.className} {(d.confidence * 100).toFixed(0)}%
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000000",
  },
  title: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 12,
    textAlign: "center",
    marginTop: 40,
  },
  message: {
    color: "#CCCCCC",
    fontSize: 14,
    marginBottom: 8,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#007AFF",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
    alignSelf: "center",
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  debugBox: {
    marginTop: 20,
    marginHorizontal: 16,
    padding: 12,
    backgroundColor: "#1A1A1A",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#333333",
  },
  debugText: {
    color: "#00FF00",
    fontSize: 11,
    fontFamily: "monospace",
  },
  hapticFlash: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    backgroundColor: "rgba(239,68,68,0.35)",
  },
  overlayTop: {
    position: "absolute",
    top: 60,
    left: 16,
  },
  debugOverlay: {
    position: "absolute",
    top: 100,
    left: 16,
    right: 16,
    padding: 8,
    backgroundColor: "rgba(0,0,0,0.6)",
    borderRadius: 8,
  },
  panelWrap: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
  },
  bboxLabel: {
    position: "absolute",
    top: -16,
    left: -2,
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 3,
  },
  bboxText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "bold",
    fontFamily: "monospace",
  },
  cameraContainer: {
    width: SCREEN_WIDTH,
    height: SCREEN_WIDTH,
    overflow: "hidden",
    position: "relative",
    backgroundColor: "#111111",
  },
});
