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
import Svg, { Path, Text as SvgText } from "react-native-svg";

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
  probeDepthBoxes,
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
// 하단 15% (서버 reflex_gate / PROXIMITY_Y와 동일) — 근접 긴급은 outdoor 게이트 우회
const PROXIMITY_BOTTOM_Y = FRAME_SIZE * 0.85;
// 2026-07-18 거리 정책 SSOT: server/detection/distance_policy.py의 NEAR_ENTER_AREA_RATIO(0.10)와
// 동일한 값. Near 전용 반사 원칙에 따라 이 값 미만은 로컬 반사 대상이 아니다(서버 인지
// 경로 담당). HIGH_HAZARDS(이동체)는 접근 속도가 빨라 더 이른(보수적) 0.08에서 긴급 처리한다.
const URGENT_AREA_RATIO = 0.10;
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

// 주행 통로 ROI (소실점 사다리꼴): 640x640 정사각 프레임, 가로 50:50 중선(y=0.5) 아래만.
// 소실점=(0.5, 0.5)에 수렴하는 원근 통로. 상단 절반(y<0.5)은 침범하지 않는다.
const PATH_ROI_MID_Y = 0.5;
const PATH_ROI_VANISH_X = 0.5;
const PATH_ROI_VANISH_Y = 0.5;
const PATH_ROI_NEAR_BAND = [0.20, 0.80] as const; // 하단(가까운) 좌우
const PATH_ROI_FAR_BAND = [0.38, 0.62] as const;  // 상단(먼) 좌우 - 소실점 근처
const PATH_ROI_FAR_Y_RATIO = PATH_ROI_MID_Y;      // 통로 상단 = 50% 선

/**
 * 소실점 사다리꼴 꼭짓점 4개 (정규화 0~1). 좌상 -> 우상 -> 우하 -> 좌하.
 */
function roiPolygon(): [number, number][] {
  const [nearLo, nearHi] = PATH_ROI_NEAR_BAND;
  const [farLo, farHi] = PATH_ROI_FAR_BAND;
  const yTop = PATH_ROI_FAR_Y_RATIO;
  const yBottom = 1.0;
  return [
    [farLo, yTop],
    [farHi, yTop],
    [nearHi, yBottom],
    [nearLo, yBottom],
  ];
}

function pointInPolygon(px: number, py: number, polygon: [number, number][]): boolean {
  if (py < PATH_ROI_MID_Y) return false;
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

// 2026-07-18 거리 정책 SSOT(1단계): Near 전용 반사로 축소. 기존 4단계(초접근/근접/
// 중거리/원거리) 로컬 비프·햅틱 중 Medium/Far 두 단계를 제거했다 - 서버가 이미 동일
// 원칙(server/detection/gates/reflex_gate.py)으로 Near만 반사하므로, 서버 연결이
// 끊겼을 때만 켜지는 이 로컬 폴백도 같은 Near 경계를 따라야 서버 복구 전후로 알림
// 패턴이 갑자기 바뀌지 않는다. Medium/Far는 로컬에서 무출력(서버 인지 TTS 전담,
// 재연결 전까지는 안내 없음 - HEURISTIC_DISTANCE_ALERT_ROUTING_IMPLEMENTATION_PLAN
// §12.1 "A. 오프라인 Near만 출력" 채택).
const LOCAL_NEAR_CRITICAL_AREA_RATIO = 0.20; // Near 구역 내 "초접근" 세부 강도(연속 진동)
const LOCAL_NEAR_LIDAR_METERS = 0.7; // area_ratio 0.10 ≈ 0.22/sqrt(0.10) ≈ 0.70m
const LOCAL_NEAR_CRITICAL_LIDAR_METERS = 0.5;

/**
 * 온디바이스 주차센서식 비프/햅틱 (LLM 미경유). Near 전용(area_ratio>=0.10 또는
 * LiDAR<=0.7m)만 반사를 발동하고, 그 미만은 기존 출력을 정지만 하고 무출력 반환한다.
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
    if (nearestLidarMeters <= LOCAL_NEAR_CRITICAL_LIDAR_METERS) {
      void hapticEngine.trigger("continuous");
      void audioEngine.playBeep(0.0, 0);
      log(`[LiDAR] 근접(초) class=${lidarClass} d=${nearestLidarMeters.toFixed(2)}m samples=${samples}`);
      return true;
    }
    if (nearestLidarMeters <= LOCAL_NEAR_LIDAR_METERS) {
      void hapticEngine.trigger("double");
      void audioEngine.playBeep(0.0, 200);
      playLocalReflexClip(200);
      log(`[LiDAR] 근접 class=${lidarClass} d=${nearestLidarMeters.toFixed(2)}m samples=${samples}`);
      return true;
    }
    // Medium/Far(0.7m 초과): Near 전용 반사 원칙 - 로컬 비프·햅틱 0건, 서버 인지 경로 전담.
    hapticEngine.stopContinuous();
    void audioEngine.stopBeep();
    return false;
  }

  // 💡 [설계 의도] 클래스 종류와 독립적(class-agnostic)으로 BBox 크기(면적비)만으로 온디바이스 반사 피드백을 제어합니다.
  if (maxAreaRatio > LOCAL_NEAR_CRITICAL_AREA_RATIO) {
    void hapticEngine.trigger("continuous");
    void audioEngine.playBeep(0.0, 0);
    log(`근접(초) ratio=${maxAreaRatio.toFixed(2)}`);
    return true;
  }
  if (maxAreaRatio >= URGENT_AREA_RATIO) {
    void hapticEngine.trigger("double");
    void audioEngine.playBeep(0.0, 200);
    playLocalReflexClip(200);
    log(`근접 ratio=${maxAreaRatio.toFixed(2)}`);
    return true;
  }
  // Medium/Far(area_ratio < 0.10): Near 전용 반사 원칙 - 로컬 비프·햅틱 0건.
  hapticEngine.stopContinuous();
  void audioEngine.stopBeep();
  return false;
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
    sendDetectionFrame,
    lastMessage,
    navRoute,
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
    setCapturePaused,
    setRequiresFloat32,
    requestCameraPermission,
    reportInferenceLatency,
    useStreamCapture,
    frameProcessor,
  } = useCamera(REFLEX_FPS, COGNITIVE_FPS);
  const { isModelsLoaded, segLoaded, detLoaded, detShapeLog, requiresFloat32, detectFrame } =
    useOnDeviceDetection();
  const { requestLocationPermission, startWatching, stopWatching } = useLocation();

  // 로컬 추론 엔진의 입력 계약을 캡처 계층에 전달 (2026-07-17, P0).
  // CoreML 정상 모드(requiresFloat32=false)면 JS JPEG 디코딩 + Float32Array 할당을 건너뛴다.
  useEffect(() => {
    setRequiresFloat32(requiresFloat32);
  }, [requiresFloat32, setRequiresFloat32]);
  // STT 음성 명령: 단말은 마이크 캡처만 담당, 인식은 서버(stt_audio 핸들러)가 수행.
  // 2026-07-10: Release 빌드는 console 출력이 안 보여 실기기에서 원인 파악이 불가능했다
  // - 에러 상세를 화면에 직접 표시(sttErrorInfo)해 즉시 읽을 수 있게 한다.
  const [sttErrorInfo, setSttErrorInfo] = useState<string>("");
  // 누르는 즉시 UI를 활성(빨간)으로 바꿔, 녹음 prepare 지연 동안에도 "버튼이 안 된다"로 오인되지 않게 한다.
  const [sttHeld, setSttHeld] = useState(false);
  const sttPressActiveRef = useRef(false);
  const sttPressStartedAtRef = useRef(0);
  const delayedSttStartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 2026-07-19: 탭 오탐(탐지 시작·화면 탭, 실측 hold≈40ms)이 안내 Speech를 끊지 않도록
  // 이 시간 이상 누른 뒤에만 선점·녹음. 서버 폐기 임계(MIN_STT_HOLD_MS=400)보다 짧게
  // 두어 의도적 STT 총 누름 시간이 과도해지지 않게 한다.
  const STT_ARM_DELAY_MS = 200;
  // arm 완료 여부. arm 전 pressOut은 오디오를 건드리지 않는다.
  const sttArmedRef = useRef(false);
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
        setCapturePaused(false);
        return;
      }
      void hapticEngine.trigger("short");
      setSttErrorInfo("");
      send({ type: "stt_audio", audio_b64: audioB64 });
      // 전송 직후 캡처 재개(응답 재생은 setSttInteractionActive가 인지 경로만 뮤트).
      setCapturePaused(false);
    },
    (reason, detail) => {
      void hapticEngine.trigger("double");
      setSttErrorInfo(`STT 실패[${reason}]: ${detail ?? "-"}`);
      setCapturePaused(false);
    },
  );
  // STT 누름/녹음 중에는 프레임 전송·온디바이스 추론을 멈춰 버튼 반응을 지킨다.
  const sttBusy = sttHeld || sttStatus !== "idle";
  const sttBusyRef = useRef(false);
  useEffect(() => {
    sttBusyRef.current = sttBusy;
  }, [sttBusy]);

  const onSttPressIn = useCallback(() => {
    // ScrollView/JS 지연으로 pressOut이 유실되면 플래그가 남아 다음 입력이 무시된다.
    // 800ms 이내 재발화만 디바운스하고, 그 이상은 stuck recovery.
    if (sttPressActiveRef.current) {
      const heldFor = Date.now() - sttPressStartedAtRef.current;
      if (heldFor < 800) return;
      console.warn(`[STT] stuck press recovery (${heldFor}ms)`);
      sttPressActiveRef.current = false;
    }
    sttPressActiveRef.current = true;
    sttPressStartedAtRef.current = Date.now();
    sttArmedRef.current = false;
    // setState useEffect보다 먼저 동기 차단해 CoreML/JPEG 디코드를 즉시 멈춘다.
    sttBusyRef.current = true;
    setCapturePaused(true);
    setSttHeld(true);
    if (delayedSttStartTimerRef.current) {
      clearTimeout(delayedSttStartTimerRef.current);
      delayedSttStartTimerRef.current = null;
    }
    void hapticEngine.trigger("short");
    setSttErrorInfo("");
    // 2026-07-19: 탭/짧은 터치(탐지 시작·화면 탭 오탐)가 온보딩·인지 안내를 즉시
    // Speech.stop()으로 끊지 않도록, STT_ARM_DELAY_MS 이상 누른 뒤에만 선점·녹음.
    // 실측: hold≈40ms STT로 "길댕아 저는…보행을"에서 온보딩이 onDone 처리됨.
    delayedSttStartTimerRef.current = setTimeout(() => {
      delayedSttStartTimerRef.current = null;
      if (!sttPressActiveRef.current) return;
      sttArmedRef.current = true;
      audioEngine.setSttActive(true);
      // STT 실패/응답 안내(priority=2) 재생 중에는 stop하지 않는다.
      audioEngine.stopGuideAudioIfPriorityAtMost(1);
      void startSttRecording();
    }, STT_ARM_DELAY_MS);
  }, [startSttRecording, setCapturePaused]);

  const onSttPressOut = useCallback(() => {
    if (!sttPressActiveRef.current) return;
    sttPressActiveRef.current = false;
    setSttHeld(false);
    if (delayedSttStartTimerRef.current) {
      clearTimeout(delayedSttStartTimerRef.current);
      delayedSttStartTimerRef.current = null;
    }
    // arm 전 해제: 안내를 끊지도, 녹음도 시작하지 않았으므로 캡처만 재개.
    if (!sttArmedRef.current) {
      sttBusyRef.current = false;
      setCapturePaused(false);
      return;
    }
    sttArmedRef.current = false;
    // 인지 가이드 뮤트는 STT 응답 수신 시 useWebSocket이 연장. 여기서 즉시 false로
    // 끄지 않는다(응답 전 인지 TTS가 끼어드는 문제 방지).
    void (async () => {
      try {
        await stopSttRecording();
      } finally {
        setCapturePaused(false);
      }
    })();
  }, [stopSttRecording, setCapturePaused]);

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
  // 2026-07-18: DEBUG 트리거 패널은 화면을 크게 가려 실기기 테스트를 방해하므로
  // 기본은 접힌 상태(작은 토글 버튼만 노출)로 시작하고 필요할 때만 펼친다.
  const [debugPanelExpanded, setDebugPanelExpanded] = useState(false);

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

  // 지도 토글은 경로 유무와 무관하게 유지(하단 도구 패널에서 항상 접근).

  // 2026-07-11 LiDAR 실거리 프로브 모드(프로토타입, iOS Pro 계열 전용, Mitos 로드맵 §2):
  // 켜면 vision-camera를 내리고(isActive=false, 두 세션이 후면 카메라를 공유할 수 없는
  // 프로토타입 제약) 자체 심도 세션으로 화면 3지점의 실거리를 표시한다. bbox 휴리스틱
  // 거리와의 교차 검증(줄자 실측 대조)용 계측 화면이며, 탐지·경보는 이 모드 동안 정지한다.
  const [depthMode, setDepthMode] = useState(false);
  const [depthResult, setDepthResult] = useState<DepthProbeResult | null>(null);
  const [depthError, setDepthError] = useState<string | null>(null);
  // 2026-07-17 LiDAR 검증 캡처(Mitos 로드맵 §2 검증 전용 스코프): 거리측정 모드의
  // 정지 프레임을 기존 "detection" 경로로 서버에 보내 실제 YOLO bbox를 받은 뒤,
  // 같은 bbox의 LiDAR 실측을 distance_probe_sample로 서버에 보고해 DB에 남긴다.
  // 반사/인지 경로의 실시간 판단에는 관여하지 않는 수동 트리거 전용 흐름이다.
  const pendingProbeEventIdRef = useRef<string | null>(null);
  const [depthProbeStatus, setDepthProbeStatus] = useState<string | null>(null);

  // 탐지 토글을 서버에 동기화: OFF면 STT가 자유 질문으로 가고, 목적지/인텐트 대기를 푼다.
  // WS 재연결 후에도 현재 토글 값을 다시 보낸다. 계측용 거리측정 모드에서는 탐지를 일시 정지한다.
  useEffect(() => {
    if (status !== "connected") return;
    send({ type: "detection_control", enabled: detectionEnabled && !depthMode, ts: Date.now() });
  }, [status, detectionEnabled, depthMode, send]);

  useEffect(() => {
    if (!depthMode) return;
    // 거리측정 모드 진입 시 vision-camera가 남긴 이전 bbox가 depth 프리뷰 위에
    // 그대로 남아 있지 않도록 비운다. "검증 캡처"가 완료되면 LiDAR 거리가 채워진
    // 새 bbox로 다시 채워진다(아래 server_detection 핸들러 참조).
    setDetections([]);
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
      setDepthProbeStatus(null);
      pendingProbeEventIdRef.current = null;
    };
  }, [depthMode]);

  // LiDAR 검증 캡처 트리거: depthResult.previewUri(depthMode 폴링이 주기적으로 갱신)를
  // 기존 "detection" base64 경로로 전송하고, 상관관계 매칭용 event_id를 기록해 둔다.
  // 실제 LiDAR 매칭·전송은 아래 server_detection 핸들러가 응답을 받은 뒤 수행한다.
  //
  // 2026-07-19: 객체 탐지 왕복과 별개로, 화면에 이미 표시 중인 고정 3지점(중앙/전방
  // 하단/발밑, DEPTH_PROBE_POINTS) 값도 같은 버튼으로 바로 저장한다. YOLO 탐지가 전혀
  // 필요 없고 depthResult.samples를 그대로 보고하면 되므로 서버 왕복 없이 즉시 전송한다.
  const handleDistanceProbeCapture = useCallback(() => {
    if (!depthResult?.ready || !depthResult.previewUri) {
      setDepthProbeStatus("검증 캡처: LiDAR 프리뷰 준비 전");
      return;
    }
    const probeEventId = `probe-${DEVICE_ID}-${Date.now()}`;
    pendingProbeEventIdRef.current = probeEventId;
    setDepthProbeStatus("검증 캡처 전송 중...");
    send({
      type: "detection",
      payload: {
        event_id: probeEventId,
        device_id: DEVICE_ID,
        frame_id: Date.now(),
        thumbnail_jpeg_b64: depthResult.previewUri,
        stream: "cognitive",
        probe_source: "lidar_validation",
      },
    });

    const fixedPointSamples = depthResult.samples
      .map((sample, index) => {
        const point = DEPTH_PROBE_POINTS[index];
        if (!point) return null;
        return {
          point_label: point.label,
          x: sample.x,
          y: sample.y,
          lidar_meters: sample.meters,
          axial_meters: sample.axialMeters ?? null,
          lidar_sample_count: sample.sampleCount ?? 0,
          lidar_accuracy: depthResult.accuracy ?? null,
          lidar_quality: depthResult.quality ?? null,
          lidar_calibrated: depthResult.calibrated === true,
        };
      })
      .filter((sample): sample is NonNullable<typeof sample> => sample !== null);

    if (fixedPointSamples.length > 0) {
      send({
        type: "fixed_point_probe_sample",
        payload: {
          event_id: `${probeEventId}-fixed`,
          samples: fixedPointSamples,
        },
      });
    }
  }, [depthResult, send]);

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

      // LiDAR 검증 캡처가 보낸 event_id와 일치하면, 받은 bbox로 같은 depth 세션의
      // LiDAR 실측을 샘플링해 distance_probe_sample로 보고한다(검증 전용, 1회성).
      if (lastMessage.event_id && lastMessage.event_id === pendingProbeEventIdRef.current) {
        const probeEventId = lastMessage.event_id;
        pendingProbeEventIdRef.current = null;
        if (serverDets.length === 0) {
          setDepthProbeStatus("검증 캡처: 탐지된 객체 없음");
        } else {
          void (async () => {
            const boxResult = await probeDepthBoxes(serverDets.map((d) => d.bbox));
            if (!boxResult || !boxResult.ready) {
              setDepthProbeStatus("검증 캡처: LiDAR 심도 미준비");
              return;
            }

            // 2026-07-19: 계산한 LiDAR 거리를 서버 DB 로깅뿐 아니라 화면에도 실제로
            // 적용한다. 지금까지는 probeDepthBoxes() 결과가 distance_probe_sample
            // 전송에만 쓰이고 detections 상태로는 돌아오지 않아, 화면에서 "이 bbox가
            // 실제로 몇 m로 측정됐는지" 확인할 방법이 없었다(줄자 대조 시 필요).
            const enrichedDets = serverDets.map((det, index) => {
              const dist = boxResult.distances.find((d) => d.index === index);
              if (!dist || typeof dist.meters !== "number") {
                return det;
              }
              return {
                ...det,
                distanceMeters: dist.meters,
                distanceSource: "lidar" as const,
                depthSampleCount: dist.sampleCount ?? 0,
                depthAccuracy: boxResult.accuracy,
              };
            });
            setDetections(enrichedDets);

            const samples = serverDets.map((det, index) => {
              const dist = boxResult.distances.find((d) => d.index === index);
              return {
                class_name: det.className,
                confidence: det.confidence,
                bbox: det.bbox,
                lidar_meters: dist?.meters ?? null,
                lidar_sample_count: dist?.sampleCount ?? 0,
                lidar_accuracy: boxResult.accuracy ?? null,
                lidar_quality: boxResult.quality ?? null,
                lidar_calibrated: boxResult.calibrated === true,
              };
            });
            send({
              type: "distance_probe_sample",
              payload: { event_id: probeEventId, samples },
            });
            setDepthProbeStatus(`검증 캡처: ${samples.length}건 전송 완료`);
          })();
        }
      }
    }
  }, [lastMessage, send]);

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
  const sendDetectionFrameRef = useRef(sendDetectionFrame);
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
  useEffect(() => { sendDetectionFrameRef.current = sendDetectionFrame; }, [sendDetectionFrame]);
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
    let flashTimer: ReturnType<typeof setTimeout> | null = null;
    hapticEngine.setMockHandler(() => {
      setHapticFlash(true);
      if (flashTimer) {
        clearTimeout(flashTimer);
      }
      flashTimer = setTimeout(() => {
        flashTimer = null;
        setHapticFlash(false);
      }, 300);
    });
    return () => {
      if (flashTimer) {
        clearTimeout(flashTimer);
      }
      hapticEngine.setMockHandler(null);
    };
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

    // STT press-and-hold 구간: 프레임/추론을 건너뛰어 오디오 세션·하트비트를 우선한다.
    if (sttBusyRef.current) {
      return;
    }

    // 카메라 렌더링 디버깅을 위한 코드
    // console.log(`[CameraView 디버그] handleFrame 호출됨! jpegBytes: ${!!frame.jpegBytes}, base64: ${!!frame.base64}, sendRef: ${!!sendRef.current}`);

    // 로컬 추론 엔진 적재 여부와 관계없이 서버로 프레임 전송 수행 (WebSocket)
    // raw JPEG 바이트가 있으면(실기기) base64를 경유하지 않고 메타데이터(JSON) + 바이너리
    // 프레임 2개를 순차 전송한다. 단일 WS 연결에서 프레임 순서는 보장되므로 서버는
    // "transport: binary" 메타 수신 직후 오는 바이너리 프레임을 해당 이벤트로 매칭한다.
    // 2026-07-17 (P0): sendDetectionFrame으로 ACK 기반 in-flight 제한을 적용한다 -
    // 메타와 binary를 한 쌍으로 전송/드롭해 서버 pending_binary_meta 매칭 오류를 막는다.
    if (frame.jpegBytes && sendDetectionFrameRef.current) {
      const sent = sendDetectionFrameRef.current(
        {
          type: "detection",
          payload: {
            event_id: eventId,
            device_id: DEVICE_ID,
            frame_id: now,
            stream: frameStream,
            transport: "binary",
            is_outdoor: isOutdoorBySceneRef.current,
          },
        },
        frame.jpegBytes,
      );
      if (sent) {
        lastFrameSentTsRef.current = now;
      }
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

      // 1. 공통 전처리: 기하/신뢰도 1차 필터(근접 긴급은 outdoor 게이트를 우회해야 하므로 아래에서 별도 처리)
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
        // ROI 판정: 소실점 사다리꼴(50% 선 아래) 밖이면 반사 경로 제외.
        // 2026-07-18: Near 전용 반사 원칙 채택 후 로컬 반사 후보는 urgentDetections
        // (isProximityUrgent 통과)뿐이므로 outdoor 게이트는 더 이상 필요 없다 - 근접
        // 긴급은 실내 판정이어도 충돌 회피가 우선이라 원래도 outdoor 게이트를 거치지 않았다.
        const cxNorm = (d.bbox.x + d.bbox.w / 2) / FRAME_SIZE;
        const cyNorm = (d.bbox.y + d.bbox.h / 2) / FRAME_SIZE;
        if (!pointInPolygon(cxNorm, cyNorm, roiPoly)) return false;
        return true;
      });
      const urgentDetections = baseCandidates.filter((d) =>
        isProximityUrgent(d.bbox, d.className),
      );
      // 2026-07-18 거리 정책 SSOT: Near 전용 반사 원칙에 따라 로컬 반사 후보를
      // urgentDetections(Near, isProximityUrgent 통과)로만 한정한다. 이전에는 근접
      // 후보가 없으면 실외 신호가 있는 중·원거리 객체까지 로컬 반사 후보로 승격했으나
      // (outdoorScopedDetections), 이는 서버 Near 전용 반사 정책과 정면 충돌해 제거했다.
      // Medium/Far는 서버 인지 경로(guide TTS)가 전담하며, 서버 연결이 끊긴 동안에는
      // 무출력이 정책상 올바른 동작이다(§12.1 "A. 오프라인 Near만 출력").
      const reflexDetections = urgentDetections;

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
    // if (isCapturing) return;

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
  }, [isMockMode, permissionStatus, device, status, serverTransport, networkRttMs, networkRttAvgMs, isCapturing, detectionEnabled, currentReflexFps, segLoaded, detLoaded, detShapeLog, lastDetect]);

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

  // 2026-07-19: 거리측정 모드에서도 "검증 캡처" 결과(LiDAR 거리가 적용된 bbox)를
  // BBoxOverlay·detectedClassesStr에 그대로 보여준다. 모드 진입 시 detections를
  // 비워두므로(위 useEffect) depthMode 초기 진입 직후에는 여전히 빈 배열이고,
  // 캡처가 끝난 뒤에만 LiDAR 거리 라벨이 붙은 bbox가 나타난다.
  const activeDetections = detections.filter(
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
        {/* 2026-07-19: 기존 소실점 사다리꼴 ROI 오버레이를 제거하고 Near/Medium/Far
            3구역 거리 경계선으로 교체. 시각적 도식화만 변경하고 반사 후보 필터링
            로직(roiPolygon/pointInPolygon)은 그대로 유지한다. */}
        {detectionEnabled && !depthMode && <DistanceZoneOverlay />}
        {/* BBox 오버레이: 640x640 비율과 1:1 카메라 프레임의 완벽 정합, 신뢰도 임계값 이상만 표시 */}
        <BBoxOverlay detections={activeDetections} />
      </View>

      {/* 2026-07-10 설계: 화면 전체가 STT press-and-hold.
          운영자 버튼은 이 레이어 *위*에 absolute + box-none으로 올린다.
          (ScrollView box-none 안에 버튼을 두면 STT 제스처 후 버튼이 먹통이 됨 - 2026-07-17 실측) */}
      <Pressable
        style={[StyleSheet.absoluteFill, styles.sttFullScreenHitLayer]}
        onPressIn={onSttPressIn}
        onPressOut={onSttPressOut}
        accessibilityRole="button"
        accessibilityLabel={`연결: ${status}, 캡처: ${isCapturing ? "활성" : "비활성"}. 화면을 누르고 있는 동안 음성 명령을 말하세요.`}
        accessibilityHint="손을 떼면 서버로 전송되어 음성 명령을 인식합니다."
      />

      {/* 표시 전용 패널: 터치 통과 → 아래 STT 레이어가 수신 */}
      <View style={styles.operatorPanel} pointerEvents="none">
        <ScrollView
          style={StyleSheet.absoluteFill}
          contentContainerStyle={styles.operatorPanelContent}
          scrollEnabled={false}
        >
          <ConnectionStatus status={status} />
          <View style={styles.operatorCard}>
            {debugInfo.map((line, i) => (
              <Text key={i} style={styles.debugText}>{line}</Text>
            ))}
          </View>
          <View style={styles.detectionListCard}>
            <Text style={styles.detectionListTitle}>[실시간 감지]</Text>
            <Text style={styles.detectionListText}>{detectedClassesStr}</Text>
          </View>
          <View style={[styles.sttButton, sttBusy && styles.sttButtonActive]}>
            <Text style={[styles.sttButtonText, sttBusy && styles.sttButtonTextActive]}>
              {sttStatus === "recording"
                ? "듣는 중..."
                : sttStatus === "sending"
                  ? "전송 중..."
                  : sttHeld
                    ? "준비 중..."
                    : "화면을 누르고 말하기"}
            </Text>
            {sttErrorInfo !== "" && (
              <Text style={styles.sttErrorText}>{sttErrorInfo}</Text>
            )}
          </View>
          {depthMode && (
            <View style={styles.operatorCard}>
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
              {depthProbeStatus ? (
                <Text style={styles.depthRow}>{depthProbeStatus}</Text>
              ) : null}
            </View>
          )}
        </ScrollView>
      </View>

      {/* 조작 버튼 오버레이: operatorPanel(표시 전용, pointerEvents=none) 밖의 별도
          box-none 레이어. none 안에 중첩하면 자식 Pressable이 조상의 none 때문에
          터치를 아예 받지 못한다(2026-07-18 th 병합 회귀 수정 - 탐지 시작 등 버튼
          무반응 버그의 원인). */}
      <View style={styles.controlsOverlay} pointerEvents="box-none">
        <View style={styles.confThresholdRow} pointerEvents="box-none">
          <Text style={styles.confThresholdLabel} pointerEvents="none">
            신뢰도 임계값: {(confThreshold * 100).toFixed(0)}%
          </Text>
          <View style={styles.confThresholdButtons} pointerEvents="box-none">
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

        {navRoute ? (
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
        ) : null}

        <View style={styles.controlRow} pointerEvents="box-none">
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
              mapVisible && styles.navToggleActive,
            ]}
            onPress={() => setMapVisible((v) => !v)}
            accessibilityRole="button"
            accessibilityLabel={mapVisible ? "지도 끄기" : "지도 켜기"}
          >
            <Text style={styles.mapToggleText}>{mapVisible ? "지도 끄기" : "지도"}</Text>
          </Pressable>

          <Pressable
            style={[
              styles.mapToggleButton,
              serverTransport === "usb" && styles.transportToggleUsb,
            ]}
            onPress={() => {
              if (NETWORK_MODE === "tailscale") {
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

          {depthMode ? (
            <Pressable
              style={styles.mapToggleButton}
              onPress={handleDistanceProbeCapture}
              accessibilityRole="button"
              accessibilityLabel="LiDAR 거리 검증 캡처"
            >
              <Text style={styles.mapToggleText}>검증 캡처</Text>
            </Pressable>
          ) : null}
        </View>

        {/* 지도는 카메라(640) 위가 아니라 하단 도구 패널에만 표시 */}
        {mapVisible && (
          <View style={styles.navMapPanel}>
            <NavMapPanel
              appKey={navRoute?.appKey ?? ""}
              waypoints={navRoute?.waypoints ?? []}
              current={mapPos}
            />
          </View>
        )}

        {__DEV__ && (
          <View style={styles.devPanelWrap} pointerEvents="box-none">
            <Pressable
              style={styles.devPanelToggle}
              onPress={() => setDebugPanelExpanded((v) => !v)}
              accessibilityRole="button"
              accessibilityLabel={debugPanelExpanded ? "DEBUG 패널 접기" : "DEBUG 패널 펼치기"}
            >
              <Text style={styles.devPanelToggleText}>
                {debugPanelExpanded ? "DEBUG 패널 접기 ▲" : "DEBUG 패널 펼치기 ▼"}
              </Text>
            </Pressable>
            {debugPanelExpanded && <DebugTriggerPanel />}
          </View>
        )}
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

// 2026-07-19: Near/Medium/Far 거리 구역 기반 색상. 서버 distance_policy.py SSOT와
// 동일한 area_ratio 경계(0.10/0.03)를 단말에서도 사용해 3자 정합을 맞춘다.
// 단말은 Near 경계(0.10)만 SSOT와 수동 동기화해 왔으나, 도식화를 위해 Medium/Far
// 경계(0.03)도 동일 값으로 로컬 사용한다(반사 라우팅은 여전히 Near-only).
// CPU 비용: 사칙연산 2회 + 비교 2회 per detection (기존 getClassColor의 문자열
// includes 체인보다 저렴).
const ZONE_NEAR_AREA_RATIO = 0.10;
const ZONE_MEDIUM_AREA_RATIO = 0.03;

function getZoneTag(areaRatio: number): { color: string; tag: string } {
  if (areaRatio >= ZONE_NEAR_AREA_RATIO) return { color: "#EF4444", tag: "NEAR" };
  if (areaRatio >= ZONE_MEDIUM_AREA_RATIO) return { color: "#F59E0B", tag: "MED" };
  return { color: "#3B82F6", tag: "FAR" };
}

/**
 * BBox 오버레이: 카메라 프리뷰 위에 탐지 박스를 그린다.
 * 박스 좌표는 640x640 기준이므로 화면 대비 비율로 변환.
 */
function BBoxOverlay({ detections }: { detections: OnDeviceDetectionResult[] }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {detections.map((d, i) => {
        // 2026-07-19: 거리 구역 기반 색상. 기존 클래스 해시 색상 대신 Near/Med/Far
        // 팔레트를 사용해 거리 직관성 확보. 단, HIGH_HAZARDS/caution/roadway는
        // 기존 강제 색상을 우선 적용(위험 종류가 거리보다 중요).
        const areaRatio = (d.bbox.w * d.bbox.h) / (FRAME_SIZE * FRAME_SIZE);
        const zone = getZoneTag(areaRatio);
        const hazardOverride = HIGH_HAZARDS.includes(d.className) || d.className === "caution" || d.className === "roadway";
        const color = hazardOverride ? getClassColor(d.className) : zone.color;
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
        // track_id가 없는 온디바이스 결과이므로 모델·클래스·반올림 bbox로 안정 키를 만든다.
        // 겹친/중복(NMS 이전) 박스는 반올림 좌표까지 같을 수 있어 배열 인덱스를
        // tie-breaker로 덧붙여 유일성을 보장한다(React 중복 key 경고 실측 수정).
        const bboxKey = `${d.model}-${d.className}-${Math.round(d.bbox.x)}-${Math.round(d.bbox.y)}-${Math.round(d.bbox.w)}-${Math.round(d.bbox.h)}-${i}`;
        return (
          <Fragment key={bboxKey}>
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
                {d.className} {distanceText} ({(d.confidence * 100).toFixed(0)}%) {zone.tag}
              </Text>
            </View>
          </Fragment>
        );
      })}
    </View>
  );
}

/**
 * 2026-07-19: Near/Medium/Far 3구역 거리 경계선 오버레이 (SVG 부채꼴).
 * 소실점(apex)에서 하단 좌·우 모서리로 퍼지는 부채꼴.
 *
 * 기하학 (좌우 끝까지 연결):
 * - 호 끝점: 좌·우 화면 가장자리(x=0, x=W)에 고정
 *   예) NEAR 호 = (0, H*0.78) ↔ (W, H*0.78) 를 apex 중심 원호로 연결
 * - 측면선(소실점→하단 모서리)은 시각적으로 FAR 삼각형처럼 보여 혼동을 주므로 제거
 * - 이전 구현은 레이 위 짧은 반경만 써서 호가 화면 중앙에만 그려지는 문제가 있었음
 *
 * 색상은 BBox zone 색상과 동일 팔레트.
 */
function DistanceZoneOverlay() {
  const [size, setSize] = useState({ width: 0, height: 0 });

  const W = size.width;
  const H = size.height;

  const NEAR_COLOR = "#EF4444";
  const MED_COLOR = "#F59E0B";
  const FAR_COLOR = "#3B82F6";
  const STROKE_W = 2;
  const STROKE_OPACITY = 0.75;

  if (W === 0 || H === 0) {
    return (
      <View
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
        onLayout={(e) => setSize(e.nativeEvent.layout)}
      />
    );
  }

  // 소실점: 화면 중앙, 상단 22% (부채꼴이 아래로 더 넓게 퍼지도록)
  const apexX = W / 2;
  const apexY = H * 0.22;

  // 좌·우 가장자리에 끝점을 두고, apex 중심 원호로 연결 (화면 끝까지 연결)
  const edgeArc = (edgeYRatio: number) => {
    const edgeY = H * edgeYRatio;
    const r = Math.sqrt(apexX ** 2 + (edgeY - apexY) ** 2);
    const left = { x: 0, y: edgeY };
    const right = { x: W, y: edgeY };
    // y 하향 좌표계에서 좌→우, 아래로 볼록한 호: sweep=1
    const d = `M ${left.x} ${left.y} A ${r} ${r} 0 0 1 ${right.x} ${right.y}`;
    return { d, r, left, right, edgeY };
  };

  const nearArc = edgeArc(0.78); // NEAR/MED
  const medArc = edgeArc(0.52);  // MED/FAR

  return (
    <View
      style={StyleSheet.absoluteFill}
      pointerEvents="none"
      onLayout={(e) => setSize(e.nativeEvent.layout)}
    >
      <Svg width={W} height={H} style={StyleSheet.absoluteFill}>
        {/* NEAR/MED 호 (좌우 끝 → 끝) */}
        <Path
          d={nearArc.d}
          fill="none"
          stroke={NEAR_COLOR}
          strokeWidth={STROKE_W}
          strokeOpacity={STROKE_OPACITY}
        />
        {/* MED/FAR 호 (좌우 끝 → 끝) */}
        <Path
          d={medArc.d}
          fill="none"
          stroke={MED_COLOR}
          strokeWidth={STROKE_W}
          strokeOpacity={STROKE_OPACITY}
        />
        <SvgText x={W - 44} y={nearArc.edgeY - 6} fill={NEAR_COLOR} fontSize={11} fontWeight="bold">
          NEAR
        </SvgText>
        <SvgText x={W - 40} y={medArc.edgeY - 6} fill={MED_COLOR} fontSize={11} fontWeight="bold">
          MED
        </SvgText>
        <SvgText x={apexX + 8} y={apexY - 4} fill={FAR_COLOR} fontSize={11} fontWeight="bold">
          FAR
        </SvgText>
      </Svg>
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
    paddingBottom: 120,
    gap: 8,
  },
  controlsOverlay: {
    ...StyleSheet.absoluteFill,
    zIndex: 20,
    justifyContent: "flex-end",
    paddingBottom: 12,
    paddingHorizontal: 12,
    gap: 8,
  },
  controlRowDock: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    alignItems: "center",
  },
  mapToggleWrap: {
    alignSelf: "flex-end",
  },
  navMapWrap: {
    height: 180,
    borderRadius: 8,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: COLOR_BORDER_TACTICAL,
  },
  devPanelWrap: {
    // 2026-07-18: 아코디언 방식. 접힌 기본 상태는 작은 토글 버튼 한 줄만 차지해
    // controlRowDock 높이에 거의 영향을 주지 않는다. 펼쳤을 때만 패널만큼 dock 전체가
    // 위로 확장되며(사용자가 의도적으로 연 상태이므로 허용), 접으면 즉시 원래 높이로 복귀.
    alignSelf: "stretch",
  },
  devPanelToggle: {
    alignSelf: "flex-start",
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
    backgroundColor: "rgba(10, 13, 16, 0.85)",
    borderWidth: 1,
    borderColor: "#222A30",
  },
  devPanelToggleText: {
    color: "#39FF14",
    fontSize: 11,
    fontFamily: "monospace",
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
  navToggleActive: {
    backgroundColor: "rgba(249, 183, 0, 0.2)",
    borderWidth: 1,
    borderColor: COLOR_GILDANG_YELLOW,
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
  sttFullScreenHitLayer: {
    // iOS에서 완전 투명 View는 네이티브 Camera에 터치가 흡수될 수 있어 최소 알파를 둔다.
    backgroundColor: "rgba(0,0,0,0.01)",
    zIndex: 1,
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
