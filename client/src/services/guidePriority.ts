/**
 * 음성/경보 우선순위 (높을수록 선점).
 *
 * 1. STT 상호작용(길찾아줘 / 물어볼게) - 질문 중 위험 안내·비프·햅틱 억제
 * 2. Near 위험 채널(햅틱·비프·12시 NEAR 음성)
 * 3. 12시 MED 탐지 안내
 * 4. 그 외 (FAR·비정면·온보딩·연결 고지 등)
 */

export const GUIDE_PRIORITY = {
  OTHER: 1,
  FRONT_MED: 2,
  FRONT_NEAR: 3,
  STT: 4,
} as const;

export type GuidePriority =
  (typeof GUIDE_PRIORITY)[keyof typeof GUIDE_PRIORITY];

/** STT 녹음 시작 시 Near 음성까지 포함해 선점(질문 방해 방지). */
export const STT_PREEMPT_MAX_PRIORITY: GuidePriority = GUIDE_PRIORITY.FRONT_NEAR;

function normalizeDistanceClass(
  distanceClass: string | null | undefined,
): "near" | "medium" | "far" | "" {
  const raw = String(distanceClass ?? "")
    .trim()
    .toLowerCase();
  if (raw === "near" || raw === "medium" || raw === "far") return raw;
  if (raw === "med" || raw === "mid") return "medium";
  return "";
}

/** 서버 clock_direction 예: "12시". 숫자만 온 경우도 허용. */
export function isTwelveOClockDirection(
  clockDirection: string | null | undefined,
): boolean {
  if (!clockDirection) return false;
  const s = String(clockDirection).trim();
  if (s === "12" || s === "12시") return true;
  return /^12\s*시/.test(s);
}

/**
 * guide / speakFallback 호출용 우선순위 해석.
 * STT(길찾아줘/물어볼게 답변)가 최상위.
 */
export function resolveGuidePriority(opts: {
  isStt?: boolean;
  clockDirection?: string | null;
  distanceClass?: string | null;
}): GuidePriority {
  if (opts.isStt) return GUIDE_PRIORITY.STT;

  const front = isTwelveOClockDirection(opts.clockDirection);
  const dist = normalizeDistanceClass(opts.distanceClass);
  if (front && dist === "near") return GUIDE_PRIORITY.FRONT_NEAR;
  if (front && dist === "medium") return GUIDE_PRIORITY.FRONT_MED;
  return GUIDE_PRIORITY.OTHER;
}
