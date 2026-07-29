/**
 * 이중 캡처 타이머 훅.
 * 반사(reflex 10fps)/인지(cognitive 2fps) 스트림을 분리 캡처하여
 * 온디바이스 TFLite 추론용 Float32Array 텐서를 공급한다.
 *
 * 동작 모드:
 *  - MOCK_CAMERA=true : MockFrameProvider가 번들 샘플 → float32 (시뮬레이터)
 *  - MOCK_CAMERA=false: 실기기. 캡처 하드웨어 접근은 플랫폼별로 분리된
 *    useFrameCaptureProvider(services/frameCaptureProviderSelect.ios.ts /
 *    .android.ts)가 담당하고, 이 훅은 타이머·동적 FPS·Mock 분기 등 플랫폼
 *    무관 오케스트레이션만 수행한다
 *    (docs/mobile/ios_android_bifurcation_contract.md §4 참조).
 *
 * 실기기에서는 서버 WS 전송용 raw JPEG 바이트(jpegBytes)와 CoreML 네이티브 브릿지 호출용
 * base64 문자열을 함께 전달한다 (서버 전송은 jpegBytes를 바이너리 프레임으로 직접 사용).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  type CameraDevice,
  useCameraDevice,
  useCameraDevices,
  useCameraPermission,
  useFrameProcessor,
} from "react-native-vision-camera";
import { useSharedValue } from "react-native-worklets-core";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import { MOCK_CAMERA } from "../config/mock";
import type { StreamType } from "../types/detection";
import {
  decodeBase64JpegToHwc,
  getFrameProvider,
} from "../services/frameProvider";
import {
  base64ToUint8,
  useFrameCaptureProvider,
  type FrameData,
} from "../services/frameCaptureProvider";
import {
  isThermalMonitoringSupported,
  readThermalState,
} from "../services/thermalBridge";

export type { FrameData };

// 동적 FPS 조절 파라미터 (온디바이스 추론 지연 + 서버 백프레셔)
// - 지연이 현재 간격의 90%를 넘으면(따라잡지 못함) 간격을 늘려 fps를 낮춘다.
// - 지연이 현재 간격의 50% 미만으로 안정되면 기본 간격까지 서서히 되돌린다.
const OVERLOAD_LATENCY_RATIO = 0.9;
const RECOVERY_LATENCY_RATIO = 0.5;
const INTERVAL_INCREASE_STEP_MS = 50;
const INTERVAL_DECREASE_STEP_MS = 20;
// 온디바이스 과부하 상한(~5fps). 서버 busy 힌트가 오면 이보다 더 낮출 수 있다.
const MAX_REFLEX_INTERVAL_MS = 200;
// 2026-07-21 P0: 서버 busy ack의 suggest_reflex_interval_ms 상한(~3.3fps).
const MAX_SERVER_BUSY_INTERVAL_MS = 300;
const SERVER_BUSY_HOLD_MS = 1500;

// 💡 [면접 대비 주석] 발열(ADPF) 기반 캡처 간격 하한 (2026-07-29, 핸드오프 §5.8).
// §5.7에서 추론 지연을 캡처 컨트롤러 입력에서 분리하면서(blocksCapture=false), 캡처 경로
// 자체가 느려질 때 물러설 장치가 사라졌다. 실사용은 장시간 보행이라 발열 스로틀링이
// 재현될 조건이므로, 대리 지표(추론 지연) 대신 발열을 직접 읽어 하한을 건다.
//
// headroom 1.0이 스로틀링 임계다. 임계에 닿은 뒤 대응하면 이미 카메라 세션 fps가
// 무너진 상태(§5.8: 30 -> 중앙 12.6)이므로, 0.85에서 한 단계 물러서고 1.0에서 상한까지
// 내린다. 복귀는 0.7 이하에서만 허용해 임계 근처에서 간격이 진동하지 않게 한다.
// 폴링 주기 10초는 플랫폼의 헤드룸 갱신 최소 간격에 맞춘 값이다(더 자주 불러도 같은 값).
const THERMAL_POLL_INTERVAL_MS = 10000;
const THERMAL_HEADROOM_SEVERE = 1.0;
const THERMAL_HEADROOM_THROTTLE = 0.85;
const THERMAL_HEADROOM_RECOVER = 0.7;

// 💡 [면접 대비 주석] 캡처 지연 기반 하한 — ADPF가 없는 단말용 대체 신호 (2026-07-29).
// 위 ADPF 경로는 Xiaomi 12(Snapdragon 8 Gen 1)에서 `getThermalHeadroom`이 NaN을 반환해
// 무효였다(`cmd thermalservice headroom 10` -> NaN으로 실기기 확인). `getCurrentThermalStatus`도
// §5.8 실측에서 스로틀링 중 0(NONE)이었으므로 이 단말에는 쓸 수 있는 발열 API가 없다.
//
// 그래서 §5.8이 원래 제안했던 대체 신호를 함께 구현한다: **캡처가 실제로 느려졌는지를 직접
// 관측한다.** 스로틀링의 최종 증상은 카메라 세션 fps 붕괴(§5.8: 30 -> 중앙 12.6)이므로,
// 프레임 도착 간격이 지시한 간격보다 크게 벌어지면 원인이 발열이든 무엇이든 물러서야 한다.
// 발열 API가 유효한 단말에서는 두 신호 중 더 보수적인(큰) 하한이 적용된다.
//
// 비율로 판정하는 이유: 지시 간격 자체가 변하므로 절대값 임계는 의미가 없다. 지시 간격
// 대비 1.4배(예: 125 -> 175ms 도착)면 한 단계, 1.8배면 상한까지 내린다. 회복은 1.15배
// 미만에서만 허용하고, 하한을 올린 뒤 20초 안에는 낮추지 않아(dwell) 진동을 막는다.
const CAPTURE_LAG_WINDOW = 24;
const CAPTURE_LAG_EVAL_INTERVAL_MS = 5000;
const CAPTURE_LAG_SEVERE_RATIO = 1.8;
const CAPTURE_LAG_THROTTLE_RATIO = 1.4;
const CAPTURE_LAG_RECOVER_RATIO = 1.15;
const CAPTURE_FLOOR_DWELL_MS = 20000;

export interface UseCameraReturn {
  cameraRef: React.RefObject<Camera | null>;
  device: CameraDevice | undefined;
  hasPermission: boolean;
  permissionStatus: string;
  isCapturing: boolean;
  isMockMode: boolean;
  currentReflexFps: number;
  startCapture: (onFrame: (frame: FrameData) => void) => void;
  stopCapture: () => void;
  /** STT 등에서 프레임 디코드/콜백만 일시 중지(카메라 세션은 유지). */
  setCapturePaused: (paused: boolean) => void;
  /**
   * 로컬 추론 엔진의 입력 계약 갱신 (2026-07-17, P0).
   * false면 JS JPEG 디코딩 + Float32Array 할당을 건너뛴다(CoreML 모드).
   * useOnDeviceDetection의 requiresFloat32 값을 전달한다.
   */
  setRequiresFloat32: (required: boolean) => void;
  requestCameraPermission: () => Promise<boolean>;
  /**
   * 온디바이스 추론 지연(ms)을 보고하여 반사 캡처 fps를 동적으로 조절한다.
   * blocksCapture=false면 추론이 캡처를 막지 않는 경로(네이티브 백그라운드 추론)이므로
   * 상승 분기를 적용하지 않는다. 상세 근거는 구현부 주석 참조.
   */
  reportInferenceLatency: (latencyMs: number, blocksCapture?: boolean) => void;
  /**
   * 서버 ack 백프레셔(server_busy / suggest_reflex_interval_ms)를 반영한다.
   * 2026-07-21 P0: 야외 과부하 시 단말 반사 송신률을 낮춰 큐 drop·늦은 판정을 줄인다.
   */
  reportServerLoad: (info: {
    busy: boolean;
    suggestIntervalMs?: number;
  }) => void;
  /** true면 <Camera>가 photo 대신 frameProcessor(연속 스트림)로 구동돼야 한다. */
  useStreamCapture: boolean;
  /** useStreamCapture가 true일 때만 값이 있다. <Camera frameProcessor={...}>에 그대로 전달한다. */
  frameProcessor: ReturnType<typeof useFrameProcessor> | undefined;
}

export function useCamera(
  reflexFps: number = REFLEX_FPS,
  cognitiveFps: number = COGNITIVE_FPS,
): UseCameraReturn {
  const isMockMode = MOCK_CAMERA;
  const { hasPermission, requestPermission } = useCameraPermission();
  const backDevice = useCameraDevice("back");
  const allDevices = useCameraDevices();
  const device = backDevice || allDevices[0];
  const cameraRef = useRef<Camera | null>(null);
  const reflexTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cognitiveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);
  // STT press-and-hold 중 JPEG 디코드/온디바이스 콜백을 즉시 막아 JS 스레드를 비운다.
  const capturePausedRef = useRef(false);
  // 로컬 추론 엔진의 입력 계약 (2026-07-17, P0).
  // false(CoreML 정상 모드)면 매 프레임 JS JPEG 디코딩 + 4.7MiB Float32Array 할당을
  // 건너뛴다 - base64는 CoreML 네이티브 브릿지가 직접 소비하므로 float32는 TFLite 폴백
  // 전용이며 CoreML 모드에서는 버려지던 비용을 제거한다. 단말 버튼 반응 지연의 직접 원인.
  const requiresFloat32Ref = useRef<boolean>(true);
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionRequested, setPermissionRequested] = useState(false);

  // 동적 FPS 상태: baseIntervalRef는 설정된 기본값(가장 빠른 허용치),
  // currentIntervalRef는 추론 지연 피드백에 따라 조절되는 실제 반사 루프 간격
  const baseIntervalRef = useRef(Math.floor(1000 / reflexFps));
  const currentIntervalRef = useRef(baseIntervalRef.current);
  const [currentReflexFps, setCurrentReflexFps] = useState(reflexFps);
  // 서버 busy 힌트가 유효한 시각(이 시각 전까지는 온디바이스 복구로 간격을 줄이지 않음)
  const serverBusyUntilRef = useRef(0);
  // 캡처 간격 하한 2종. 실제 하한은 둘 중 큰 값이며, base면 제약 없음.
  // - thermalFloorRef: ADPF 발열 헤드룸 기반(지원 단말 한정)
  // - captureFloorRef: 프레임 도착 간격 실측 기반(전 단말 공통 대체 신호)
  const thermalFloorRef = useRef(baseIntervalRef.current);
  const captureFloorRef = useRef(baseIntervalRef.current);
  // 하한을 마지막으로 올린 시각. 이 시각 + CAPTURE_FLOOR_DWELL_MS 전에는 낮추지 않는다.
  const captureFloorRaisedAtRef = useRef(0);
  // 프레임 도착 간격 링버퍼(최근 CAPTURE_LAG_WINDOW개)와 직전 도착 시각.
  const captureGapsRef = useRef<number[]>([]);
  const lastCaptureArrivalRef = useRef(0);
  const lastCaptureEvalRef = useRef(0);

  /** 두 하한과 base 중 가장 보수적인(큰) 값. */
  const effectiveFloor = useCallback(() => {
    return Math.max(
      baseIntervalRef.current,
      thermalFloorRef.current,
      captureFloorRef.current,
    );
  }, []);

  // 프레임 프로세서(worklet) 경로용 SharedValue. worklet(별도 JS 컨텍스트)과 메인
  // JS 스레드 간 상태 공유는 SharedValue로만 안전하다(일반 useRef는 worklet에서
  // 최신값을 보장하지 못함). currentIntervalRef가 갱신될 때마다 함께 갱신한다.
  const intervalSharedValue = useSharedValue(currentIntervalRef.current);
  const lastCaptureTsShared = useSharedValue(0);

  const applyReflexInterval = useCallback(
    (next: number, reason: string) => {
      const cur = currentIntervalRef.current;
      if (next === cur) return;
      currentIntervalRef.current = next;
      intervalSharedValue.value = next;
      setCurrentReflexFps(Math.round(1000 / next));
      console.log(`[Camera] 동적 FPS 조절: 반사 간격 ${cur}ms -> ${next}ms (${reason})`);
    },
    [intervalSharedValue],
  );

  /**
   * 온디바이스 추론 지연을 캡처 루프에 피드백한다.
   *
   * 💡 [면접 대비 주석] blocksCapture 인자의 의미 (2026-07-28).
   * 이 컨트롤러는 "추론이 캡처 간격을 못 따라가면 캡처 fps를 낮춰 과부하 크래시를 막는다"는
   * 목적으로 도입됐다. 그 전제는 추론이 JS 스레드를 점유해 캡처를 실제로 방해한다는 것이었다.
   *
   * 그런데 현재 네이티브 경로(iOS CoreML / Android TFLiteInferenceBridge)는 추론이
   * 네이티브 백그라운드 스레드에서 돌고, CameraView가 fire-and-forget으로 디스패치하므로
   * 추론 지연이 캡처를 전혀 막지 않는다. 그럼에도 추론 지연으로 캡처 간격을 늘리면
   * 서버 전송·콘솔 Live Feed까지 함께 느려지는 잘못된 결합이 된다.
   *
   * Xiaomi 12 실측(2026-07-28): 추론 96~160ms에서 상승 분기(latency > cur*0.9)가 계속
   * 걸려 간격이 180~200ms에 고착됐다(약 5fps). 하강 분기는 latency < cur*0.5를 요구하므로
   * base 125ms에는 수학적으로 도달할 수 없다. 반대로 지연이 0으로 잘못 보고되던 동안에는
   * base까지 내려가 8.6~9.0fps가 나왔다.
   *
   * 따라서 추론이 캡처를 막지 않는 경로(blocksCapture=false)에서는 상승 분기를 적용하지
   * 않는다. 하강(회복) 분기는 유지해야 서버 busy로 올라간 간격이 되돌아올 수 있다.
   * 추론 폭주에 대한 역압력은 CameraView의 in-flight 상한(MAX_INFLIGHT_DETECTIONS를 채우면
   * 디스패치 생략)이 이미 담당하므로 과부하 보호가 사라지는 것은 아니다.
   *
   * 2026-07-29: 캡처 경로 자체가 느려지는 경우(발열 스로틀링)에 대한 물러섬은 발열 헤드룸
   * 폴링이 담당한다(아래 useEffect, 핸드오프 §5.8).
   *
   * JS 디코드 폴백 경로(requiresFloat32=true)는 추론이 실제로 JS 스레드를 점유하므로
   * blocksCapture=true로 기존 동작을 그대로 유지한다.
   */
  const reportInferenceLatency = useCallback(
    (latencyMs: number, blocksCapture: boolean = true) => {
      if (!Number.isFinite(latencyMs) || latencyMs < 0) return;
      const cur = currentIntervalRef.current;
      // 발열/캡처 지연 하한이 걸려 있으면 회복은 그 하한까지만 허용한다(§5.8).
      const floor = effectiveFloor();
      let next = cur;

      // 회복 가능 조건은 두 경로 공통으로 유지한다. 특히 serverBusyUntil 홀드를 건너뛰면
      // 서버 백프레셔가 무력화되므로 blocksCapture 여부와 무관하게 지킨다.
      const canRecover = cur > floor && Date.now() >= serverBusyUntilRef.current;

      if (blocksCapture && latencyMs > cur * OVERLOAD_LATENCY_RATIO) {
        next = Math.min(MAX_REFLEX_INTERVAL_MS, cur + INTERVAL_INCREASE_STEP_MS);
      } else if (
        canRecover &&
        (!blocksCapture || latencyMs < cur * RECOVERY_LATENCY_RATIO)
      ) {
        next = Math.max(floor, cur - INTERVAL_DECREASE_STEP_MS);
      }

      if (next !== cur) {
        applyReflexInterval(next, `추론 지연=${latencyMs.toFixed(1)}ms`);
      }
    },
    [applyReflexInterval, effectiveFloor],
  );

  const reportServerLoad = useCallback(
    (info: { busy: boolean; suggestIntervalMs?: number }) => {
      if (!info.busy) return;
      const suggested =
        typeof info.suggestIntervalMs === "number" && Number.isFinite(info.suggestIntervalMs)
          ? info.suggestIntervalMs
          : MAX_SERVER_BUSY_INTERVAL_MS;
      const target = Math.min(
        MAX_SERVER_BUSY_INTERVAL_MS,
        Math.max(currentIntervalRef.current, Math.round(suggested)),
      );
      serverBusyUntilRef.current = Date.now() + SERVER_BUSY_HOLD_MS;
      if (target > currentIntervalRef.current) {
        applyReflexInterval(target, `서버 busy suggest=${suggested}ms`);
      }
    },
    [applyReflexInterval],
  );

  /**
   * 발열(ADPF) 폴링 — 캡처 간격 하한을 갱신한다 (2026-07-29, 핸드오프 §5.8 설계 공백 보완).
   *
   * 상수 정의부의 주석에 임계 근거를 적었다. 여기서는 적용 규칙만 둔다.
   *  - 하한이 올라가면 즉시 반영한다(발열은 기다릴수록 나빠진다).
   *  - 하한이 내려가면 즉시 되돌리지 않고 하한만 낮춘다. 실제 복귀는 기존 회복 분기
   *    (reportInferenceLatency)가 20ms씩 점진 수행하므로 서버 백프레셔·추론 과부하로
   *    올라가 있던 간격을 발열 회복이 한 번에 밀어내는 부작용이 없다.
   */
  useEffect(() => {
    if (isMockMode || !isCapturing) return;
    if (!isThermalMonitoringSupported()) return;

    let cancelled = false;
    // 첫 조회 결과는 하한 변화가 없어도 1회 로그로 남긴다. 이걸 찍지 않으면 "발열이 없어서
    // 조용한 것"과 "헤드룸이 NaN이라 기능 자체가 죽은 것"을 로그로 구분할 수 없다
    // (Xiaomi 12가 실제로 후자였다 - 상수 정의부 주석 참조).
    let probeLogged = false;
    const evaluate = async () => {
      const state = await readThermalState(
        Math.round(THERMAL_POLL_INTERVAL_MS / 1000),
      );
      if (cancelled) return;
      if (!probeLogged) {
        probeLogged = true;
        console.log(
          `[Camera] 발열 헤드룸 지원 여부: headroom=${state?.headroom ?? "미지원"} thermalStatus=${state?.status ?? "n/a"}${state?.reason ? ` (${state.reason})` : ""}`,
        );
      }
      if (state?.headroom == null) return;

      const headroom = state.headroom;
      const base = baseIntervalRef.current;
      const prevFloor = thermalFloorRef.current;
      let floor = prevFloor;

      if (headroom >= THERMAL_HEADROOM_SEVERE) {
        floor = MAX_REFLEX_INTERVAL_MS;
      } else if (headroom >= THERMAL_HEADROOM_THROTTLE) {
        floor = Math.min(
          MAX_REFLEX_INTERVAL_MS,
          base + INTERVAL_INCREASE_STEP_MS,
        );
      } else if (headroom <= THERMAL_HEADROOM_RECOVER) {
        floor = base;
      }
      // 0.7 초과 0.85 미만은 히스테리시스 구간이라 직전 하한을 그대로 유지한다.
      if (floor === prevFloor) return;

      thermalFloorRef.current = floor;
      console.log(
        `[Camera] 발열 헤드룸 ${headroom.toFixed(2)} (thermalStatus=${state.status ?? "n/a"}) - 캡처 간격 하한 ${prevFloor}ms -> ${floor}ms`,
      );
      if (floor > currentIntervalRef.current) {
        applyReflexInterval(floor, `발열 헤드룸=${headroom.toFixed(2)}`);
      }
    };

    void evaluate();
    const timer = setInterval(() => {
      void evaluate();
    }, THERMAL_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [isMockMode, isCapturing, applyReflexInterval]);

  /**
   * 프레임 도착 간격 실측 -> 캡처 간격 하한 (2026-07-29).
   *
   * ADPF가 없는 단말에서 §5.8 공백을 메우는 대체 신호다. 상수 정의부에 임계 근거를 적었다.
   * 캡처 진입점(handleStreamFrameBase64)에서 매 프레임 호출되므로 비용은 배열 push + 5초에
   * 한 번의 정렬(24개)뿐이다.
   */
  const observeCaptureArrival = useCallback(
    (now: number) => {
      const prev = lastCaptureArrivalRef.current;
      lastCaptureArrivalRef.current = now;
      if (prev <= 0) return;

      const gaps = captureGapsRef.current;
      gaps.push(now - prev);
      if (gaps.length > CAPTURE_LAG_WINDOW) gaps.shift();
      if (gaps.length < CAPTURE_LAG_WINDOW) return;
      if (now - lastCaptureEvalRef.current < CAPTURE_LAG_EVAL_INTERVAL_MS) return;
      lastCaptureEvalRef.current = now;

      const sorted = [...gaps].sort((a, b) => a - b);
      const median = sorted[Math.floor(sorted.length / 2)];
      const cur = currentIntervalRef.current;
      const base = baseIntervalRef.current;
      const ratio = median / cur;
      const prevFloor = captureFloorRef.current;
      let floor = prevFloor;

      if (ratio >= CAPTURE_LAG_SEVERE_RATIO) {
        floor = MAX_REFLEX_INTERVAL_MS;
      } else if (ratio >= CAPTURE_LAG_THROTTLE_RATIO) {
        floor = Math.min(MAX_REFLEX_INTERVAL_MS, base + INTERVAL_INCREASE_STEP_MS);
      } else if (
        ratio < CAPTURE_LAG_RECOVER_RATIO &&
        now - captureFloorRaisedAtRef.current >= CAPTURE_FLOOR_DWELL_MS
      ) {
        floor = base;
      }
      if (floor === prevFloor) return;

      captureFloorRef.current = floor;
      if (floor > prevFloor) captureFloorRaisedAtRef.current = now;
      console.log(
        `[Camera] 캡처 도착 간격 중앙 ${median}ms / 지시 ${cur}ms (x${ratio.toFixed(2)}) - 간격 하한 ${prevFloor}ms -> ${floor}ms`,
      );
      const target = effectiveFloor();
      if (target > currentIntervalRef.current) {
        applyReflexInterval(target, `캡처 지연 x${ratio.toFixed(2)}`);
      }
    },
    [applyReflexInterval, effectiveFloor],
  );

  const effectivePermission = isMockMode ? true : hasPermission;

  const requestCameraPermission = useCallback(async (): Promise<boolean> => {
    if (isMockMode) return true;
    console.log("[Camera] 권한 요청 시작");
    const granted = await requestPermission();
    console.log("[Camera] 권한 요청 결과:", granted);
    setPermissionRequested(true);
    return granted;
  }, [isMockMode, requestPermission]);

  useEffect(() => {
    if (isMockMode) return;
    if (!hasPermission && !permissionRequested) {
      console.log("[Camera] 권한 없음, 자동 요청");
      requestCameraPermission();
    }
    console.log(
      "[Camera] 상태 - hasPermission:",
      hasPermission,
      "device:",
      device?.id ?? "undefined",
    );
  }, [
    isMockMode,
    hasPermission,
    permissionRequested,
    device,
    requestCameraPermission,
  ]);

  // ---- 프레임 획득 ----

  const captureMockFrame = useCallback(
    async (stream: StreamType): Promise<FrameData | null> => {
      const provider = getFrameProvider();
      if (!provider) return null;
      try {
        const float32 = await provider.getFrame();
        return { float32, stream, base64: null, jpegBytes: null };
      } catch (err) {
        console.error(`[Camera/Mock] ${stream} 프레임 오류:`, err);
        return null;
      }
    },
    [],
  );

  // ---- 스트림 캡처 콜백 (플랫폼 구현이 base64 결과를 밀어 넣는 진입점) ----
  const streamFrameCounterRef = useRef(0);

  const handleStreamFrameBase64 = useCallback((base64: string) => {
    if (capturePausedRef.current) return;
    if (!onFrameRef.current || !base64) return;
    streamFrameCounterRef.current++;
    // 캡처 경로가 실제로 느려졌는지(발열 스로틀링 등) 관측하는 지점(§5.8 대체 신호).
    observeCaptureArrival(Date.now());

    const jpegBytes = base64ToUint8(base64);
    // 💡 [면접 대비 주석] CoreML 정상 모드(requiresFloat32=false)에서는 JS JPEG 디코딩과
    // 640x640x3 Float32Array(~4.7MiB) 할당을 건너뛴다 (2026-07-17, P0).
    // CoreML 네이티브 브릿지는 base64를 직접 소비하므로 float32는 TFLite 폴백 전용이다.
    // 이전에는 폴백 전용 전처리를 CoreML 모드에서도 매 프레임 실행해 JS 스레드를 포화시켰다.
    // takePhoto 폴백 경로(frameCaptureProvider.ts Float32Array(0))와 동일한 우회 전략.
    //
    // 2026-07-28 (Android Live Feed 끊김 P0): TFLite 경로(requiresFloat32=true)에서는
    // 위 우회가 적용되지 않아 매 프레임 JS JPEG 디코드가 돌았다. Xiaomi 12 실측에서
    // handleFrame 호출 간격이 899~965ms(약 1.05fps, 목표 8fps=125ms)로 고정되고
    // NetworkBench RTT가 33ms에서 35s까지 치솟았다 - JS 스레드 포화의 전형적 신호다.
    // 네이티브 플러그인이 이미 640x640으로 크롭·리사이즈한 비트맵을 JPEG로 압축해
    // 넘기는데, JS가 그것을 다시 디코드·크롭·바이리니어 리사이즈해 640x640으로
    // 되돌리는 완전한 왕복이었다.
    //
    // float32를 지연 계산(lazy getter)으로 바꿔, 서버·콘솔 전송 경로(jpegBytes)는
    // 디코드를 전혀 기다리지 않게 한다. 디코드는 온디바이스 추론이 실제로
    // frame.float32를 읽는 순간에만, 프레임당 최대 1회 수행된다(반사/인지 프레임이
    // 결과를 공유). 추론 스로틀(CameraView REAL_DETECT_MIN_INTERVAL_MS)에 걸려
    // 건너뛰는 프레임은 디코드 비용이 0이 된다.
    const needsFloat32 = requiresFloat32Ref.current;
    let decodedFloat32: Float32Array | null = null;
    const readFloat32 = (): Float32Array => {
      if (decodedFloat32 === null) {
        decodedFloat32 = needsFloat32 ? decodeBase64JpegToHwc(base64) : new Float32Array(0);
      }
      return decodedFloat32;
    };

    const makeFrame = (stream: StreamType): FrameData => {
      const frame = { stream, base64, jpegBytes } as FrameData;
      Object.defineProperty(frame, "float32", {
        enumerable: true,
        configurable: true,
        get: readFloat32,
      });
      return frame;
    };

    onFrameRef.current(makeFrame("reflex"));

    const ratio = Math.max(1, Math.floor(reflexFps / cognitiveFps));
    if (streamFrameCounterRef.current % ratio === 0) {
      // 스프레드({...frame})는 getter를 즉시 평가해 지연 계산 효과를 없앤다. 같은
      // readFloat32 클로저를 공유하는 새 프레임 객체를 만들어 디코드 1회를 유지한다.
      onFrameRef.current(makeFrame("cognitive"));
    }
  }, [reflexFps, cognitiveFps, observeCaptureArrival]);

  const setCapturePaused = useCallback((paused: boolean) => {
    capturePausedRef.current = paused;
  }, []);

  const setRequiresFloat32 = useCallback((required: boolean) => {
    if (requiresFloat32Ref.current !== required) {
      requiresFloat32Ref.current = required;
      console.log(`[Camera] 로컬 추론 입력 계약 갱신: requiresFloat32=${required}`);
    }
  }, []);

  // 플랫폼별 캡처 구현 (iOS/Android 모두 frameProcessor 가능, 실패 시 takePhoto 폴백).
  // Metro가 frameCaptureProviderSelect.ios.ts 또는 .android.ts를 자동 바인딩한다.
  const captureProvider = useFrameCaptureProvider({
    cameraRef,
    intervalSharedValue,
    lastCaptureTsShared,
    onStreamFrameBase64: handleStreamFrameBase64,
  });

  const captureFrame = isMockMode ? captureMockFrame : captureProvider.capturePhoto;
  // Frame Processor(연속 스트림) 우선. 플러그인 미등록 시에만 takePhoto 폴백.
  // takePhoto 강제(useStreamCapture=false)는 AVCapturePhotoOutput 경로로
  // AVFoundation -11803 "Cannot Record"/오디오 세션 충돌을 유발한다(2026-07-17 실측).
  // Expo Go 등 supportsStream=false 환경에서는 자동으로 takePhoto 폴백된다.
  const useStreamCapture = !isMockMode && captureProvider.supportsStream;

  // ---- 캡처 루프 (capturePhoto 경로 전용, 스트림 경로는 <Camera frameProcessor>가 구동) ----

  const startCapture = useCallback(
    (onFrame: (frame: FrameData) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      baseIntervalRef.current = Math.floor(1000 / reflexFps);
      currentIntervalRef.current = baseIntervalRef.current;
      intervalSharedValue.value = currentIntervalRef.current;
      setCurrentReflexFps(reflexFps);
      streamFrameCounterRef.current = 0;

      if (useStreamCapture) {
        // 스트림 경로: <Camera frameProcessor={frameProcessor}>가 이미 프레임을
        // 지속적으로 공급 중이므로(isCapturing=true가 됨과 동시에 onFrameRef가 유효해져
        // handleStreamFrameBase64가 실제로 dispatch를 시작), 여기서는 별도 타이머가 필요 없다.
        console.log(
          `[Camera] Stream 캡처 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성, supportsStream=${captureProvider.supportsStream})`,
        );
        return;
      }

      const frameCounter = { current: 0 };

      // setInterval 대신 재귀 setTimeout을 사용: 매 tick마다 currentIntervalRef의
      // 최신값을 다시 읽어와야 reportInferenceLatency()의 동적 fps 조절이 반영된다.
      const tick = async () => {
        frameCounter.current++;

        // 단일 프레임 캡처 (하드웨어 호출 1회로 통일)
        const frame = await captureFrame("reflex");
        if (frame && onFrameRef.current) {
          // Reflex 플러그인 없는 바이너리(takePhoto 폴백)는 float32를 비워 둔다.
          // TFLite 폴백(requiresFloat32=true)이면 base64에서 즉시 복원해 온디바이스 탐지를 살린다.
          if (
            requiresFloat32Ref.current &&
            frame.float32.length === 0 &&
            frame.base64
          ) {
            frame.float32 = decodeBase64JpegToHwc(frame.base64);
          }
          // 반사 경로로 즉시 전달
          onFrameRef.current(frame);

          // 매 N번째 프레임마다 동일 프레임을 인지 경로로 전달 (중복 캡처 제거)
          const ratio = Math.max(1, Math.floor(reflexFps / cognitiveFps));
          if (frameCounter.current % ratio === 0) {
            onFrameRef.current({
              ...frame,
              stream: "cognitive",
            });
          }
        }

        // stopCapture()가 이미 호출되어 null이 됐다면 재예약하지 않는다.
        if (reflexTimerRef.current !== null) {
          reflexTimerRef.current = setTimeout(tick, currentIntervalRef.current);
        }
      };

      reflexTimerRef.current = setTimeout(tick, currentIntervalRef.current);

      console.log(
        `[Camera] ${isMockMode ? "Mock" : "Real"} 통합 단일 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성, supportsStream=${captureProvider.supportsStream})`,
      );
    },
    [
      reflexFps,
      cognitiveFps,
      isCapturing,
      isMockMode,
      captureFrame,
      useStreamCapture,
      intervalSharedValue,
    ],
  );

  const stopCapture = useCallback(() => {
    if (reflexTimerRef.current) {
      clearTimeout(reflexTimerRef.current);
      reflexTimerRef.current = null;
    }
    if (cognitiveTimerRef.current) {
      clearInterval(cognitiveTimerRef.current);
      cognitiveTimerRef.current = null;
    }
    onFrameRef.current = null;
    streamFrameCounterRef.current = 0;
    setIsCapturing(false);
    console.log("[Camera] 루프 중지");
  }, []);

  useEffect(() => {
    return () => stopCapture();
  }, [stopCapture]);

  return {
    cameraRef,
    device,
    hasPermission: effectivePermission,
    permissionStatus: isMockMode
      ? "mock"
      : hasPermission
        ? "granted"
        : permissionRequested
          ? "denied"
          : "not-requested",
    isCapturing,
    isMockMode,
    currentReflexFps,
    startCapture,
    stopCapture,
    setCapturePaused,
    setRequiresFloat32,
    requestCameraPermission,
    reportInferenceLatency,
    reportServerLoad,
    useStreamCapture,
    frameProcessor: useStreamCapture
      ? (captureProvider.frameProcessor as ReturnType<typeof useFrameProcessor>)
      : undefined,
  };
}
