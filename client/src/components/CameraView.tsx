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
import { DEVICE_ID, TOKEN, REFLEX_FPS, COGNITIVE_FPS } from "../config";
import { MOCK_HAPTIC } from "../config/mock";
import { useCamera, type FrameData } from "../hooks/useCamera";
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

// 29클래스 중 이동체(충돌 접근 속도가 빠른 대상) - 조기 경보 임계치를 낮게 적용
const HIGH_HAZARDS = ["person", "bicycle", "car", "motorcycle", "bus", "truck", "scooter", "wheelchair", "stroller", "carrier"];
// 노면 위험 구간 (segmentation 클래스, SEG_HAZARD 인덱스와 정합: caution, roadway)
const GROUND_HAZARDS = ["caution", "roadway"];
// 2026-07-07 추가: 정상 보행로(안전한 바닥면)는 화면을 크게 채워도 장애물이 아니다.
// 기존 로직은 maxAreaRatio > 0.32 등 면적 조건이 클래스와 무관하게 무조건 최상위(초접근)
// 경보를 발동시켜, 카메라를 아래로 향하거나 바닥에 가까이 대면 정상 보행로만으로도
// 연속음+강한 진동이 울리는 오탐이 관측됨. 안전 노면 클래스는 반사 경보 판정에서
// 완전히 제외한다(디스플레이용 activeDetections/BBoxOverlay에는 계속 노출됨).
const SAFE_SURFACE_CLASSES = ["sidewalk_normal", "braille_normal"];

// 2026-07-07 추가: 이 모델(det/seg 둘 다)은 AI Hub 한국 인도(실외) 데이터셋만으로
// 학습되어 실내 개념 자체를 모른다. 특정 클래스(car)만 개별로 막아본 결과 bollard/
// movable_signage/pole 등 다른 클래스도 똑같이 실내에서 고신뢰도 오탐이 발생함을 확인함.
// 이 제품 자체가 "실외 보행로 보조"로 스코프가 한정되어 있으므로(README/설계 문서),
// object_detection 클래스 전체에 대해 "같은 프레임에 실외 보행로 segmentation 신호가
// 전혀 없으면 반사 경보 대상에서 제외"하는 포괄적 교차검증(co-occurrence)을 적용한다.
// segmentation 4클래스 자체(sidewalk_normal/caution/roadway/braille_normal)는 그 존재
// 자체가 "실외 보행로를 보고 있다"는 근거이므로 이 게이트에서 자기 자신을 통과시킨다.
const OUTDOOR_SURFACE_CLASSES = ["sidewalk_normal", "caution", "roadway", "braille_normal"];
const OUTDOOR_SURFACE_MIN_CONFIDENCE = 0.15;

// 2026-07-07 추가: 실내 오탐 완화용 클래스별 최소 confidence.
// YOLO26n det/seg 둘 다 AI Hub 한국 인도(실외) 데이터셋만으로 학습되어 "실내"라는 개념
// 자체를 모른다. 실내에서만 나타날 리 없는(즉 실외 전용) 클래스들이 실내 오탐 시 자주
// 걸리는 대상이라, 전역 confThreshold(사용자 슬라이더, 기본 40%)보다 더 높은 하한선을
// 개별로 강제한다. 목록에 없는 클래스는 confThreshold를 그대로 사용한다.
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

// 클래스별 최소 confidence와 사용자 슬라이더(confThreshold) 중 더 높은 값을 유효 임계값으로 사용
function getEffectiveConfThreshold(className: string, baseThreshold: number): number {
  const classMin = CLASS_MIN_CONFIDENCE[className];
  return classMin !== undefined ? Math.max(classMin, baseThreshold) : baseThreshold;
}

// 2026-07-07 추가 (docs/design/indoor_fp_mitigation_design.md §3 물리적 타당성 필터):
// bbox는 640x640 캔버스에 대한 회귀 출력이므로, 정상 학습 데이터의 GT는 캔버스 경계를
// 초과할 수 없다. 실기기 실내 오탐 로그에서 w/h가 640을 뚜렷하게 초과(641~676)하는
// 회귀 붕괴 패턴이 반복 관측됨 - 클래스와 무관하게 이런 bbox는 신뢰할 수 없으므로
// 반사 경보 판정에서 제외한다. 부동소수점 회귀 노이즈 감안 2% 여유만 허용.
const CANVAS_OVERFLOW_MARGIN = 1.02;

function isGeometricallyImplausible(bbox: { w: number; h: number }): boolean {
  const maxSize = FRAME_SIZE * CANVAS_OVERFLOW_MARGIN;
  return bbox.w > maxSize || bbox.h > maxSize;
}

export function CameraView() {
  const { status, send, sendBinary, lastMessage } = useWebSocket(DEVICE_ID, TOKEN);
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
  } = useCamera(REFLEX_FPS, COGNITIVE_FPS);
  const { isModelsLoaded, segLoaded, detLoaded, detShapeLog, detectFrame } =
    useOnDeviceDetection();

  // STT 음성 명령: 단말은 마이크 캡처만 담당, 인식은 서버(stt_audio 핸들러)가 수행.
  const { status: sttStatus, startRecording: startSttRecording, stopRecordingAndSend: stopSttRecording } =
    useSttRecorder((audioB64) => {
      send({ type: "stt_audio", audio_b64: audioB64 });
    });

  const [debugInfo, setDebugInfo] = useState<string[]>([]);
  const [lastDetect, setLastDetect] = useState<string>("대기");
  const [hapticFlash, setHapticFlash] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<number | null>(null);
  const [detections, setDetections] = useState<OnDeviceDetectionResult[]>([]);
  const [confThreshold, setConfThreshold] = useState(0.40);

  // 서버 실시간 웹소켓 추론 결과 수신 시 화면 상태 업데이트
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "reflex_alert") {
      const alertId = lastMessage.alert_id ?? "unknown";
      const risk = lastMessage.risk_level ?? "unknown";
      setLastDetect(`서버반사: ${alertId} (위험: ${risk})`);
    } else if (lastMessage.type === "guide") {
      // 오디오 재생은 useWebSocket의 onmessage에서 직접 트리거된다(상태 경유 차단).
      const text = lastMessage.guidance_text ?? "";
      const risk = lastMessage.risk_level ?? "unknown";
      setLastDetect(`서버가이드: ${text} (${risk})`);
    } else if (lastMessage.type === "ack") {
      setLastDetect(`서버추론: 안전 (${lastMessage.decode_ms ?? 0}ms)`);
    }
  }, [lastMessage]);

  // Stale Closure 방지용 useRef 미러: setInterval 콜백은 등록 시점의 값을 캡처하므로
  // 최신 상태는 반드시 ref 를 통해 읽어야 한다.
  const detectFrameRef = useRef(detectFrame);
  const isModelsLoadedRef = useRef(isModelsLoaded);
  const isMockModeRef = useRef(isMockMode);
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
  useEffect(() => { sendRef.current = send; }, [send]);
  useEffect(() => { sendBinaryRef.current = sendBinary; }, [sendBinary]);
  useEffect(() => { confThresholdRef.current = confThreshold; }, [confThreshold]);
  useEffect(() => { reportInferenceLatencyRef.current = reportInferenceLatency; }, [reportInferenceLatency]);

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

    // 로컬 추론 엔진 적재 여부와 관계없이 서버로 프레임 전송 수행 (WebSocket)
    // raw JPEG 바이트가 있으면(실기기) base64를 경유하지 않고 메타데이터(JSON) + 바이너리
    // 프레임 2개를 순차 전송한다. 단일 WS 연결에서 프레임 순서는 보장되므로 서버는
    // "transport: binary" 메타 수신 직후 오는 바이너리 프레임을 해당 이벤트로 매칭한다.
    if (frame.jpegBytes && sendRef.current && sendBinaryRef.current) {
      sendRef.current({
        type: "detection",
        payload: {
          event_id: `event-${now}`,
          device_id: DEVICE_ID,
          frame_id: now,
          stream: frame.stream ?? "reflex",
          transport: "binary",
        }
      });
      sendBinaryRef.current(frame.jpegBytes);
    } else if (frame.base64 && sendRef.current) {
      // 폴백(Mock 등 jpegBytes 미지원 경로): 기존 base64 방식 유지
      sendRef.current({
        type: "detection",
        payload: {
          event_id: `event-${now}`,
          device_id: DEVICE_ID,
          frame_id: now,
          thumbnail_jpeg_b64: frame.base64,
          stream: frame.stream ?? "reflex",
        }
      });
    }

    if (!isModelsLoadedRef.current) return;

    // 실기기 온디바이스 추론 재활성화 (Vision/raw-tensor 불일치로 인한 크래시 원인 수정 완료,
    // CoreMLInferenceBridge.swift 참조). 재현 테스트를 위해 서버 추론 전담 우회 가드를 제거함.

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
      // 온디바이스 추론 지연을 캡처 루프에 피드백하여 반사 fps를 동적으로 조절
      // (추론이 캡처 간격을 못 따라가면 fps를 낮춰 과부하로 인한 크래시 재발을 방지)
      reportInferenceLatencyRef.current(benchmark?.total_ms ?? dt);
      // BBox 오버레이용: det + seg 상위 결과 병합
      const allDetections = [...det, ...seg].slice(0, 20);
      setDetectionsRef.current(allDetections);

      // 실시간 햅틱 및 입체 비프음 피드백 연동 (Reflex Gate - 주차 센서 다이내믹 피드백)
      const hasOutdoorSurface = (seg as OnDeviceDetectionResult[]).some(
        (d: OnDeviceDetectionResult) => OUTDOOR_SURFACE_CLASSES.includes(d.className) && d.confidence >= OUTDOOR_SURFACE_MIN_CONFIDENCE
      );
      // docs/design/indoor_fp_mitigation_design.md §4.4: seg 기반 co-occurrence 게이트(hasOutdoorSurface)와
      // VNClassifyImageRequest 씬 분류(scene.isLikelyIndoor)를 AND로 결합한다(중첩 방어).
      // scene이 없거나(Android, 계측 실패) 판정 불가면 true로 폴백해 기존 게이트만으로 동작시킨다.
      const isOutdoorByScene = scene ? !scene.isLikelyIndoor : true;
      const validDetections = allDetections.filter((d: OnDeviceDetectionResult) => {
        // 안전 보행로는 화면을 아무리 채워도 장애물이 아니므로 반사 경보 판정에서 제외
        if (SAFE_SURFACE_CLASSES.includes(d.className)) return false;
        // 회귀 붕괴로 캔버스 크기를 초과하는 bbox는 기하학적으로 신뢰 불가 (§3 물리적 타당성 필터)
        if (isGeometricallyImplausible(d.bbox)) return false;
        if (d.confidence <= getEffectiveConfThreshold(d.className, confThresholdRef.current)) return false;
        // 실외 보행로 신호가 전혀 없는 프레임(=실내로 추정)이면 어떤 클래스든 반사 경보 대상에서 제외.
        // OUTDOOR_SURFACE_CLASSES 자신은 존재 자체가 hasOutdoorSurface를 true로 만들므로 자기 자신은 통과한다.
        if (!hasOutdoorSurface) return false;
        // §4.4 씬 분류 게이트: 지면/초목/도로 긍정 증거 없이 실내로 판정되면 제외
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

        // 긴급 회피 클래스 목록 (이동체 + 노면 위험 구간)
        const isHighClass = HIGH_HAZARDS.includes(mostCriticalClass) || GROUND_HAZARDS.includes(mostCriticalClass);

        // 주차센서식 거리 반비례 4단계 피드백 캘리브레이션
        if (maxAreaRatio > 0.32 || (isHighClass && maxAreaRatio > 0.20)) {
          // 1단계: 초접근 (연속음 + 강한 진동)
          void hapticEngine.trigger("continuous");
          void audioEngine.playBeep(0.0, 0); // 0ms는 정지/연속 반복음
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 초접근 경보! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> continuous / 0ms`);
          }
        } else if (maxAreaRatio > 0.12 || (isHighClass && maxAreaRatio > 0.08)) {
          // 2단계: 근접 (빠른 핑퐁 점멸 + Warning 진동)
          void hapticEngine.trigger("double");
          void audioEngine.playBeep(0.0, 200); // 200ms 고속 점멸
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 근접 주의! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> double / 200ms`);
          }
        } else if (maxAreaRatio > 0.03) {
          // 3단계: 중거리 (일반 점멸 + 단발 진동)
          void hapticEngine.trigger("short");
          void audioEngine.playBeep(0.0, 600); // 600ms 중속 점멸
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 중거리 감지! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> short / 600ms`);
          }
        } else {
          // 4단계: 원거리 (매우 느린 점멸 + 무진동)
          hapticEngine.stopContinuous();
          void audioEngine.playBeep(0.0, 1200); // 1200ms 저속 점멸
          if (!audioEngine.isGuidePlaying) {
            console.log(`[ReflexGate] 원거리 포착! class=${mostCriticalClass} ratio=${maxAreaRatio.toFixed(2)} -> none / 1200ms`);
          }
        }
      } else {
        // 안전 상황: 햅틱 및 비프음 끔
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
    info.push(`캡처: ${isCapturing ? "ON" : "OFF"} (반사 ${currentReflexFps}fps 동적)`);
    info.push(`모델: ${segLoaded ? "seg" : "…"} / ${detLoaded ? "det" : "…"}`);
    if (detShapeLog) info.push(`det shape: ${detShapeLog}`);
    info.push(`추론: ${lastDetect}`);
    setDebugInfo(info);
  }, [isMockMode, permissionStatus, device, status, isCapturing, currentReflexFps, segLoaded, detLoaded, detShapeLog, lastDetect]);

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

  const activeDetections = detections.filter(
    d => d.confidence > getEffectiveConfThreshold(d.className, confThreshold)
  );
  const detectedClassesStr = activeDetections.length > 0
    ? activeDetections.map(d => {
        const areaRatio = (d.bbox.w * d.bbox.h) / (FRAME_SIZE * FRAME_SIZE);
        const dist = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
        return `${d.className} ${dist.toFixed(1)}m (${(d.confidence * 100).toFixed(0)}%)`;
      }).join(", ")
    : "없음";

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
              audio={false}
              style={StyleSheet.absoluteFill}
            />
          )
        )}
        {hapticFlash && <View style={styles.hapticFlash} />}
        {/* BBox 오버레이: 640x640 비율과 1:1 카메라 프레임의 완벽 정합, 신뢰도 임계값 이상만 표시 */}
        <BBoxOverlay detections={activeDetections} />
      </View>

      <View style={styles.overlayTop}>
        <ConnectionStatus status={status} />
      </View>

      <View style={styles.debugOverlay}>
        {debugInfo.map((line, i) => (
          <Text key={i} style={styles.debugText}>{line}</Text>
        ))}
      </View>

      <View style={styles.confThresholdRow}>
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

      <View style={styles.detectionListOverlay}>
        <Text style={styles.detectionListTitle}>[실시간 감지]</Text>
        <Text style={styles.detectionListText}>{detectedClassesStr}</Text>
      </View>

      <Pressable
        style={[styles.sttButton, sttStatus !== "idle" && styles.sttButtonActive]}
        onPressIn={() => {
          void hapticEngine.trigger("short");
          void startSttRecording();
        }}
        onPressOut={() => {
          void stopSttRecording();
        }}
        accessibilityRole="button"
        accessibilityLabel="음성 명령 버튼. 누르고 있는 동안 말하세요."
        accessibilityHint="손을 떼면 서버로 전송되어 음성 명령을 인식합니다."
      >
        <Text style={styles.sttButtonText}>
          {sttStatus === "recording" ? "듣는 중..." : sttStatus === "sending" ? "전송 중..." : "누르고 말하기"}
        </Text>
      </Pressable>

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
  if (HIGH_HAZARDS.includes(className) || className === "caution") {
    return "#EF4444";
  }

  // 지면 관련 위험은 주황색 강제 고정
  if (className === "roadway") {
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
        const areaRatio = (d.bbox.w * d.bbox.h) / (FRAME_SIZE * FRAME_SIZE);
        const distance = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
        // 박스가 화면 밖(음수 좌표 등)으로 나가도 클래스명 라벨은 항상 화면 안쪽에 보이도록
        // 박스 테두리와 라벨의 위치를 분리하고, 라벨 좌표만 [0, 100]%로 clamp한다.
        const labelLeftPct = Math.min(100, Math.max(0, leftPct));
        const labelTopPct = Math.min(100, Math.max(0, topPct));
        // Fragment 사용 필수: 두 절대좌표 View를 감싸는 style 없는 중간 View를 두면
        // 그 View가 0x0으로 collapse되어, 안쪽 %기반 left/top/width/height가 그 0x0
        // 기준으로 계산되어 박스 자체가 안 보이는 회귀가 발생함(실기기 재현 확인, 2026-07-07).
        // 반드시 두 View 모두 바깥 absoluteFill 컨테이너의 직계 자식으로 유지해야 한다.
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
                {d.className} {distance.toFixed(1)}m ({(d.confidence * 100).toFixed(0)}%)
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
    // 실제 캡처/추론 프레임은 640x640 정사각형(디버그로 확인함, 2026-07-06)이므로
    // 미리보기 컨테이너도 1:1 정사각형이어야 BBox 좌표가 화면과 정합한다.
    // 3:4였을 때는 미리보기가 실제 캡처 범위보다 넓게 보여, 박스가 실제 사물보다
    // 훨씬 넓게 그려지는 것처럼 보이는 불일치가 있었다.
    width: "100%",
    aspectRatio: 1,
    overflow: "hidden",
    position: "relative",
    backgroundColor: "#111111",
  },
});
