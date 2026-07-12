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

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { Dimensions, Image, Pressable, StyleSheet, Text, View } from "react-native";
import { Camera } from "react-native-vision-camera";

import { ConnectionStatus } from "./ConnectionStatus";
import { DebugTriggerPanel } from "./DebugTriggerPanel";
import { NavMapPanel, type NavMapWaypoint } from "./NavMapPanel";
import { DEVICE_ID, TOKEN, REFLEX_FPS, COGNITIVE_FPS } from "../config";
import { MOCK_HAPTIC } from "../config/mock";
import { useCamera, type FrameData } from "../hooks/useCamera";
import { useLocation, type GpsCoords } from "../hooks/useLocation";
import { useOnDeviceDetection, type OnDeviceDetectionResult } from "../hooks/useOnDeviceDetection";
import { useSttRecorder } from "../hooks/useSttRecorder";
import { useWebSocket } from "../hooks/useWebSocket";
import { getFrameProvider } from "../services/frameProvider";
import { hapticEngine } from "../services/hapticEngine";
import { audioEngine } from "../services/audioEngine";
import type { StreamType } from "../types/detection";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const FRAME_SIZE = 640;

const MOCK_DETECT_MIN_INTERVAL_MS = 1000;
const REAL_DETECT_MIN_INTERVAL_MS = 120;

const HIGH_HAZARDS = ["person", "bicycle", "car", "motorcycle", "bus", "truck", "scooter", "wheelchair", "stroller", "carrier"];
const GROUND_HAZARDS = ["caution", "roadway"];
const SAFE_SURFACE_CLASSES = ["sidewalk_normal", "braille_normal"];
const OUTDOOR_SURFACE_CLASSES = ["sidewalk_normal", "caution", "roadway", "braille_normal"];
const OUTDOOR_SURFACE_MIN_CONFIDENCE = 0.15;

const CLASS_MIN_CONFIDENCE: Record<string, number> = {
  car: 0.6,
  bus: 0.6,
  truck: 0.6,
  motorcycle: 0.55,
  scooter: 0.5,
  fire_hydrant: 0.55,
  parking_meter: 0.55,
  traffic_light: 0.55,
  traffic_light_controller: 0.55,
  traffic_sign: 0.55,
  stop: 0.55,
  roadway: 0.55,
};

function getEffectiveConfThreshold(className: string, baseThreshold: number): number {
  const classMin = CLASS_MIN_CONFIDENCE[className];
  return classMin !== undefined ? Math.max(classMin, baseThreshold) : baseThreshold;
}

const CANVAS_OVERFLOW_MARGIN = 1.02;

function isGeometricallyImplausible(bbox: { w: number; h: number }): boolean {
  const maxSize = FRAME_SIZE * CANVAS_OVERFLOW_MARGIN;
  return bbox.w > maxSize || bbox.h > maxSize;
}

export function CameraView() {
  const { status, send, sendBinary, lastMessage, navRoute, setSttInteractionActive } = useWebSocket(DEVICE_ID, TOKEN);
  const {
    cameraRef,
    device,
    hasPermission,
    permissionStatus,
    isCapturing,
    isMockMode,
    currentReflexFps,
    startCapture,
    stopCapture,
    requestCameraPermission,
    reportInferenceLatency,
    useStreamCapture,
    frameProcessor,
  } = useCamera(REFLEX_FPS, COGNITIVE_FPS);
  const { isModelsLoaded, segLoaded, detLoaded, detShapeLog, detectFrame } =
    useOnDeviceDetection();
  const { requestLocationPermission, startWatching, stopWatching } = useLocation();

  useEffect(() => {
    if (isMockMode) return;
    let cancelled = false;

    (async () => {
      const granted = await requestLocationPermission();
      if (cancelled || !granted) return;
      await startWatching((coords: GpsCoords) => {
        send({
          type: "realtime_gps",
          lat: coords.lat,
          lon: coords.lon,
          heading: coords.heading,
        });
        const nowTs = Date.now();
        if (nowTs - lastMapPosTsRef.current >= 2000) {
          lastMapPosTsRef.current = nowTs;
          setMapPos({ lat: coords.lat, lon: coords.lon });
        }
      });
    })();

    return () => {
      cancelled = true;
      stopWatching();
    };
  }, [isMockMode]);

  const [sttErrorInfo, setSttErrorInfo] = useState<string>("");
  const sttPressActiveRef = useRef(false);
  const delayedSttStartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const {
    status: sttStatus,
    startRecording: startSttRecording,
    stopRecordingAndSend: stopSttRecording,
    requestPermissionEarly: requestSttPermissionEarly,
  } = useSttRecorder(
    (audioB64) => {
      void hapticEngine.trigger("short");
      setSttErrorInfo("");
      send({ type: "stt_audio", audio_b64: audioB64 });
    },
    (reason, detail) => {
      void hapticEngine.trigger("double");
      setSttErrorInfo(`STT 실패[${reason}]: ${detail ?? "-"}`);
    },
  );

  useEffect(() => {
    if (isMockMode) return;
    void requestSttPermissionEarly();
  }, [isMockMode]);

  useEffect(() => {
    return () => {
      sttPressActiveRef.current = false;
      if (delayedSttStartTimerRef.current) {
        clearTimeout(delayedSttStartTimerRef.current);
        delayedSttStartTimerRef.current = null;
      }
    };
  }, []);

  const [debugInfo, setDebugInfo] = useState<string[]>([]);
  const [lastDetect, setLastDetect] = useState<string>("대기");
  const [hapticFlash, setHapticFlash] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<number | null>(null);
  const [detections, setDetections] = useState<OnDeviceDetectionResult[]>([]);
  const [confThreshold, setConfThreshold] = useState(0.40);

  const [mapVisible, setMapVisible] = useState(false);
  const [mapPos, setMapPos] = useState<NavMapWaypoint | null>(null);
  const lastMapPosTsRef = useRef(0);

  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "reflex_alert") {
      const alertId = lastMessage.alert_id ?? "unknown";
      const risk = lastMessage.risk_level ?? "unknown";
      setLastDetect(`서버반사: ${alertId} (위험: ${risk})`);
    } else if (lastMessage.type === "guide") {
      const text = lastMessage.guidance_text ?? "";
      const risk = lastMessage.risk_level ?? "unknown";
      setLastDetect(`서버가이드: ${text} (${risk})`);
    } else if (lastMessage.type === "ack") {
      setLastDetect(`서버추론: 안전 (${lastMessage.decode_ms ?? 0}ms)`);
    } else if (lastMessage.type === "server_detection") {
      const rawDets = lastMessage.detections;
      const serverDets = Array.isArray(rawDets)
        ? rawDets.filter((d: any) => d && (d.bbox || d.class_name || d.className))
        : [];
      setDetections(serverDets);
    }
  }, [lastMessage]);

  const detectFrameRef = useRef(detectFrame);
  const isModelsLoadedRef = useRef(isModelsLoaded);
  const isMockModeRef = useRef(isMockMode);
  const wsStatusRef = useRef(status);
  const sendRef = useRef(send);
  const sendBinaryRef = useRef(sendBinary);
  const setLastDetectRef = useRef(setLastDetect);
  const setPreviewSrcRef = useRef(setPreviewSrc);
  const setDetectionsRef = useRef(setDetections);
  const confThresholdRef = useRef(confThreshold);
  const reportInferenceLatencyRef = useRef(reportInferenceLatency);

  useEffect(() => { detectFrameRef.current = detectFrame; }, [detectFrame]);
  useEffect(() => { isModelsLoadedRef.current = isModelsLoaded; }, [isModelsLoaded]);
  useEffect(() => { isMockModeRef.current = isMockMode; }, [isMockMode]);
  useEffect(() => { wsStatusRef.current = status; }, [status]);
  useEffect(() => { sendRef.current = send; }, [send]);
  useEffect(() => { sendBinaryRef.current = sendBinary; }, [sendBinary]);
  useEffect(() => { confThresholdRef.current = confThreshold; }, [confThreshold]);
  useEffect(() => { reportInferenceLatencyRef.current = reportInferenceLatency; }, [reportInferenceLatency]);

  const detectingRef = useRef(false);
  const lastDetectTsRef = useRef(0);

  useEffect(() => {
    if (!MOCK_HAPTIC) return;
    hapticEngine.setMockHandler(() => {
      setHapticFlash(true);
      setTimeout(() => setHapticFlash(false), 300);
    });
    return () => hapticEngine.setMockHandler(null);
  }, []);

  const handleFrame = useCallback(async (frame: FrameData, _stream: StreamType) => {
    const now = Date.now();
    const frameStream = frame.stream ?? "reflex";
    const eventId = `event-${DEVICE_ID}-${frameStream}-${now}`;

    if (frame.jpegBytes && sendRef.current && sendBinaryRef.current) {
      sendRef.current({
        type: "detection",
        payload: {
          event_id: eventId,
          device_id: DEVICE_ID,
          frame_id: now,
          stream: frameStream,
          transport: "binary",
        }
      });
      sendBinaryRef.current(frame.jpegBytes);
    } else if (frame.base64 && sendRef.current) {
      sendRef.current({
        type: "detection",
        payload: {
          event_id: eventId,
          device_id: DEVICE_ID,
          frame_id: now,
          thumbnail_jpeg_b64: frame.base64,
          stream: frameStream,
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
      const { seg, det, benchmark, scene } = await detectFrameRef.current(frame.float32, frame.base64) as any;
      const dt = Date.now() - t0;
      if (benchmark && !audioEngine.isGuidePlaying) {
        console.log(`[CoreMLBench] ANE 가속 지연시간 - 탐지(det): ${benchmark.det_ms?.toFixed(2) ?? 0}ms | 분할(seg): ${benchmark.seg_ms?.toFixed(2) ?? 0}ms | 총합(total): ${benchmark.total_ms?.toFixed(2) ?? 0}ms`);
      }
      reportInferenceLatencyRef.current(benchmark?.total_ms ?? dt);
      const allDetections = [...det, ...seg].slice(0, 20);

      // 폴백 모드(서버 연결 끊김)에서는 server_detection이 들어오지 않으므로 온디바이스
      // 추론 결과로 BBox를 표시한다. 정상 연결 시에는 온디바이스 det 결과가 비어 있을 수
      // 있어 서버 결과를 덮어쓰지 않도록 한다(원래 의도 유지). Mock 모드는 항상 온디바이스 결과 사용.
      if (isMockModeRef.current || wsStatusRef.current === "fallback") {
        setDetectionsRef.current(allDetections);
      }


      const hasOutdoorSurface = (seg as OnDeviceDetectionResult[]).some(
        (d: OnDeviceDetectionResult) => OUTDOOR_SURFACE_CLASSES.includes(d.className) && d.confidence >= OUTDOOR_SURFACE_MIN_CONFIDENCE
      );
      const isOutdoorByScene = scene ? !scene.isLikelyIndoor : true;
      const validDetections = allDetections.filter((d: OnDeviceDetectionResult) => {
        if (SAFE_SURFACE_CLASSES.includes(d.className)) return false;
        if (isGeometricallyImplausible(d.bbox)) return false;
        if (d.confidence <= getEffectiveConfThreshold(d.className, confThresholdRef.current)) return false;
        if (!hasOutdoorSurface) return false;
        if (!isOutdoorByScene) return false;
        return true;
      });
      if (validDetections.length > 0) {
        let maxAreaRatio = 0;
        let mostCriticalClass = "";

        validDetections.forEach(d => {
          const area = d.bbox.w * d.bbox.h;
          const ratio = area / (FRAME_SIZE * FRAME_SIZE);
          if (ratio > maxAreaRatio) {
            maxAreaRatio = ratio;
            mostCriticalClass = d.className;
          }
        });

        const isHighClass = HIGH_HAZARDS.includes(mostCriticalClass) || GROUND_HAZARDS.includes(mostCriticalClass);

        if (maxAreaRatio > 0.32 || (isHighClass && maxAreaRatio > 0.20)) {
          void hapticEngine.trigger("continuous");
          void audioEngine.playBeep(0.0, 0);
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 초접근 경보! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> continuous / 0ms`);
          }
        } else if (maxAreaRatio > 0.12 || (isHighClass && maxAreaRatio > 0.08)) {
          void hapticEngine.trigger("double");
          void audioEngine.playBeep(0.0, 200);
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 근접 주의! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> double / 200ms`);
          }
        } else if (maxAreaRatio > 0.03) {
          void hapticEngine.trigger("short");
          void audioEngine.playBeep(0.0, 600);
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 중거리 감지! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> short / 600ms`);
          }
        } else {
          hapticEngine.stopContinuous();
          void audioEngine.playBeep(0.0, 1200);
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 원거리 포착! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> none / 1200ms`);
          }
        }
      } else {
        hapticEngine.stopContinuous();
        void audioEngine.stopBeep();
      }

      if (isMockModeRef.current) {
        const top = [...det, ...seg][0];
        setLastDetectRef.current(
          top
            ? `${top.model}:${top.className} ${(top.confidence * 100).toFixed(0)}% (${dt}ms) seg=${seg.length} det=${det.length}`
            : `무탐지 (${dt}ms) seg=${seg.length} det=${det.length}`,
        );
      }
      if (isMockModeRef.current) {
        const src = getFrameProvider()?.getPreviewSource?.();
        if (typeof src === "number") setPreviewSrcRef.current(src);
      }
    } catch (err) {
      console.error("[CameraView] 추론 오류:", err);
    } finally { // <- finaly에서 finally로 철자 오류 완벽 정정!
      detectingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (!isMockMode && !hasPermission) return;
    if (!isMockMode && !device) return;
    if (isCapturing) return;

    startCapture((frame: FrameData) => {
      void handleFrame(frame, frame.stream ?? "reflex");
    });
    return () => stopCapture();
  }, [isMockMode, hasPermission, device]);

  useEffect(() => {
    const info: string[] = [];
    info.push(`모드: ${isMockMode ? "MOCK(시뮬레이터)" : "REAL(실기기)"}`);
    info.push(`권한: ${permissionStatus}`);
    if (!isMockMode) info.push(`카메라: ${device ? device.id : "없음"}`);
    info.push(`WS: ${status}`);
    info.push(`캡처: ${isCapturing ? "ON" : "OFF"} (반사 ${currentReflexFps}fps 동적)`);
    info.push(`모델: ${segLoaded ? "seg" : "…"} / ${detLoaded ? "det" : "…"}`);
    if (detShapeLog) info.push(`det shape: ${detShapeLog}`);
    info.push(`추론: ${lastDetect}`);
    setDebugInfo(info);
  }, [isMockMode, permissionStatus, device, status, isCapturing, currentReflexFps, segLoaded, detLoaded, detShapeLog, lastDetect]);

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

  const activeDetections = detections.filter(d => {
    const cName = (d as any).class_name || d.className;
    const cConf = d.confidence;
    return cConf > getEffectiveConfThreshold(cName, confThreshold);
  });

  const detectedClassesStr = activeDetections.length > 0
    ? activeDetections.map(d => {
      const cName = (d as any).class_name || d.className;
      const cConf = d.confidence;
      const areaRatio = (d.bbox.w * d.bbox.h) / (FRAME_SIZE * FRAME_SIZE);
      const dist = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
      return `${cName} ${dist.toFixed(1)}m (${(cConf * 100).toFixed(0)}%)`;
    }).join(", ")
    : "없음";

  return (
    <View
      style={styles.container}
      accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? "활성" : "비활성"}`}
    >
      <View style={styles.cameraContainer}>
        {isMockMode && previewSrc !== null ? (
          <Image
            source={previewSrc}
            style={StyleSheet.absoluteFill}
            resizeMode="cover"
          />
        ) : (
          !isMockMode &&
          (useStreamCapture ? (
            <Camera
              ref={cameraRef}
              device={device!}
              isActive={true}
              video={true}
              audio={false}
              pixelFormat="yuv"
              frameProcessor={frameProcessor}
              style={StyleSheet.absoluteFill}
            />
          ) : (
            <Camera
              ref={cameraRef}
              device={device!}
              isActive={true}
              photo={true}
              audio={false}
              style={StyleSheet.absoluteFill}
            />
          ))
        )}
        {hapticFlash && <View style={styles.hapticFlash} />}
        <BBoxOverlay detections={activeDetections} />
      </View>

      <Pressable
        style={StyleSheet.absoluteFill}
        onPressIn={() => {
          sttPressActiveRef.current = true;
          if (delayedSttStartTimerRef.current) {
            clearTimeout(delayedSttStartTimerRef.current);
            delayedSttStartTimerRef.current = null;
          }
          void hapticEngine.trigger("short");
          setSttInteractionActive(true);
          if (audioEngine.isGuidePlaying) {
            audioEngine.stopGuideAudio();
            delayedSttStartTimerRef.current = setTimeout(() => {
              delayedSttStartTimerRef.current = null;
              if (sttPressActiveRef.current) {
                void startSttRecording();
              }
            }, 150);
          } else {
            void startSttRecording();
          }
        }}
        onPressOut={() => {
          sttPressActiveRef.current = false;
          if (delayedSttStartTimerRef.current) {
            clearTimeout(delayedSttStartTimerRef.current);
            delayedSttStartTimerRef.current = null;
            setSttInteractionActive(false);
          }
          void stopSttRecording();
        }}
        accessibilityRole="button"
        accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? "활성" : "비활성"}. 화면을 누르고 있는 동안 음성 명령을 말하세요.`}
        accessibilityHint="손을 떼면 서버로 전송되어 음성 명령을 인식합니다."
      />

      <View style={styles.overlayTop} pointerEvents="none">
        <ConnectionStatus status={status} />
      </View>

      <View style={styles.debugOverlay} pointerEvents="none">
        {debugInfo.map((line, i) => (
          <Text key={i} style={styles.debugText}>{line}</Text>
        ))}
      </View>

      <View style={styles.confThresholdRow} pointerEvents="box-none">
        <Text style={styles.confThresholdLabel}>신뢰도 임계값: {(confThreshold * 100).toFixed(0)}%</Text>
        <View style={styles.confThresholdButtons}>
          <Pressable
            style={styles.confThresholdButton}
            onPress={() => setConfThreshold(v => Math.max(0.05, Math.round((v - 0.05) * 100) / 100))}
          >
            <Text style={styles.confThresholdButtonText}>-</Text>
          </Pressable>
          <Pressable
            style={styles.confThresholdButton}
            onPress={() => setConfThreshold(v => Math.min(0.95, Math.round((v + 0.05) * 100) / 100))}
          >
            <Text style={styles.confThresholdButtonText}>+</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.detectionListOverlay} pointerEvents="none">
        <Text style={styles.detectionListTitle}>[실시간 감지]</Text>
        <Text style={styles.detectionListText}>{detectedClassesStr}</Text>
      </View>

      <View
        style={[styles.sttButton, sttStatus !== "idle" && styles.sttButtonActive]}
        pointerEvents="none"
      >
        <Text style={styles.sttButtonText}>
          {sttStatus === "recording" ? "듣는 중..." : sttStatus === "sending" ? "전송 중..." : "화면을 누르고 말하기"}
        </Text>
        {sttErrorInfo !== "" && (
          <Text style={styles.sttErrorText}>{sttErrorInfo}</Text>
        )}
      </View>

      <View style={styles.panelWrap} pointerEvents="box-none">
        <DebugTriggerPanel />
      </View>

      {mapVisible && (
        <View style={styles.navMapWrap} pointerEvents="none">
          <NavMapPanel
            appKey={navRoute?.appKey ?? ""}
            waypoints={navRoute?.waypoints ?? []}
            current={mapPos}
          />
        </View>
      )}
      <View style={styles.mapToggleWrap} pointerEvents="box-none">
        <Pressable
          style={styles.mapToggleButton}
          onPress={() => setMapVisible((v) => !v)}
          accessibilityRole="button"
          accessibilityLabel={mapVisible ? "지도 끄기" : "지도 켜기"}
        >
          <Text style={styles.mapToggleText}>{mapVisible ? "지도 끄기" : "지도 켜기"}</Text>
        </Pressable>
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

function getClassColor(className: string): string {
  if (HIGH_HAZARDS.includes(className) || className === "caution") {
    return "#EF4444";
  }
  if (className === "roadway") {
    return "#F59E0B";
  }
  let hash = 0;
  for (let i = 0; i < className.length; i++) {
    hash = className.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  return `hsl(${hue}, 85%, 55%)`;
}

function BBoxOverlay({ detections }: { detections: OnDeviceDetectionResult[] }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {detections.map((d, i) => {
        // 안전 가드레일: 데이터 구조가 깨져있거나 bbox가 없으면 강제 패스하여 렌더링 붕괴 방지
        if (!d || !d.bbox) return null;

        const cName = (d as any).class_name || d.className;
        const color = getClassColor(cName);
        const leftPct = (d.bbox.x / FRAME_SIZE) * 100;
        const topPct = (d.bbox.y / FRAME_SIZE) * 100;
        const widthPct = (d.bbox.w / FRAME_SIZE) * 100;
        const heightPct = (d.bbox.h / FRAME_SIZE) * 100;
        const areaRatio = (d.bbox.w * d.bbox.h) / (FRAME_SIZE * FRAME_SIZE);
        const distance = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
        const labelLeftPct = Math.min(100, Math.max(0, leftPct));
        const labelTopPct = Math.min(100, Math.max(0, topPct));
        return (
          <Fragment key={`${d.model}-${i}`}>

            <View
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
            />
            <View
              style={[
                styles.bboxLabel,
                { position: "absolute", left: `${labelLeftPct}%`, top: `${labelTopPct}%`, backgroundColor: color },
              ]}
            >
              <Text style={styles.bboxText}>
                {cName} {distance.toFixed(1)}m ({(d.confidence * 100).toFixed(0)}%)
              </Text>
            </View>
          </Fragment>
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
  confThresholdRow: {
    position: "absolute",
    top: 216,
    left: 16,
    right: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 8,
    backgroundColor: "rgba(0,0,0,0.6)",
    borderRadius: 8,
  },
  confThresholdLabel: {
    color: "#FFFFFF",
    fontSize: 12,
    fontFamily: "monospace",
  },
  confThresholdButtons: {
    flexDirection: "row",
  },
  confThresholdButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#007AFF",
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 8,
  },
  confThresholdButtonText: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "bold",
  },
  detectionListOverlay: {
    position: "absolute",
    top: 300,
    left: 16,
    right: 16,
    padding: 10,
    backgroundColor: "rgba(0,0,0,0.8)",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#555555",
  },
  detectionListTitle: {
    color: "#F59E0B",
    fontSize: 12,
    fontWeight: "bold",
    fontFamily: "monospace",
    marginBottom: 4,
  },
  detectionListText: {
    color: "#10B981",
    fontSize: 15,
    fontWeight: "bold",
    fontFamily: "monospace",
  },
  panelWrap: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
  },
  navMapWrap: {
    position: "absolute",
    bottom: 6,
    left: 12,
    right: 12,
    height: 210,
    borderRadius: 8,
    overflow: "hidden",
  },
  mapToggleWrap: {
    position: "absolute",
    bottom: 222,
    right: 12,
  },
  mapToggleButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 16,
    backgroundColor: "rgba(0,0,0,0.6)",
  },
  mapToggleText: {
    color: "#FFFFFF",
    fontSize: 12,
    fontWeight: "600",
  },
  sttButton: {
    position: "absolute",
    bottom: 180,
    alignSelf: "center",
    minWidth: 220,
    paddingVertical: 18,
    paddingHorizontal: 28,
    borderRadius: 32,
    backgroundColor: "#2563EB",
    alignItems: "center",
    justifyContent: "center",
  },
  sttButtonActive: {
    backgroundColor: "#DC2626",
  },
  sttButtonText: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "700",
  },
  sttErrorText: {
    color: "#FCA5A5",
    fontSize: 12,
    fontWeight: "600",
    marginTop: 4,
    textAlign: "center",
  },
  bboxLabel: {
    position: "absolute",
    top: 0,
    left: 0,
    paddingHorizontal: 4,
    paddingVertical: 2,
  },
  bboxText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "bold",
    fontFamily: "monospace",
  },
  cameraContainer: {
    width: "100%",
    aspectRatio: 1,
    overflow: "hidden",
    position: "relative",
    backgroundColor: "#111111",
  },
});
