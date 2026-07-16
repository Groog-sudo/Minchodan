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
import { AppState, Dimensions, Image, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Camera } from "react-native-vision-camera";

import { ConnectionStatus } from "./ConnectionStatus";
import { DebugTriggerPanel } from "./DebugTriggerPanel";
import { NavMapPanel, type NavMapWaypoint } from "./NavMapPanel";
import {
  COGNITIVE_FPS,
  DEFAULT_SERVER_TRANSPORT,
  DEVICE_ID,
  NETWORK_MODE,
  REFLEX_FPS,
  TOKEN,
  type ServerTransport,
} from "../config";
import { MOCK_HAPTIC } from "../config/mock";
import { useCamera, type FrameData } from "../hooks/useCamera";
import { useLocation, type GpsCoords } from "../hooks/useLocation";
import { useOnDeviceDetection, type OnDeviceDetectionResult } from "../hooks/useOnDeviceDetection";
import { useSttRecorder } from "../hooks/useSttRecorder";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  isDepthProbeSupported,
  probeDepth,
  startDepthProbe,
  stopDepthProbe,
  type DepthProbeResult,
} from "../services/depthProbe";
import { getFrameProvider } from "../services/frameProvider";
import { hapticEngine } from "../services/hapticEngine";
import { audioEngine } from "../services/audioEngine";
import { pathObstacleDetector } from "../inference/pathObstacleDetector";
import {
  loadServerTransport,
  saveServerTransport,
  transportAccessibilityLabel,
  transportButtonText,
  transportLabel,
  wsUrlFor,
} from "../services/serverTransport";
import type { StreamType } from "../types/detection";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const FRAME_SIZE = 640;

// GILDANG 브랜드 톤(콘솔 console/src/styles.css의 "Tactical" 다크 테마와 동일 팔레트).
// 탐지 bbox 색상(getClassColor)은 위험도 시맨틱 색상이라 이 팔레트와 무관하게 유지한다.
const COLOR_BG_BASE = "#0A0D10";
const COLOR_BG_SURFACE = "#12161A";
const COLOR_BORDER_TACTICAL = "#222A30";
const COLOR_GILDANG_YELLOW = "#F9B700";
const COLOR_OP_GREEN = "#39FF14";
const COLOR_REFLEX_RED = "#FF3333";
const COLOR_TECH_BLUE = "#00D2FF";
const COLOR_TEXT_BASE = "#EDF2F9";
const COLOR_TEXT_MUTED = "#9DA7BA";
const COLOR_OVERLAY_BG = "rgba(10, 13, 16, 0.85)";

const MOCK_DETECT_MIN_INTERVAL_MS = 1000;
const REAL_DETECT_MIN_INTERVAL_MS = 120;

// 2026-07-11 LiDAR 실거리 프로브(프로토타입) 샘플링 지점: 세로 화면 정규화 좌표.
// bbox 휴리스틱 거리의 기준점(중앙/하단)과 대응시켜 줄자 실측 대조가 쉽게 한다.
const DEPTH_PROBE_POINTS = [
  { label: "중앙", x: 0.5, y: 0.5 },
  { label: "전방 하단", x: 0.5, y: 0.72 },
  { label: "발밑", x: 0.5, y: 0.9 },
];
const DEPTH_PROBE_INTERVAL_MS = 500;

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
// [P3 2026-07-14] 노면 세그 신뢰도 최소값 0.15→0.35 상향 (논문 기준 0.35~0.50).
// 0.15는 너무 낮아 저신뢰 오탐이 실외 판정을 통과해 반사 경보 오발동을 허용했음.
const OUTDOOR_SURFACE_MIN_CONFIDENCE = 0.35;
// 하단 15% (서버 reflex_gate / PROXIMITY_Y와 동일) — 근접 긴급은 outdoor 게이트 우회
const PROXIMITY_BOTTOM_Y = FRAME_SIZE * 0.85;
// 주차센서 면적비: 1단계(초접근) / 2단계(근접) — 이 이상은 실내에서도 즉시 경보
const URGENT_AREA_RATIO = 0.12;
const URGENT_HIGH_CLASS_AREA_RATIO = 0.08;

// 2026-07-14: 씬 판정(isLikelyIndoor) 채터링 완화. 문/창가에서 프레임마다
// 실내↔실외가 뒤집히면 반사 경보도 깜빡이므로, 최근 N프레임 다수결로 안정화한다.
// 서버 DEPARTURE_CONFIRM_STREAK와 같은 "연속/다수 확정" 패턴. iOS 우선 반영.
const SCENE_HYSTERESIS_WINDOW = 5;
const SCENE_INDOOR_MAJORITY = 3;

function stabilizeIsOutdoorByScene(
  rawIsOutdoor: boolean,
  indoorVotes: boolean[],
): boolean {
  // indoorVotes 에는 "실내인가?" 를 쌓는다 (true=실내).
  indoorVotes.push(!rawIsOutdoor);
  if (indoorVotes.length > SCENE_HYSTERESIS_WINDOW) {
    indoorVotes.shift();
  }
  const indoorCount = indoorVotes.filter(Boolean).length;
  const isIndoorStable = indoorCount >= SCENE_INDOOR_MAJORITY;
  return !isIndoorStable;
}

// 2026-07-07 추가: 실내 오탐 완화용 클래스별 최소 confidence.
// YOLO26n det/seg 둘 다 AI Hub 한국 인도(실외) 데이터셋만으로 학습되어 "실내"라는 개념
// 자체를 모른다. 실내에서만 나타날 리 없는(즉 실외 전용) 클래스들이 실내 오탐 시 자주
// 걸리는 대상이라, 전역 confThreshold(사용자 슬라이더, 기본 20%)보다 더 높은 하한선을
// 개별로 강제한다. 목록에 없는 클래스는 confThreshold를 그대로 사용한다.
const CLASS_MIN_CONFIDENCE: Record<string, number> = {
  barricade: 0.35,
  bench: 0.3,
  bicycle: 0.3,
  bollard: 0.3,
  bus: 0.35,
  car: 0.35,
  carrier: 0.3,
  cat: 0.3,
  chair: 0.3,
  dog: 0.3,
  fire_hydrant: 0.35,
  kiosk: 0.3,
  motorcycle: 0.35,
  movable_signage: 0.3,
  parking_meter: 0.35,
  person: 0.3,
  pole: 0.3,
  potted_plant: 0.3,
  power_controller: 0.3,
  scooter: 0.3,
  stop: 0.35,
  stroller: 0.3,
  table: 0.3,
  traffic_light: 0.35,
  traffic_light_controller: 0.35,
  traffic_sign: 0.35,
  tree_trunk: 0.3,
  truck: 0.35,
  wheelchair: 0.3,
  roadway: 0.35,
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

// 주행 통로 ROI 사다리꼴 상수 - server/detection/path_risk.py와 동일 값으로 유지해 좌표 정합.
// NEAR: 화면 하단(가장 가까운 지점) 좌우 경계, FAR: 화면 상단(먼 지점) 좌우 경계.
// FAR_Y_RATIO: ROI 상단이 화면 높이의 35% 지점에서 시작.
const PATH_ROI_NEAR_BAND = [0.20, 0.80] as const; // 정규화 x 좌표 (0~1)
const PATH_ROI_FAR_BAND  = [0.38, 0.62] as const;
const PATH_ROI_FAR_Y_RATIO = 0.35;

/**
 * ROI 사다리꼴 꼭짓점 4개를 정규화 좌표(0~1)로 반환.
 * 순서: 좌상 -> 우상 -> 우하 -> 좌하 (시계 방향)
 */
function roiPolygon(): [number, number][] {
  const [nearLo, nearHi] = PATH_ROI_NEAR_BAND;
  const [farLo, farHi] = PATH_ROI_FAR_BAND;
  const yTop = PATH_ROI_FAR_Y_RATIO;
  const yBottom = 1.0;
  return [
    [farLo,  yTop],    // 좌상
    [farHi,  yTop],    // 우상
    [nearHi, yBottom], // 우하
    [nearLo, yBottom], // 좌하
  ];
}

/**
 * 점(px, py)이 볼록 다각형 polygon(정규화 좌표 배열) 내부에 있는지 판정.
 * ray-casting 알고리즘 사용.
 */
function pointInPolygon(px: number, py: number, polygon: [number, number][]): boolean {
  let inside = false;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersect =
      yi > py !== yj > py &&
      px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function isGeometricallyImplausible(bbox: { w: number; h: number }): boolean {
  const maxSize = FRAME_SIZE * CANVAS_OVERFLOW_MARGIN;
  return bbox.w > maxSize || bbox.h > maxSize;
}

function detectionAreaRatio(bbox: { w: number; h: number }): number {
  return (bbox.w * bbox.h) / (FRAME_SIZE * FRAME_SIZE);
}

function isBottomProximity(bbox: { x: number; y: number; w: number; h: number }): boolean {
  return bbox.y + bbox.h >= PROXIMITY_BOTTOM_Y;
}

/** 초접근/근접 — LLM/실외 게이트 없이 즉시 비프·햅틱 대상 */
function isProximityUrgent(
  bbox: { x: number; y: number; w: number; h: number },
  className: string,
): boolean {
  if (isBottomProximity(bbox)) return true;
  const ratio = detectionAreaRatio(bbox);
  const isHigh =
    HIGH_HAZARDS.includes(className) || GROUND_HAZARDS.includes(className);
  if (ratio > URGENT_AREA_RATIO) return true;
  if (isHigh && ratio > URGENT_HIGH_CLASS_AREA_RATIO) return true;
  return false;
}

type Direction = "front-left" | "front" | "front-right";

/**
 * BBox의 좌우 점유 및 거리를 기준으로 시각장애인 충돌 회랑 방향(3분대)을 산출합니다.
 */
function estimateDirection(
  bbox: { x: number; w: number },
  frameWidth: number,
): Direction {
  if (frameWidth <= 0) return "front";
  const xMin = bbox.x;
  const xMax = bbox.x + bbox.w;
  const xMinN = xMin / frameWidth;
  const xMaxN = xMax / frameWidth;

  const frontLo = 0.20;
  const frontHi = 0.80;

  if (xMaxN >= frontLo && xMinN <= frontHi) {
    return "front";
  }
  return xMaxN < frontLo ? "front-left" : "front-right";
}

/**
 * 온디바이스 주차센서식 비프/햅틱 (LLM 미경유).
 * @returns 경보를 올렸으면 true
 */
function applyLocalAreaReflex(
  detections: OnDeviceDetectionResult[],
  logTag: string,
  lastLocalVoiceClipTs: Record<string, number>,
): boolean {
  if (detections.length === 0) return false;

  let maxAreaRatio = 0;
  let mostCriticalClass = "";
  let nearestLidarDetection: OnDeviceDetectionResult | null = null;
  let nearestLidarMeters = Number.POSITIVE_INFINITY;
  let mostCriticalDetection: OnDeviceDetectionResult | null = null;

  for (const d of detections) {
    const ratio = detectionAreaRatio(d.bbox);
    if (ratio > maxAreaRatio) {
      maxAreaRatio = ratio;
      mostCriticalClass = d.className;
      mostCriticalDetection = d;
    }
    const resolvedDistance = resolveDetectionDistance(d);
    if (
      resolvedDistance.source === "lidar" &&
      resolvedDistance.meters !== null &&
      resolvedDistance.meters < nearestLidarMeters
    ) {
      nearestLidarMeters = resolvedDistance.meters;
      nearestLidarDetection = d;
    }
  }

  const log = (msg: string) => {
    if (!audioEngine.isGuidePlaying) {
      console.log(`[LocalReflex]${logTag} ${msg}`);
    }
  };

  const targetDet = nearestLidarDetection || mostCriticalDetection;
  let direction: Direction = "front";
  if (targetDet) {
    direction = estimateDirection(targetDet.bbox, FRAME_SIZE);
  }

  const playLocalReflexClip = (beepIntervalMs: number) => {
    if (beepIntervalMs > 100 && targetDet) {
      const nowTs = Date.now();
      const lastPlay = lastLocalVoiceClipTs[direction] || 0;
      if (nowTs - lastPlay >= 3000) { // 동일 방향 경고 최소 3초 간격 보장 (쿨다운)
        lastLocalVoiceClipTs[direction] = nowTs;
        const clipName = `reflex_clips/high_${direction}.wav`;
        void audioEngine.playReflexClip(clipName);
      }
    }
  };

  if (nearestLidarDetection !== null) {
    const lidarClass = nearestLidarDetection.className;
    const samples = nearestLidarDetection.depthSampleCount ?? 0;
    if (nearestLidarMeters <= 0.5) {
      void hapticEngine.trigger("continuous");
      void audioEngine.playBeep(0.0, 0);
      log(`[LiDAR] 초접근 class=${lidarClass} d=${nearestLidarMeters.toFixed(2)}m samples=${samples}`);
      return true;
    }
    if (nearestLidarMeters <= 1.0) {
      void hapticEngine.trigger("double");
      void audioEngine.playBeep(0.0, 200);
      playLocalReflexClip(200);
      log(`[LiDAR] 근접 class=${lidarClass} d=${nearestLidarMeters.toFixed(2)}m samples=${samples}`);
      return true;
    }
    if (nearestLidarMeters <= 1.5) {
      void hapticEngine.trigger("short");
      void audioEngine.playBeep(0.0, 600);
      playLocalReflexClip(600);
      log(`[LiDAR] 중거리 class=${lidarClass} d=${nearestLidarMeters.toFixed(2)}m samples=${samples}`);
      return true;
    }
    if (nearestLidarMeters <= 3.0) {
      hapticEngine.stopContinuous();
      void audioEngine.playBeep(0.0, 1200);
      playLocalReflexClip(1200);
      log(`[LiDAR] 원거리 class=${lidarClass} d=${nearestLidarMeters.toFixed(2)}m samples=${samples}`);
      return true;
    }
    hapticEngine.stopContinuous();
    void audioEngine.stopBeep();
    return false;
  }

  // 💡 [설계 의도] 클래스 종류와 독립적(class-agnostic)으로 BBox 크기(면적비)만으로 온디바이스 반사 피드백을 제어합니다.
  if (maxAreaRatio > 0.20) {
    void hapticEngine.trigger("continuous");
    void audioEngine.playBeep(0.0, 0);
    log(`초접근 ratio=${maxAreaRatio.toFixed(2)}`);
    return true;
  }
  if (maxAreaRatio > 0.08) {
    void hapticEngine.trigger("double");
    void audioEngine.playBeep(0.0, 200);
    playLocalReflexClip(200);
    log(`근접 ratio=${maxAreaRatio.toFixed(2)}`);
    return true;
  }
  if (maxAreaRatio > 0.03) {
    void hapticEngine.trigger("short");
    void audioEngine.playBeep(0.0, 600);
    playLocalReflexClip(600);
    log(`중거리 ratio=${maxAreaRatio.toFixed(2)}`);
    return true;
  }
  hapticEngine.stopContinuous();
  void audioEngine.playBeep(0.0, 1200);
  playLocalReflexClip(1200);
  log(`원거리 ratio=${maxAreaRatio.toFixed(2)}`);
  return true;
}

type DistanceSource = "lidar" | "heuristic" | "none";

interface DetectionDistanceInput {
  bbox: { w: number; h: number };
  distanceMeters?: number | null;
  distanceSource?: DistanceSource;
  depthSampleCount?: number;
}

interface ResolvedDetectionDistance {
  meters: number | null;
  source: DistanceSource;
  label: "LiDAR" | "추정" | "거리없음";
  depthSampleCount?: number;
}

function isUsableMeters(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function estimateHeuristicDistanceMeters(detection: DetectionDistanceInput): number | null {
  const areaRatio = (detection.bbox.w * detection.bbox.h) / (FRAME_SIZE * FRAME_SIZE);
  if (!Number.isFinite(areaRatio) || areaRatio <= 0) return null;
  return Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
}

function resolveDetectionDistance(detection: DetectionDistanceInput): ResolvedDetectionDistance {
  if (isUsableMeters(detection.distanceMeters)) {
    if (detection.distanceSource === "heuristic") {
      return {
        meters: detection.distanceMeters,
        source: "heuristic",
        label: "추정",
      };
    }
    if (detection.distanceSource === "none") {
      return {
        meters: null,
        source: "none",
        label: "거리없음",
      };
    }
    return {
      meters: detection.distanceMeters,
      source: "lidar",
      label: "LiDAR",
      depthSampleCount: detection.depthSampleCount,
    };
  }

  const heuristicMeters = estimateHeuristicDistanceMeters(detection);
  if (heuristicMeters !== null) {
    return {
      meters: heuristicMeters,
      source: "heuristic",
      label: "추정",
    };
  }

  return {
    meters: null,
    source: "none",
    label: "거리없음",
  };
}

export function CameraView() {
  const [debugInfo, setDebugInfo] = useState<string[]>([]);
  const [lastDetect, setLastDetect] = useState<string>("대기");
  const [hapticFlash, setHapticFlash] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<number | null>(null);
  const [detections, setDetections] = useState<OnDeviceDetectionResult[]>([]);
  const [confThreshold, setConfThreshold] = useState(0.35);
  // 2026-07-13 th: 상시 캡처/서버 전송이 실기기에서 과부하·캡처 오류를 유발해
  // 기본은 중지, "탐지 시작" 버튼으로만 루프를 켠다(STT press-and-hold와 독립).
  const [detectionEnabled, setDetectionEnabled] = useState(false);

  // 평상시 WiFi / 개발 USB — 둘 다 설정에 두고 토글로 전환 (재시작 후에도 유지).
  const [serverTransport, setServerTransport] = useState<ServerTransport>(DEFAULT_SERVER_TRANSPORT);
  const [transportReady, setTransportReady] = useState(false);
  useEffect(() => {
    void loadServerTransport().then((t) => {
      // Expo 환경값의 기본 수송 경로를 시작 정책으로 삼는다.
      // 유선 테스트는 usb(127.0.0.1 + adb reverse), 핫스팟/LAN 테스트는 wifi.
      const initialTransport: ServerTransport = DEFAULT_SERVER_TRANSPORT || t;
      if (t !== initialTransport) {
        void saveServerTransport(initialTransport);
        console.log(`[ServerTransport] 시작 기본값 적용: ${transportLabel(initialTransport)}`);
      }
      setServerTransport(initialTransport);
      setTransportReady(true);
    });
  }, []);
  const wsBaseUrl = wsUrlFor(serverTransport);
  const {
    status,
    send,
    sendBinary,
    lastMessage,
    navRoute,
    setSttInteractionActive,
    networkRttMs,
    networkRttAvgMs,
  } = useWebSocket(
    DEVICE_ID,
    TOKEN,
    transportReady ? wsBaseUrl : wsUrlFor(DEFAULT_SERVER_TRANSPORT),
  );
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
  // STT 음성 명령: 단말은 마이크 캡처만 담당, 인식은 서버(stt_audio 핸들러)가 수행.
  // 2026-07-10: Release 빌드는 console 출력이 안 보여 실기기에서 원인 파악이 불가능했다
  // - 에러 상세를 화면에 직접 표시(sttErrorInfo)해 즉시 읽을 수 있게 한다.
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
      if (status !== "connected") {
        void hapticEngine.trigger("double");
        setSttErrorInfo(`STT 실패[ws_disconnected]: websocket 상태=${status}`);
        audioEngine.speakFallback("서버 연결이 불안정해 음성 명령을 전송할 수 없습니다.");
        return;
      }
      void hapticEngine.trigger("short");
      setSttErrorInfo("");
      send({ type: "stt_audio", audio_b64: audioB64 });
    },
    (reason, detail) => {
      void hapticEngine.trigger("double");
      setSttErrorInfo(`STT 실패[${reason}]: ${detail ?? "-"}`);
    },
  );

  // 화면을 누르는 press-and-hold 도중 마이크 권한 다이얼로그가 뜨면 터치가 취소되어
  // 첫 시도가 항상 실패하므로, 진입 시 미리 권한을 확보한다.
  useEffect(() => {
    if (isMockMode) return;
    void requestSttPermissionEarly();

    // 앱이 포그라운드(active) 상태로 복귀(리로드)할 때 마이크 권한을 재확인하여 실시간 동기화
    const subscription = AppState.addEventListener("change", (nextAppState) => {
      if (nextAppState === "active") {
        void requestSttPermissionEarly();
      }
    });

    return () => {
      subscription.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // 2026-07-11 하단 T맵 지도 패널(운영자/데모용): 정적 표시 + 2초 마커 갱신 + 토글.
  // 꺼져 있으면 WebView를 마운트하지 않아 단말 부하가 없다.
  // 경로 데이터(navRoute)는 useWebSocket이 전용 상태로 직접 보존한다
  // (lastMessage 경유 시 고빈도 메시지에 덮여 유실 - 실기기 확인).
  const [mapVisible, setMapVisible] = useState(false);
  const [mapPos, setMapPos] = useState<NavMapWaypoint | null>(null);
  const lastMapPosTsRef = useRef(0);

  // GPS 전송: 앱 부팅 직후부터 watch를 시작해 공기계의 첫 GPS fix 지연을 줄인다.
  // 네비게이션 경로 이탈/웨이포인트 판정은 전부 서버(NavigationFilter)가
  // 수행하므로, 클라이언트는 좌표를 주기적으로 realtime_gps 메시지로 보내기만 한다.
  // Mock 모드는 시뮬레이터 좌표가 무의미하므로 제외.
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
        // 지도 마커 갱신은 2초 스로틀(WebView 주입 빈도 제한, 성능 합의 사항).
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMockMode]);

  // State variables moved to top of Component to avoid block-scope/TDZ errors.

  // 탐지 토글을 서버에 동기화: OFF면 STT가 자유 질문으로 가고, 목적지/인텐트 대기를 푼다.
  // WS 재연결 후에도 현재 토글 값을 다시 보낸다.
  useEffect(() => {
    if (status !== "connected") return;
    send({ type: "detection_control", enabled: detectionEnabled, ts: Date.now() });
  }, [status, detectionEnabled, send]);

  useEffect(() => {
    if (!navRoute) {
      setMapVisible(false);
    }
  }, [navRoute]);

  // 2026-07-11 LiDAR 실거리 프로브 모드(프로토타입, iOS Pro 계열 전용, Mitos 로드맵 §2):
  // 켜면 vision-camera를 내리고(isActive=false, 두 세션이 후면 카메라를 공유할 수 없는
  // 프로토타입 제약) 자체 심도 세션으로 화면 3지점의 실거리를 표시한다. bbox 휴리스틱
  // 거리와의 교차 검증(줄자 실측 대조)용 계측 화면이며, 탐지·경보는 이 모드 동안 정지한다.
  const [depthMode, setDepthMode] = useState(false);
  const [depthResult, setDepthResult] = useState<DepthProbeResult | null>(null);
  const [depthError, setDepthError] = useState<string | null>(null);

  // 탐지 토글을 서버에 동기화: OFF면 STT가 자유 질문으로 가고, 목적지/인텐트 대기를 푼다.
  // WS 재연결 후에도 현재 토글 값을 다시 보낸다. 계측용 거리측정 모드에서는 탐지를 일시 정지한다.
  useEffect(() => {
    if (status !== "connected") return;
    send({ type: "detection_control", enabled: detectionEnabled && !depthMode, ts: Date.now() });
  }, [status, detectionEnabled, depthMode, send]);

  useEffect(() => {
    if (!depthMode) return;
    let cancelled = false;
    let timerId: ReturnType<typeof setInterval> | null = null;
    (async () => {
      // vision-camera가 isActive=false 렌더로 세션을 놓을 시간을 준 뒤 프로브를 켠다.
      await new Promise((resolve) => setTimeout(resolve, 500));
      if (cancelled) return;
      const started = await startDepthProbe();
      if (cancelled) {
        void stopDepthProbe();
        return;
      }
      if (!started.ok) {
        setDepthError(started.error ?? "프로브 시작 실패");
        return;
      }
      setDepthError(null);
      timerId = setInterval(async () => {
        const result = await probeDepth(DEPTH_PROBE_POINTS);
        if (!cancelled && result) {
          setDepthResult(result);
          // 실측 기록용(Release 빌드에서는 미출력) - 시나리오 기록은 화면 판독으로 수행
          console.log(
            `[DepthProbe] acc=${result.accuracy} quality=${result.quality} ` +
              `calibrated=${result.calibrated === true} ` +
              result.samples
                .map(
                  (s, i) =>
                    `${DEPTH_PROBE_POINTS[i]?.label}=${s.meters?.toFixed(2) ?? "-"}m` +
                    `(z=${s.axialMeters?.toFixed(2) ?? "-"}m)`,
                )
                .join(", "),
          );
        }
      }, DEPTH_PROBE_INTERVAL_MS);
    })();
    return () => {
      cancelled = true;
      if (timerId) {
        clearInterval(timerId);
      }
      void stopDepthProbe();
      setDepthResult(null);
      setDepthError(null);
    };
  }, [depthMode]);

  // 서버 실시간 웹소켓 추론 결과 수신 시 화면 상태 업데이트
  useEffect(() => {
    if (!lastMessage) return;

    lastServerResponseTsRef.current = Date.now();

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
    } else if (lastMessage.type === "server_detection") {
      const serverDets = lastMessage.detections ?? [];
      // 서버가 mock 탐지기이거나 해당 프레임에서 무탐지인 경우 빈 배열을
      // 수신하더라도, 온디바이스 결과를 지워 BBox가 사라지지 않게 한다.
      if (serverDets.length > 0) setDetections(serverDets);
    }
  }, [lastMessage]);

  // Stale Closure 방지용 useRef 미러: setInterval 콜백은 등록 시점의 값을 캡처하므로
  // 최신 상태는 반드시 ref 를 통해 읽어야 한다.
  const lastFrameSentTsRef = useRef(0);
  const lastServerResponseTsRef = useRef(0);
  const localReflexStreakRef = useRef(0);
  const lastLocalVoiceClipTsRef = useRef<Record<string, number>>({
    front: 0,
    "front-left": 0,
    "front-right": 0,
  });
  const detectFrameRef = useRef(detectFrame);
  const isModelsLoadedRef = useRef(isModelsLoaded);
  const isMockModeRef = useRef(isMockMode);
  // 2026-07-11: WS 연결 상태를 ref로 추적해 handleFrame 클로저 안에서 최신값을 읽는다.
  // 폴백 모드에서 온디바이스 추론 결과를 BBox로 표시하기 위해 필요하다.
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
  // 2026-07-13: 온디바이스 씬 분류(scene.isLikelyIndoor) 기반 실외 추정치를 서버로 전달하기
  // 위한 ref. 이번 프레임 전송 시점엔 아직 이번 프레임의 온디바이스 추론이 끝나지 않았으므로
  // "직전 프레임"에서 계산된 값을 1프레임 지연 허용하고 보낸다(1~2fps 인지 경로 기준 무시할
  // 만한 지연). 서버는 이 값으로 세그멘테이션 기반 보도 이탈 판정을 게이팅한다
  // (server/detection/detection_pipeline.py, 실내 바닥이 roadway/caution으로 오분류되는
  // 문제를 실기기 실측으로 확인).
  const isOutdoorBySceneRef = useRef<boolean | null>(null);
  // 씬 히스테리시스용 최근 N프레임 "실내" 투표 버퍼 (true=실내).
  const sceneIndoorVotesRef = useRef<boolean[]>([]);
  const lastAndroidTtsTsRef = useRef(0);

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
    // 2026-07-11 event_id 구조화(dev 개선 계획서 §3): 기존 `event-${now}`는 ms 단위라
    // 반사/인지 두 캡처 타이머가 같은 ms에 발화하면 event_id가 충돌했고, 서버 DB의
    // event_id UNIQUE + 중복 저장 방지 로직(detection_guidance_log_service)이 두 번째
    // 프레임 로그를 조용히 버렸다. device_id와 stream을 포함해 충돌을 제거한다.
    const frameStream = frame.stream ?? "reflex";
    const eventId = `event-${DEVICE_ID}-${frameStream}-${now}`;

    // 로컬 추론 엔진 적재 여부와 관계없이 서버로 프레임 전송 수행 (WebSocket)
    // raw JPEG 바이트가 있으면(실기기) base64를 경유하지 않고 메타데이터(JSON) + 바이너리
    // 프레임 2개를 순차 전송한다. 단일 WS 연결에서 프레임 순서는 보장되므로 서버는
    // "transport: binary" 메타 수신 직후 오는 바이너리 프레임을 해당 이벤트로 매칭한다.
    if (frame.jpegBytes && sendRef.current && sendBinaryRef.current) {
      sendRef.current({
        type: "detection",
        payload: {
          event_id: eventId,
          device_id: DEVICE_ID,
          frame_id: now,
          stream: frameStream,
          transport: "binary",
          is_outdoor: isOutdoorBySceneRef.current,
        }
      });
      sendBinaryRef.current(frame.jpegBytes);
      lastFrameSentTsRef.current = now;
    } else if (frame.base64 && sendRef.current) {
      // 폴백(Mock 등 jpegBytes 미지원 경로): 기존 base64 방식 유지
      sendRef.current({
        type: "detection",
        payload: {
          event_id: eventId,
          device_id: DEVICE_ID,
          frame_id: now,
          thumbnail_jpeg_b64: frame.base64,
          stream: frameStream,
          is_outdoor: isOutdoorBySceneRef.current,
        }
      });
      lastFrameSentTsRef.current = now;
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

      // BBox는 연결 상태와 무관하게 최신 온디바이스 결과를 표시한다.
      // 서버 server_detection 결과가 존재하면 위 수신 핸들러가 이를 덮어쓴다.
      setDetectionsRef.current(allDetections);

      // 1. 공통 전처리: 기하/신뢰도 1차 → 근접 긴급은 outdoor 우회, 중·원거리만 실외 게이트
      const hasOutdoorSurface = (seg as OnDeviceDetectionResult[]).some(
        (d: OnDeviceDetectionResult) =>
          OUTDOOR_SURFACE_CLASSES.includes(d.className) &&
          d.confidence >= OUTDOOR_SURFACE_MIN_CONFIDENCE,
      );
      // scene 미존재(허용적 폴백)면 히스테리시스 없이 실외로 간주해 기존 co-occurrence만 사용.
      const rawIsOutdoorByScene = scene ? !scene.isLikelyIndoor : true;
      const isOutdoorByScene = scene
        ? stabilizeIsOutdoorByScene(rawIsOutdoorByScene, sceneIndoorVotesRef.current)
        : true;
      isOutdoorBySceneRef.current = isOutdoorByScene;
      if (__DEV__ && scene) {
        console.log(
          `[SceneHysteresis] rawOutdoor=${rawIsOutdoorByScene} stableOutdoor=${isOutdoorByScene} ` +
            `indoorVotes=${sceneIndoorVotesRef.current.filter(Boolean).length}/${sceneIndoorVotesRef.current.length}`,
        );
      }

      const roiPoly = roiPolygon();
      const baseCandidates = allDetections.filter((d: OnDeviceDetectionResult) => {
        if (SAFE_SURFACE_CLASSES.includes(d.className)) return false;
        if (GROUND_HAZARDS.includes(d.className)) return false; // 바닥(roadway/caution)은 반사 경로 제외 - 인지 경로(TTS) 전담
        if (isGeometricallyImplausible(d.bbox)) return false;
        if (d.confidence <= getEffectiveConfThreshold(d.className, confThresholdRef.current)) {
          return false;
        }
        // ROI 판정: bbox 중심점이 주행 통로 사다리꼴 내부에 없으면 반사 경로 제외.
        // outdoor 게이트(hasOutdoorSurface/isOutdoorByScene)는 여기서 걸지 않는다 - 근접 긴급
        // (urgentDetections)은 실내 판정이어도 충돌 회피가 우선이라 outdoor 게이트를 우회해야 한다.
        const cxNorm = (d.bbox.x + d.bbox.w / 2) / FRAME_SIZE;
        const cyNorm = (d.bbox.y + d.bbox.h / 2) / FRAME_SIZE;
        if (!pointInPolygon(cxNorm, cyNorm, roiPoly)) return false;
        return true;
      });
      const urgentDetections = baseCandidates.filter((d) =>
        isProximityUrgent(d.bbox, d.className),
      );
      // 중·원거리 점진 비프: 실외 신호가 있을 때만 (실내 차량 오탐 억제)
      const outdoorScopedDetections =
        hasOutdoorSurface && isOutdoorByScene
          ? baseCandidates.filter((d) => !isProximityUrgent(d.bbox, d.className))
          : [];
      const reflexDetections =
        urgentDetections.length > 0
          ? urgentDetections
          : outdoorScopedDetections;

      // 2. 단일 프레임 오탐 방지를 위한 연속 4프레임 안정화 필터 적용
      if (reflexDetections.length > 0) {
        localReflexStreakRef.current += 1;
      } else {
        localReflexStreakRef.current = 0;
      }
      
      const maxAreaRatio = reflexDetections.reduce((max, d) => {
        const ratio = detectionAreaRatio(d.bbox);
        return ratio > max ? ratio : max;
      }, 0);

      const requiredStreak = maxAreaRatio > 0.20 ? 1 : 4;
      const isReflexStable = localReflexStreakRef.current >= requiredStreak;
      const stableReflexDetections = isReflexStable ? reflexDetections : [];

      // 3. WebSocket 연결 끊김/타임아웃(300ms 초과) 감지 (마지막 수신 타임스탬프 기준)
      const isServerTimeout = wsStatusRef.current !== "connected" ||
        (lastFrameSentTsRef.current > lastServerResponseTsRef.current &&
         now - lastServerResponseTsRef.current > 300);

      let pathRaisedAlert = false;
      if (Platform.OS === "android") {
        if (!isServerTimeout) {
          // 4. 서버 정상 시 중복 경보 방지를 위해 온디바이스 반사 경보 억제 및 사운드 즉각 회수
          hapticEngine.stopContinuous();
          void audioEngine.stopBeep();
          if (!audioEngine.isGuidePlaying && __DEV__) {
            console.log("[LocalReflex] 서버 연결 정상 — 온디바이스 반사 경보 억제");
          }
        } else if (!isOutdoorByScene) {
          hapticEngine.stopContinuous();
          void audioEngine.stopBeep();
          if (__DEV__) {
            console.log("[PathObstacle] 실내 씬 판정 — 통로 경보 억제");
          }
        } else {
          const pathRes = pathObstacleDetector.analyze(allDetections);

          if (pathRes.state === "STOP") {
            void hapticEngine.trigger("double");
            void audioEngine.playBeep(0.0, 0);
            pathRaisedAlert = true;
            if (!audioEngine.isGuidePlaying) {
              console.log(
                `[LocalReflex][PathObstacle] STOP score=${pathRes.riskScore.toFixed(2)}`,
              );
            }
          } else if (pathRes.state === "BLOCKED") {
            void hapticEngine.trigger("short");
            void audioEngine.playBeep(0.0, 200);
            pathRaisedAlert = true;
            if (!audioEngine.isGuidePlaying) {
              console.log(
                `[LocalReflex][PathObstacle] BLOCKED score=${pathRes.riskScore.toFixed(2)}`,
              );
            }
          } else if (pathRes.state === "CAUTION") {
            void audioEngine.playBeep(0.0, 600);
            pathRaisedAlert = true;
            if (!audioEngine.isGuidePlaying) {
              console.log(
                `[LocalReflex][PathObstacle] CAUTION score=${pathRes.riskScore.toFixed(2)}`,
              );
            }
          } else if (stableReflexDetections.length > 0) {
            // path CLEAR 이어도 가까운 사람/의자 등은 즉시 경보 (실내 포함)
            applyLocalAreaReflex(stableReflexDetections, "[AndroidFallback]", lastLocalVoiceClipTsRef.current);
            pathRaisedAlert = true;
          } else {
            hapticEngine.stopContinuous();
            void audioEngine.stopBeep();
          }

          const nowTs = Date.now();
          if (
            pathRaisedAlert &&
            (pathRes.state === "STOP" || pathRes.state === "BLOCKED") &&
            !audioEngine.isGuidePlaying &&
            nowTs - lastAndroidTtsTsRef.current >= 2500
          ) {
            lastAndroidTtsTsRef.current = nowTs;
            let guidanceText = "정면 장애물";
            if (pathRes.bestTurn === "left") {
              guidanceText = "정면 장애물, 왼쪽 공간 넓음";
            } else if (pathRes.bestTurn === "right") {
              guidanceText = "정면 장애물, 오른쪽 공간 넓음";
            }
            audioEngine.speakFallback(guidanceText);
            console.log(
              `[LocalReflex][PathObstacle] 회피 가이드: "${guidanceText}" (L: ${pathRes.leftClearance.toFixed(1)}m, R: ${pathRes.rightClearance.toFixed(1)}m)`,
            );
          }
        }
      } else {
        // iOS: iOS관련 파일 수정 금지 제약이 있으므로, CameraView.tsx 내의 iOS 분기 로직은 최소한으로 우선순위 게이트만 씌움
        if (!isServerTimeout) {
          // 서버 정상 시 온디바이스 반사 경보 억제 및 사운드 즉각 회수
          hapticEngine.stopContinuous();
          void audioEngine.stopBeep();
        } else if (stableReflexDetections.length > 0) {
          applyLocalAreaReflex(stableReflexDetections, "[iOS]", lastLocalVoiceClipTsRef.current);
        } else {
          hapticEngine.stopContinuous();
          void audioEngine.stopBeep();
        }
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
    } finally {
      detectingRef.current = false;
    }
  }, []); // 의존성 없음 - 모든 최신 상태를 ref 로 직접 참조

  // 캡처 시작: 기본 OFF. "탐지 시작"으로 detectionEnabled=true일 때만 루프 기동.
  // (상시 기동은 실기기 과부하·캡처 오류 유발 - 2026-07-13 th)
  useEffect(() => {
    if (!detectionEnabled || depthMode) {
      stopCapture();
      setDetections([]);
      return;
    }
    if (!isMockMode && !hasPermission) return;
    if (!isMockMode && !device) return;
    if (isCapturing) return;

    startCapture((frame: FrameData) => {
      void handleFrame(frame, frame.stream ?? "reflex");
    });
    return () => stopCapture();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMockMode, hasPermission, device, detectionEnabled, depthMode]);

  useEffect(() => {
    const info: string[] = [];
    info.push(`모드: ${isMockMode ? "MOCK(시뮬레이터)" : "REAL(실기기)"}`);
    info.push(`권한: ${permissionStatus}`);
    if (!isMockMode) info.push(`카메라: ${device ? device.id : "없음"}`);
    info.push(`WS: ${status} / ${transportLabel(serverTransport)}`);
    if (networkRttMs !== null) {
      info.push(`망RTT: ${networkRttMs}ms (평균 ${networkRttAvgMs ?? "-"}ms)`);
    }
    info.push(`캡처: ${isCapturing ? "ON" : "OFF"} (탐지토글 ${detectionEnabled ? "ON" : "OFF"}, 반사 ${currentReflexFps}fps 동적)`);
    info.push(`모델: ${segLoaded ? "seg" : "…"} / ${detLoaded ? "det" : "…"}`);
    if (detShapeLog) info.push(`det shape: ${detShapeLog}`);
    info.push(`추론: ${lastDetect}`);
    setDebugInfo(info);
  }, [isMockMode, permissionStatus, device, status, serverTransport, networkRttMs, networkRttAvgMs, isCapturing, currentReflexFps, segLoaded, detLoaded, detShapeLog, lastDetect]);

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

  const activeDetections = depthMode
    ? []
    : detections.filter(
      d => d.confidence > getEffectiveConfThreshold(d.className, confThreshold)
    );
  const detectedClassesStr = activeDetections.length > 0
    ? activeDetections.map(d => {
      const distance = resolveDetectionDistance(d);
      const distanceText = distance.meters !== null ? `${distance.meters.toFixed(1)}m ${distance.label}` : distance.label;
      return `${d.className} ${distanceText} (${(d.confidence * 100).toFixed(0)}%)`;
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
          !isMockMode &&
          (useStreamCapture ? (
            // 프레임 프로세서 경로(기본값, 2026-07-09): AVCapturePhotoOutput을 세션에
            // 붙이지 않아(photo 미지정) 촬영마다 발생하던 AVAudioSessionInterruption을
            // 원천 제거한다. 플랫폼별 구현: client/src/services/frameCaptureProviderSelect.ios.ts
            <Camera
              ref={cameraRef}
              device={device!}
              // 의도(2026-07-13): 탐지 시작 전=카메라 세션 OFF(검은 화면),
              // 탐지 시작 후=프리뷰 ON. 부하 절감 + "탐지 중" 상태를 화면으로 구분.
              isActive={detectionEnabled && !depthMode}
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
              isActive={detectionEnabled && !depthMode}
              photo={true}
              audio={false}
              style={StyleSheet.absoluteFill}
            />
          ))
        )}
        {depthMode && depthResult?.previewUri ? (
          <Image
            source={{ uri: depthResult.previewUri }}
            style={StyleSheet.absoluteFill}
            resizeMode="cover"
          />
        ) : null}
        {depthMode && !depthResult?.previewUri && (
          <View style={styles.detectionIdleBanner} pointerEvents="none">
            <Text style={styles.detectionIdleText}>
              LiDAR 프리뷰 준비 중...
            </Text>
          </View>
        )}
        {depthMode && <DepthProbeMarkers result={depthResult} />}
        {!depthMode && !detectionEnabled && !isMockMode && (
          <View style={styles.detectionIdleBanner} pointerEvents="none">
            <Text style={styles.detectionIdleText}>
              탐지 대기 중 (카메라 OFF) — 아래 &quot;탐지 시작&quot;을 누르면 화면이 켜집니다
            </Text>
          </View>
        )}
        {hapticFlash && <View style={styles.hapticFlash} />}
        {/* ROI 사다리꼴 오버레이: 주행 통로 시각화 (탐지 활성 시에만 표시) */}
        {detectionEnabled && !depthMode && <ROIOverlay />}
        {/* BBox 오버레이: 640x640 비율과 1:1 카메라 프레임의 완벽 정합, 신뢰도 임계값 이상만 표시 */}
        <BBoxOverlay detections={activeDetections} />

        {/* STT press-and-hold: 카메라 프리뷰(1:1) 위에서만 동작. 하단 운영자 패널 버튼과 터치 충돌 방지. */}
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
          accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? "활성" : "비활성"}. 카메라 화면을 누르고 있는 동안 음성 명령을 말하세요.`}
          accessibilityHint="손을 떼면 서버로 전송되어 음성 명령을 인식합니다."
        />
      </View>

      {/* 운영자/모니터링 UI: 카메라 시야(1:1) 아래 여백으로 분리 */}
      <ScrollView
        style={styles.operatorPanel}
        contentContainerStyle={styles.operatorPanelContent}
        keyboardShouldPersistTaps="handled"
      >
        <ConnectionStatus status={status} />

        <View style={styles.operatorCard} pointerEvents="none">
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

        <View style={styles.detectionListCard} pointerEvents="none">
          <Text style={styles.detectionListTitle}>[실시간 감지]</Text>
          <Text style={styles.detectionListText}>{detectedClassesStr}</Text>
        </View>

        <View
          style={[styles.sttButton, sttStatus !== "idle" && styles.sttButtonActive]}
          pointerEvents="none"
        >
          <Text style={[styles.sttButtonText, sttStatus !== "idle" && styles.sttButtonTextActive]}>
            {sttStatus === "recording" ? "듣는 중..." : sttStatus === "sending" ? "전송 중..." : "카메라 화면을 누르고 말하기"}
          </Text>
          {sttErrorInfo !== "" && (
            <Text style={styles.sttErrorText}>{sttErrorInfo}</Text>
          )}
        </View>

        {depthMode && (
          <View style={styles.operatorCard} pointerEvents="none">
            <Text style={styles.depthTitle}>
              LiDAR 실거리 (동기화·보정: {depthResult?.calibrated ? "적용" : "대기"}, 정확도:{" "}
              {depthResult?.accuracy ?? "-"}, 품질: {depthResult?.quality ?? "-"})
            </Text>
            {depthError ? (
              <Text style={styles.depthError}>{depthError}</Text>
            ) : (
              DEPTH_PROBE_POINTS.map((point, i) => {
                const sample = depthResult?.samples?.[i];
                return (
                  <Text key={point.label} style={styles.depthRow}>
                    {point.label}:{" "}
                    {sample && sample.meters != null
                      ? `${sample.meters.toFixed(2)} m ` +
                        `(원본 z ${sample.axialMeters?.toFixed(2) ?? "-"} m, ` +
                        `${sample.sampleCount ?? 0})`
                      : "측정 불가"}
                  </Text>
                );
              })
            )}
          </View>
        )}

        {navRoute && (
          <Pressable
            style={styles.mapToggleButton}
            onPress={() => setMapVisible((v) => !v)}
            accessibilityRole="button"
            accessibilityLabel={mapVisible ? "지도 끄기" : "지도 켜기"}
          >
            <Text style={styles.mapToggleText}>{mapVisible ? "지도 끄기" : "지도 켜기"}</Text>
          </Pressable>
        )}

        {mapVisible && navRoute && (
          <View style={styles.navMapPanel}>
            <NavMapPanel
              appKey={navRoute.appKey}
              waypoints={navRoute.waypoints}
              current={mapPos}
            />
          </View>
        )}

        <View style={styles.controlRow}>
          <Pressable
            style={[
              styles.mapToggleButton,
              detectionEnabled && styles.detectionToggleActive,
            ]}
            onPress={() => {
              setDetectionEnabled((v) => {
                const next = !v;
                if (!next) {
                  hapticEngine.stopContinuous();
                  void audioEngine.stopBeep();
                }
                return next;
              });
            }}
            accessibilityRole="button"
            accessibilityLabel={detectionEnabled ? "탐지 중지" : "탐지 시작"}
          >
            <Text style={styles.mapToggleText}>
              {detectionEnabled ? "탐지 중지" : "탐지 시작"}
            </Text>
          </Pressable>

          <Pressable
            style={[
              styles.mapToggleButton,
              serverTransport === "usb" && styles.transportToggleUsb,
            ]}
            onPress={() => {
              if (NETWORK_MODE === "ngrok" || NETWORK_MODE === "tailscale") {
                console.log(
                  `[ServerTransport] 외부망 고정 모드: ${transportLabel(serverTransport)} -> ${wsUrlFor(serverTransport)}`,
                );
                return;
              }
              const next: ServerTransport = serverTransport === "wifi" ? "usb" : "wifi";
              setServerTransport(next);
              void saveServerTransport(next);
              console.log(`[ServerTransport] 전환: ${transportLabel(next)} -> ${wsUrlFor(next)}`);
            }}
            accessibilityRole="button"
            accessibilityLabel={transportAccessibilityLabel(serverTransport)}
          >
            <Text style={styles.mapToggleText}>
              {transportButtonText(serverTransport)}
            </Text>
          </Pressable>

          {isDepthProbeSupported() ? (
            <Pressable
              style={styles.mapToggleButton}
              onPress={() => setDepthMode((v) => !v)}
              accessibilityRole="button"
              accessibilityLabel={depthMode ? "거리 측정 끄기" : "거리 측정 켜기"}
            >
              <Text style={styles.mapToggleText}>{depthMode ? "거리측정 끄기" : "거리측정"}</Text>
            </Pressable>
          ) : null}
        </View>

        {__DEV__ && <DebugTriggerPanel />}
      </ScrollView>
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

function DepthProbeMarkers({ result }: { result: DepthProbeResult | null }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {DEPTH_PROBE_POINTS.map((point, i) => {
        const sample = result?.samples?.[i];
        const metersText = sample?.meters != null ? `${sample.meters.toFixed(2)}m` : "-";
        return (
          <View
            key={point.label}
            style={[
              styles.depthMarkerWrap,
              {
                left: `${point.x * 100}%`,
                top: `${point.y * 100}%`,
              },
            ]}
          >
            <View style={styles.depthMarkerDot} />
            <Text style={styles.depthMarkerLabel}>
              {point.label} {metersText}
            </Text>
          </View>
        );
      })}
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
        const distance = resolveDetectionDistance(d);
        const distanceText = distance.meters !== null ? `${distance.meters.toFixed(1)}m ${distance.label}` : distance.label;
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
                {d.className} {distanceText} ({(d.confidence * 100).toFixed(0)}%)
              </Text>
            </View>
          </Fragment>
        );
      })}
    </View>
  );
}

/**
 * ROIOverlay: 주행 통로 사다리꼴 ROI를 화면에 반투명 테두리로 시각화한다.
 * path_risk.py의 PATH_ROI_NEAR_BAND / PATH_ROI_FAR_BAND 와 동일 좌표 기준.
 * BBoxOverlay와 동일한 absoluteFill + 절대좌표 View 방식을 사용한다.
 */
function ROIOverlay() {
  const [nearLo, nearHi] = PATH_ROI_NEAR_BAND;
  const [farLo, farHi] = PATH_ROI_FAR_BAND;
  const yTopPct  = PATH_ROI_FAR_Y_RATIO * 100;
  const yBotPct  = 100;
  const heightPct = yBotPct - yTopPct;
  // 사다리꼴 4변을 각각 얇은 View로 그린다.
  // 상변 / 하변은 수평 선, 좌변 / 우변은 기울어진 선(width 계산 + transform).
  const topWidthPct  = (farHi  - farLo)  * 100;
  const botWidthPct  = (nearHi - nearLo) * 100;
  const topLeftPct   = farLo  * 100;
  const botLeftPct   = nearLo * 100;
  const LINE_W = 2;
  const COLOR  = "rgba(249, 183, 0, 0.75)"; // COLOR_GILDANG_YELLOW 반투명

  // 좌변/우변 기울기 계산: 화면 비율 좌표 -> 실제 픽셀 변환은 % 사용으로 생략
  // 단순화: 좌/우변을 작은 세그먼트로 근사하지 않고 두꺼운 사선 View 1개로 표현.
  // (React Native는 SVG가 없으므로 4개 꼭짓점 방식 대신 상/하/좌/우 4변 직사각형으로 근사)
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {/* 상변 */}
      <View style={{
        position: "absolute",
        left: `${topLeftPct}%`,
        top: `${yTopPct}%`,
        width: `${topWidthPct}%`,
        height: LINE_W,
        backgroundColor: COLOR,
      }} />
      {/* 하변 */}
      <View style={{
        position: "absolute",
        left: `${botLeftPct}%`,
        top: `${yBotPct - 0.5}%`,
        width: `${botWidthPct}%`,
        height: LINE_W,
        backgroundColor: COLOR,
      }} />
      {/* 좌변 - 상하단 x차/y범위로 기울기 근사 */}
      <View style={{
        position: "absolute",
        left: `${topLeftPct}%`,
        top: `${yTopPct}%`,
        width: LINE_W,
        height: `${heightPct}%`,
        backgroundColor: COLOR,
        transform: [{ skewX: `${Math.atan2((farLo - nearLo) * 100, heightPct) * (180 / Math.PI)}deg` }],
      }} />
      {/* 우변 */}
      <View style={{
        position: "absolute",
        left: `${farHi * 100}%`,
        top: `${yTopPct}%`,
        width: LINE_W,
        height: `${heightPct}%`,
        backgroundColor: COLOR,
        transform: [{ skewX: `${Math.atan2((nearHi - farHi) * 100, heightPct) * (180 / Math.PI)}deg` }],
      }} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLOR_BG_BASE,
  },
  title: {
    color: COLOR_GILDANG_YELLOW,
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 12,
    textAlign: "center",
    marginTop: 40,
    letterSpacing: 1,
  },
  message: {
    color: COLOR_TEXT_MUTED,
    fontSize: 14,
    marginBottom: 8,
    textAlign: "center",
  },
  button: {
    backgroundColor: COLOR_GILDANG_YELLOW,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
    alignSelf: "center",
  },
  buttonText: {
    color: COLOR_BG_BASE,
    fontSize: 16,
    fontWeight: "700",
  },
  debugBox: {
    marginTop: 20,
    marginHorizontal: 16,
    padding: 12,
    backgroundColor: COLOR_BG_SURFACE,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  debugText: {
    color: COLOR_OP_GREEN,
    fontSize: 11,
    fontFamily: "monospace",
  },
  hapticFlash: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    backgroundColor: "rgba(255, 51, 51, 0.35)",
  },
  operatorPanel: {
    flex: 1,
    backgroundColor: COLOR_BG_BASE,
  },
  operatorPanelContent: {
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 24,
    gap: 8,
  },
  operatorCard: {
    padding: 8,
    backgroundColor: COLOR_OVERLAY_BG,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  confThresholdRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 8,
    backgroundColor: COLOR_OVERLAY_BG,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  confThresholdLabel: {
    color: COLOR_TEXT_BASE,
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
    backgroundColor: COLOR_GILDANG_YELLOW,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 8,
  },
  confThresholdButtonText: {
    color: COLOR_BG_BASE,
    fontSize: 18,
    fontWeight: "bold",
  },
  detectionListCard: {
    padding: 10,
    backgroundColor: COLOR_OVERLAY_BG,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  detectionListTitle: {
    color: COLOR_GILDANG_YELLOW,
    fontSize: 12,
    fontWeight: "bold",
    fontFamily: "monospace",
    marginBottom: 4,
  },
  detectionListText: {
    color: COLOR_OP_GREEN,
    fontSize: 15,
    fontWeight: "bold",
    fontFamily: "monospace",
  },
  navMapPanel: {
    height: 210,
    borderRadius: 8,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  controlRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  detectionToggleActive: {
    backgroundColor: "rgba(57, 255, 20, 0.18)",
    borderWidth: 1,
    borderColor: COLOR_OP_GREEN,
  },
  transportToggleUsb: {
    backgroundColor: "rgba(0, 210, 255, 0.18)",
    borderWidth: 1,
    borderColor: COLOR_TECH_BLUE,
  },
  detectionIdleBanner: {
    ...StyleSheet.absoluteFill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(10, 13, 16, 0.75)",
    paddingHorizontal: 24,
  },
  detectionIdleText: {
    color: COLOR_TEXT_BASE,
    fontSize: 15,
    fontWeight: "600",
    textAlign: "center",
    lineHeight: 22,
  },
  depthTitle: {
    color: COLOR_TECH_BLUE,
    fontSize: 13,
    fontWeight: "700",
    marginBottom: 6,
  },
  depthRow: {
    color: COLOR_TEXT_BASE,
    fontSize: 16,
    fontWeight: "600",
    lineHeight: 24,
  },
  depthError: {
    color: COLOR_REFLEX_RED,
    fontSize: 13,
  },
  depthMarkerWrap: {
    position: "absolute",
    alignItems: "center",
    transform: [{ translateX: -38 }, { translateY: -10 }],
  },
  depthMarkerDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 3,
    borderColor: COLOR_TECH_BLUE,
    backgroundColor: "rgba(10, 13, 16, 0.5)",
  },
  depthMarkerLabel: {
    marginTop: 4,
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
    overflow: "hidden",
    color: COLOR_TEXT_BASE,
    backgroundColor: COLOR_OVERLAY_BG,
    fontSize: 11,
    fontWeight: "700",
  },
  mapToggleButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 16,
    backgroundColor: COLOR_OVERLAY_BG,
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  mapToggleText: {
    color: COLOR_TEXT_BASE,
    fontSize: 12,
    fontWeight: "600",
  },
  sttButton: {
    alignSelf: "stretch",
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 24,
    backgroundColor: COLOR_GILDANG_YELLOW,
    alignItems: "center",
    justifyContent: "center",
  },
  sttButtonActive: {
    backgroundColor: COLOR_REFLEX_RED,
  },
  sttButtonText: {
    color: COLOR_BG_BASE,
    fontSize: 20,
    fontWeight: "700",
  },
  sttButtonTextActive: {
    color: "#FFFFFF",
  },
  sttErrorText: {
    color: "#FF9999",
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
    // 실제 캡처/추론 프레임은 640x640 정사각형(디버그로 확인함, 2026-07-06)이므로
    // 미리보기 컨테이너도 1:1 정사각형이어야 BBox 좌표가 화면과 정합한다.
    // 3:4였을 때는 미리보기가 실제 캡처 범위보다 넓게 보여, 박스가 실제 사물보다
    // 훨씬 넓게 그려지는 것처럼 보이는 불일치가 있었다.
    width: "100%",
    aspectRatio: 1,
    overflow: "hidden",
    position: "relative",
    backgroundColor: COLOR_BG_SURFACE,
  },
});
