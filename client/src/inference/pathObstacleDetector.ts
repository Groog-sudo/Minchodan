import { Platform } from "react-native";
import { OnDeviceDetectionResult } from "../hooks/useOnDeviceDetection";

// 640x640 카메라 해상도 기준 설정
const FRAME_SIZE = 640;
const GRID_SIZE = 16; // 성능 최적화를 위한 16x16 격자 분할 (총 256셀)
const CELL_PIXELS = FRAME_SIZE / GRID_SIZE; // 셀 하나의 픽셀 크기 (40px)

export type ObstacleState = "STOP" | "BLOCKED" | "CAUTION" | "CLEAR";

export interface PathObstacleResult {
  state: ObstacleState;
  riskScore: number;
  bestTurn: "left" | "right" | "none";
  leftClearance: number;
  rightClearance: number;
}

class PathObstacleDetector {
  private history: ObstacleState[] = [];
  private readonly MAX_HISTORY = 5;

  /**
   * 주어진 격자 셀 좌표(col, row)가 사다리꼴 주행 통로 ROI 영역에 포함되는지 검사
   */
  private isInPathMask(col: number, row: number): boolean {
    const y = row * CELL_PIXELS + CELL_PIXELS / 2;
    const x = col * CELL_PIXELS + CELL_PIXELS / 2;

    // [P2 2026-07-14] top-y를 35%(224px)로 수정 - 서버 PATH_ROI_FAR_Y_RATIO=0.35 와 정합
    // 기존 50%(320px)는 원경 ROI를 과도하게 제외함.
    if (y < 224 || y > 640) return false;

    // 원근 왜곡 보정: y=224(상단) 너비 96px, y=640(하단) 너비 384px
    const progress = (y - 224) / 416; // 0.0 ~ 1.0
    const halfWidth = 48 + progress * 144;

    const centerX = 320;
    return x >= centerX - halfWidth && x <= centerX + halfWidth;
  }

  /**
   * 주어진 격자 셀 좌표(col, row)가 좌측 회피 ROI 영역에 포함되는지 검사
   */
  private isInLeftMask(col: number, row: number): boolean {
    const y = row * CELL_PIXELS + CELL_PIXELS / 2;
    const x = col * CELL_PIXELS + CELL_PIXELS / 2;
    if (y < 224 || y > 640) return false;

    const progress = (y - 224) / 416;
    const halfWidth = 48 + progress * 144;
    const centerX = 320;

    return x < centerX - halfWidth;
  }

  /**
   * 주어진 격자 셀 좌표(col, row)가 우측 회피 ROI 영역에 포함되는지 검사
   */
  private isInRightMask(col: number, row: number): boolean {
    const y = row * CELL_PIXELS + CELL_PIXELS / 2;
    const x = col * CELL_PIXELS + CELL_PIXELS / 2;
    if (y < 224 || y > 640) return false;

    const progress = (y - 224) / 416;
    const halfWidth = 48 + progress * 144;
    const centerX = 320;

    return x > centerX + halfWidth;
  }

  /**
   * 검출된 BBox 및 노면 주의/차도 영역 정보를 기반으로 16x16 격자의 가상 깊이맵(Pseudo Depth Map)을 빌드하고
   * 주행 통로의 막힘 유무와 회피 방향을 판정합니다.
   */
  public analyze(detections: OnDeviceDetectionResult[]): PathObstacleResult {
    // 1. 격자 뎁스 맵 초기화 (기본값 3.0m = 안전한 보도)
    const depthMap = Array(GRID_SIZE).fill(null).map(() => Array(GRID_SIZE).fill(3.0));

    // 2. 검출된 BBox(장애물 및 위험 노면)를 순회하며 격자에 최솟값(가장 가까운 거리)으로 깊이 투영
    for (const d of detections) {
      const { x, y, w, h } = d.bbox;
      const areaRatio = (w * h) / (FRAME_SIZE * FRAME_SIZE);

      // 원근 역산에 기반한 객체 거리 추정 (0.3m ~ 3.0m)
      let distance = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));

      // [P1 2026-07-14] 노면 세그(roadway/caution/sidewalk_normal/braille_normal) 전체를
      // depthMap 반사 경보 경로에서 제외한다.
      // 설계 원칙(MDPI 2023): 노면 클래스는 인지 경로(서버 LLM TTS) 전담이며,
      // 즉각 비프/햅틱(반사 경로)을 발동해서는 안 된다.
      // 노면 위험 판정은 server/detection/path_risk.py에서 별도 수행한다.
      if (d.model === "segmentation") continue;

      // 객체 바운딩 박스가 덮고 있는 격자 범위 계산
      const colStart = Math.max(0, Math.floor(x / CELL_PIXELS));
      const colEnd = Math.min(GRID_SIZE - 1, Math.floor((x + w) / CELL_PIXELS));
      const rowStart = Math.max(0, Math.floor(y / CELL_PIXELS));
      const rowEnd = Math.min(GRID_SIZE - 1, Math.floor((y + h) / CELL_PIXELS));

      for (let r = rowStart; r <= rowEnd; r++) {
        for (let c = colStart; c <= colEnd; c++) {
          depthMap[r][c] = Math.min(depthMap[r][c], distance);
        }
      }
    }

    // 3. 주행 통로(사다리꼴 ROI) 내부의 깊이값 수집
    const pathDepths: number[] = [];
    const leftDepths: number[] = [];
    const rightDepths: number[] = [];

    for (let r = 0; r < GRID_SIZE; r++) {
      for (let c = 0; c < GRID_SIZE; c++) {
        const val = depthMap[r][c];
        if (this.isInPathMask(c, r)) {
          pathDepths.push(val);
        } else if (this.isInLeftMask(c, r)) {
          leftDepths.push(val);
        } else if (this.isInRightMask(c, r)) {
          rightDepths.push(val);
        }
      }
    }

    if (pathDepths.length === 0) {
      return { state: "CLEAR", riskScore: 0.0, bestTurn: "none", leftClearance: 3.0, rightClearance: 3.0 };
    }

    // 4. 주행 통로 내 위험 픽셀 비중 및 최종 위험 점수 계산
    const near_07 = pathDepths.filter(d => d < 0.7).length / pathDepths.length;
    const near_15 = pathDepths.filter(d => d < 1.5).length / pathDepths.length;
    const near_30 = pathDepths.filter(d => d < 3.0).length / pathDepths.length;

    const riskScore = near_07 * 5.0 + near_15 * 2.0 + near_30 * 0.5;

    // 단발성 프레임 판정
    let frameState: ObstacleState = "CLEAR";
    if (near_07 > 0.08) {
      frameState = "STOP";
    } else if (near_15 > 0.18) {
      frameState = "BLOCKED";
    } else if (near_30 > 0.25) {
      frameState = "CAUTION";
    }

    // 5. 시간 누적 5프레임 슬라이딩 윈도우 필터
    this.history.push(frameState);
    if (this.history.length > this.MAX_HISTORY) {
      this.history.shift();
    }

    // 최근 5프레임 중 빈도가 가장 높은 상태를 도출 (동률인 경우 위험도가 높은 상태 우선 채택)
    const counts = this.history.reduce((acc, curr) => {
      acc[curr] = (acc[curr] || 0) + 1;
      return acc;
    }, {} as Record<ObstacleState, number>);

    let smoothedState = frameState;
    let maxCount = 0;
    const statePriority: Record<ObstacleState, number> = { STOP: 4, BLOCKED: 3, CAUTION: 2, CLEAR: 1 };

    for (const stateKey in counts) {
      const state = stateKey as ObstacleState;
      const count = counts[state];
      if (count > maxCount) {
        maxCount = count;
        smoothedState = state;
      } else if (count === maxCount) {
        // 빈도가 같은 경우 위험도가 더 높은 것을 최종 상태로 반영 (방어적 설계)
        if (statePriority[state] > statePriority[smoothedState]) {
          smoothedState = state;
        }
      }
    }

    // [P4 2026-07-14] 5프레임 중 3프레임 미달 시 CLEAR로 폴백 (방어적 설계).
    // 기존 frameState 폴백은 단발 오탐을 스무딩 없이 그대로 반영해 오경보를 유발했다.
    if (maxCount < 3) {
      smoothedState = "CLEAR";
    }

    // 6. 회피 공간 계산 (30th percentile 기법 적용으로 소형 돌출 장애물 누락 차단)
    const getPercentile = (arr: number[], p: number): number => {
      if (arr.length === 0) return 3.0;
      const sorted = [...arr].sort((a, b) => a - b);
      const index = Math.floor(sorted.length * p);
      return sorted[index] ?? 3.0;
    };

    const leftClearance = getPercentile(leftDepths, 0.3);
    const rightClearance = getPercentile(rightDepths, 0.3);

    let bestTurn: "left" | "right" | "none" = "none";
    if (smoothedState === "STOP" || smoothedState === "BLOCKED" || smoothedState === "CAUTION") {
      if (leftClearance > rightClearance && leftClearance > 1.2) {
        bestTurn = "left";
      } else if (rightClearance > leftClearance && rightClearance > 1.2) {
        bestTurn = "right";
      }
    }

    return {
      state: smoothedState,
      riskScore,
      bestTurn,
      leftClearance,
      rightClearance,
    };
  }
}

export const pathObstacleDetector = new PathObstacleDetector();
