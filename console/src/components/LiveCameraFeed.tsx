import { useEffect, useLayoutEffect, useRef, useState } from "react";
import "./LiveCameraFeed.css";
import { resolveServiceUrl } from "../config/network";

interface LiveCameraFeedProps {
  imageUrl: string | null;
  latestDetections: any[];
  connected: boolean;
  lastGps?: { lat: number; lon: number; heading: number } | null;
  platform?: string | null;
}

const NAV_MAP_URL = resolveServiceUrl(
  import.meta.env.VITE_NAV_MAP_URL,
  "/navigation/?embed=true",
  import.meta.env.VITE_API_BASE_URL,
);

function getDisplayBBox(
  bbox: { x: number; y: number; w: number; h: number },
  natural: { w: number; h: number },
  rotateDeg: number,
): { leftPct: number; topPct: number; widthPct: number; heightPct: number } {
  const { x, y, w, h } = bbox;
  const srcW = natural.w;
  const srcH = natural.h;

  let rx = x;
  let ry = y;
  let rw = w;
  let rh = h;
  let dstW = srcW;
  let dstH = srcH;

  const angle = ((rotateDeg % 360) + 360) % 360;

  if (angle === 90) {
    rx = srcH - y - h;
    ry = x;
    rw = h;
    rh = w;
    dstW = srcH;
    dstH = srcW;
  } else if (angle === 180) {
    rx = srcW - x - w;
    ry = srcH - y - h;
    rw = w;
    rh = h;
    dstW = srcW;
    dstH = srcH;
  } else if (angle === 270) {
    rx = y;
    ry = srcW - x - w;
    rw = h;
    rh = w;
    dstW = srcH;
    dstH = srcW;
  }

  return {
    leftPct: (rx / dstW) * 100,
    topPct: (ry / dstH) * 100,
    widthPct: (rw / dstW) * 100,
    heightPct: (rh / dstH) * 100,
  };
}

function getColorForClass(className: string): string {
  const c = className.toLowerCase();
  if (c.includes("person") || c.includes("pedestrian")) return "#10b981"; // Emerald Green
  if (
    c.includes("car") ||
    c.includes("truck") ||
    c.includes("bus") ||
    c.includes("motorcycle") ||
    c.includes("vehicle")
  )
    return "#ef4444"; // Vivid Red
  if (
    c.includes("bollard") ||
    c.includes("pole") ||
    c.includes("tree") ||
    c.includes("obstacle") ||
    c.includes("barrier")
  )
    return "#f59e0b"; // Alert Amber
  if (
    c.includes("caution") ||
    c.includes("warning") ||
    c.includes("danger") ||
    c.includes("construction")
  )
    return "#ec4899"; // Pink/Magenta
  if (
    c.includes("crosswalk") ||
    c.includes("sidewalk") ||
    c.includes("walkway")
  )
    return "#3b82f6"; // Blue
  return "#8b5cf6"; // Purple
}

// 2026-07-19: Near/Medium/Far 거리 구역 색상. 서버 effective_distance_zone 값을
// 그대로 사용해 3자 정합을 맞춘다. 단말 getZoneTag와 동일 팔레트.
function getColorForZone(zone: string): string {
  const z = (zone || "").toLowerCase();
  if (z === "near") return "#EF4444";
  if (z === "medium" || z === "med") return "#F59E0B";
  if (z === "far") return "#3B82F6";
  return ""; // 빈 문자열이면 zone 정보 없음 → 기존 클래스 색상 사용
}

function getZoneTag(zone: string): string {
  const z = (zone || "").toLowerCase();
  if (z === "near") return "NEAR";
  if (z === "medium" || z === "med") return "MED";
  if (z === "far") return "FAR";
  return "";
}

// ---------------------------------------------------------------------------
// 2계층 오버레이 기하 (도식만, 판정 SSOT 아님)
// L1 PATH ROI: 단말 CameraView PATH_ROI_* 와 동일 사다리꼴 (좌우 통로)
// L2 거리 호: distance_policy area_ratio → heuristic_m 경계의 사람 기준 원근 근사
// SSOT 판정은 BBox effective_distance_zone / area_ratio 태그·색상만 사용
// ---------------------------------------------------------------------------
const PATH_ROI_MID_Y = 0.5;
const PATH_ROI_NEAR_BAND = [0.2, 0.8] as const;
const PATH_ROI_FAR_BAND = [0.38, 0.62] as const;

/** distance_policy: heuristic_m ≈ 0.22 / sqrt(area_ratio) */
const HEURISTIC_COEFF = 0.22;
const NEAR_ENTER_AREA_RATIO = 0.1;
const MEDIUM_ENTER_AREA_RATIO = 0.03;
const NEAR_HEURISTIC_M = HEURISTIC_COEFF / Math.sqrt(NEAR_ENTER_AREA_RATIO); // ≈0.70m
const MED_HEURISTIC_M = HEURISTIC_COEFF / Math.sqrt(MEDIUM_ENTER_AREA_RATIO); // ≈1.27m

/**
 * 지면 접촉 Y 근사: 수평선(PATH_ROI_MID_Y) + 역비례 깊이.
 * k는 Near(≈0.70m) 접촉이 y≈0.78이 되도록 맞춤(기존 호와 연속).
 */
const GROUND_HORIZON_Y = PATH_ROI_MID_Y;
const GROUND_CALIB_K =
  (0.78 - GROUND_HORIZON_Y) * NEAR_HEURISTIC_M / (1 - GROUND_HORIZON_Y);

function contactYForHeuristicMeters(meters: number): number {
  if (meters <= 0) return 1;
  const y =
    GROUND_HORIZON_Y +
    (1 - GROUND_HORIZON_Y) * (GROUND_CALIB_K / meters);
  return Math.min(0.98, Math.max(GROUND_HORIZON_Y + 0.02, y));
}

function pathRoiPolygonPoints(W: number, H: number): string {
  const [nearLo, nearHi] = PATH_ROI_NEAR_BAND;
  const [farLo, farHi] = PATH_ROI_FAR_BAND;
  const yTop = PATH_ROI_MID_Y * H;
  const yBottom = H;
  const pts: [number, number][] = [
    [farLo * W, yTop],
    [farHi * W, yTop],
    [nearHi * W, yBottom],
    [nearLo * W, yBottom],
  ];
  return pts.map(([x, y]) => `${x},${y}`).join(" ");
}

function edgeArcPath(
  W: number,
  H: number,
  edgeYRatio: number,
  apexYRatio = 0.22,
): { d: string; edgeY: number } {
  const apexX = W / 2;
  const apexY = H * apexYRatio;
  const edgeY = H * edgeYRatio;
  const r = Math.sqrt(apexX ** 2 + (edgeY - apexY) ** 2);
  return {
    d: `M 0 ${edgeY} A ${r} ${r} 0 0 1 ${W} ${edgeY}`,
    edgeY,
  };
}

export function LiveCameraFeed({
  imageUrl,
  latestDetections,
  connected,
  lastGps,
  platform,
}: LiveCameraFeedProps) {
  const [naturalSize, setNaturalSize] = useState<{
    w: number;
    h: number;
  } | null>(null);
  const [mapVisible, setMapVisible] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  // iframe onLoad 콜백(마운트 시 1회)이 항상 최신 lastGps를 읽도록 ref로 미러링한다.
  // 렌더 순수성을 지키기 위해 mutation은 useLayoutEffect 안에서 수행한다(React Doctor 지적 반영).
  const lastGpsRef = useRef(lastGps);
  useLayoutEffect(() => {
    lastGpsRef.current = lastGps;
  }, [lastGps]);

  // 단말에서 정자세 JPEG를 보내도록 맞춘다(iOS/Android 모두). 콘솔 CSS 회전은
  // 운영자 수동 보정용이며 플랫폼별 기본값은 0 (2026-07-16 정본, Android 90 하드코딩 제거).
  const [rotateDeg, setRotateDeg] = useState<number>(0);

  useEffect(() => {
    setRotateDeg(0);
  }, [platform]);

  // 앱 실기기 GPS 좌표를 HUD 미니맵 iframe에 주입한다.
  // iframe 로드 전에 lastGps가 도착하면 유실되므로 onLoad에서도 재주입한다.
  const injectGpsToMap = () => {
    const gps = lastGpsRef.current;
    if (!gps || !iframeRef.current?.contentWindow) return;
    iframeRef.current.contentWindow.postMessage(
      {
        type: "inject_gps",
        lat: gps.lat,
        lon: gps.lon,
        heading: gps.heading,
      },
      "*",
    );
  };

  useEffect(() => {
    injectGpsToMap();
  }, [lastGps]);

  return (
    <section className="panel live-feed-panel">
      {/* Corner Corner-ticks for military console styling */}
      <div className="panel-corner-tick top-left"></div>
      <div className="panel-corner-tick top-right"></div>
      <div className="panel-corner-tick bottom-left"></div>
      <div className="panel-corner-tick bottom-right"></div>

      <div className="panel-header">
        <div className="live-title-group">
          <h2>Live Feed</h2>
          {connected ? (
            <span className="live-badge connected">
              <span className="live-dot blinking"></span>
              REC
            </span>
          ) : (
            <span className="live-badge disconnected">OFFLINE</span>
          )}

          <div className="feed-rotation-controls">
            <button
              type="button"
              className={`rotate-btn ${rotateDeg === 0 ? "active" : ""}`}
              onClick={() => setRotateDeg(0)}
              title="회전 각도 0도"
            >
              0°
            </button>
            <button
              type="button"
              className={`rotate-btn ${rotateDeg === 90 ? "active" : ""}`}
              onClick={() => setRotateDeg(90)}
              title="회전 각도 90도"
            >
              90°
            </button>
            <button
              type="button"
              className={`rotate-btn ${rotateDeg === 180 ? "active" : ""}`}
              onClick={() => setRotateDeg(180)}
              title="회전 각도 180도"
            >
              180°
            </button>
            <button
              type="button"
              className={`rotate-btn ${rotateDeg === 270 ? "active" : ""}`}
              onClick={() => setRotateDeg(270)}
              title="회전 각도 270도"
            >
              270°
            </button>
          </div>
        </div>
        <span className="panel-kicker">
          실기기 카메라 (BBox=area_ratio SSOT · L1 통로 ROI · L2 거리 호 근사 · GPS HUD)
        </span>
      </div>

      <div className="live-feed-viewport">
        {imageUrl ? (
          <div className="feed-image-container frame-overlay-wrap">
            <img
              src={imageUrl}
              alt="실기기 실시간 화면"
              className="feed-image frame-overlay-image live-feed-rotated"
              style={{ transform: `rotate(${rotateDeg}deg)` }}
              onLoad={(event) => {
                const img = event.currentTarget;
                setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
              }}
            />
            {naturalSize &&
              latestDetections.map((det: any, index: number) => {
                if (!det.bbox) return null;
                const { x, y, w, h } = det.bbox;
                const displayBBox = getDisplayBBox({ x, y, w, h }, naturalSize, rotateDeg);
                // 2026-07-19: 서버가 보낸 effective_distance_zone이 있으면 zone 색상을
                // 우선 적용. 없으면 기존 클래스 기반 색상으로 폴백.
                const zoneColor = getColorForZone(det.effective_distance_zone);
                const color = zoneColor || getColorForClass(det.className);
                const zoneTag = getZoneTag(det.effective_distance_zone);
                const isSeg = det.model === "segmentation";
                const detKey =
                  det.track_id ??
                  `${det.className ?? "unknown"}-${Math.round(x)}-${Math.round(y)}-${Math.round(w)}-${Math.round(h)}-${index}`;
                return (
                  <div
                    key={detKey}
                    className={
                      isSeg
                        ? "frame-overlay-box frame-overlay-seg"
                        : "frame-overlay-box"
                    }
                    style={{
                      left: `${displayBBox.leftPct}%`,
                      top: `${displayBBox.topPct}%`,
                      width: `${displayBBox.widthPct}%`,
                      height: `${displayBBox.heightPct}%`,
                      borderColor: color,
                      borderStyle: isSeg ? "dashed" : "solid",
                      borderWidth: isSeg ? "1px" : "2px",
                      backgroundColor: isSeg ? `${color}33` : "transparent",
                      boxShadow: isSeg
                        ? `inset 0 0 10px ${color}, 0 0 4px ${color}`
                        : `0 0 6px ${color}`,
                    }}
                  >
                    <span
                      className="frame-overlay-label"
                      style={{
                        backgroundColor: color,
                        color: "#000000",
                        fontWeight: 900,
                      }}
                    >
                      {det.className.toUpperCase()}{" "}
                      {isSeg ? "" : `(${(det.confidence * 100).toFixed(0)}%)`}
                      {zoneTag ? ` ${zoneTag}` : ""}
                    </span>
                  </div>
                );
              })}

            {/* 2026-07-21: 2계층 도식 오버레이 (판정 SSOT 아님).
                L1 PATH ROI = 단말과 동일 사다리꼴(좌우 통로).
                L2 거리 호 = area_ratio→heuristic_m 경계의 사람 기준 원근 근사. */}
            {naturalSize && (
              <svg
                className="feed-dual-layer-overlay"
                width="100%"
                height="100%"
                viewBox={`0 0 ${naturalSize.w} ${naturalSize.h}`}
                preserveAspectRatio="none"
                style={{
                  position: "absolute",
                  inset: 0,
                  pointerEvents: "none",
                  transform: `rotate(${rotateDeg}deg)`,
                  transformOrigin: "center",
                }}
              >
                {(() => {
                  const W = naturalSize.w;
                  const H = naturalSize.h;
                  const apexX = W / 2;
                  const apexY = H * 0.22;
                  const fontPx = Math.max(10, Math.round(Math.min(W, H) * 0.018));
                  const strokeScale = Math.max(1.5, Math.min(W, H) * 0.003);

                  const nearY = contactYForHeuristicMeters(NEAR_HEURISTIC_M);
                  const medY = contactYForHeuristicMeters(MED_HEURISTIC_M);
                  const nearArc = edgeArcPath(W, H, nearY);
                  const medArc = edgeArcPath(W, H, medY);

                  return (
                    <>
                      {/* L1: PATH ROI (통로) */}
                      <polygon
                        points={pathRoiPolygonPoints(W, H)}
                        fill="rgba(34, 211, 238, 0.06)"
                        stroke="#22D3EE"
                        strokeWidth={strokeScale}
                        strokeOpacity={0.85}
                        strokeDasharray={`${strokeScale * 4} ${strokeScale * 3}`}
                      />
                      <text
                        x={apexX}
                        y={PATH_ROI_MID_Y * H + fontPx + 2}
                        fill="#22D3EE"
                        fontSize={fontPx}
                        fontWeight="bold"
                        textAnchor="middle"
                        opacity={0.9}
                      >
                        L1 PATH ROI
                      </text>

                      {/* L2: 거리 호 (사람 기준 원근 근사) */}
                      <path
                        d={nearArc.d}
                        fill="none"
                        stroke="#EF4444"
                        strokeWidth={strokeScale}
                        strokeOpacity={0.8}
                      />
                      <path
                        d={medArc.d}
                        fill="none"
                        stroke="#F59E0B"
                        strokeWidth={strokeScale}
                        strokeOpacity={0.8}
                      />
                      <line
                        x1={apexX}
                        y1={apexY}
                        x2={apexX}
                        y2={H}
                        stroke="#22D3EE"
                        strokeWidth={strokeScale * 1.4}
                        strokeOpacity={0.95}
                      />
                      <text
                        x={W - 8}
                        y={nearArc.edgeY - 4}
                        fill="#EF4444"
                        fontSize={fontPx}
                        fontWeight="bold"
                        textAnchor="end"
                      >
                        {`NEAR ~${NEAR_HEURISTIC_M.toFixed(1)}m (a≥${NEAR_ENTER_AREA_RATIO})`}
                      </text>
                      <text
                        x={W - 8}
                        y={medArc.edgeY - 4}
                        fill="#F59E0B"
                        fontSize={fontPx}
                        fontWeight="bold"
                        textAnchor="end"
                      >
                        {`MED ~${MED_HEURISTIC_M.toFixed(1)}m (a≥${MEDIUM_ENTER_AREA_RATIO})`}
                      </text>
                      <text
                        x={apexX + 8}
                        y={apexY - 4}
                        fill="#3B82F6"
                        fontSize={fontPx}
                        fontWeight="bold"
                      >
                        FAR
                      </text>
                      <text
                        x={apexX + 8}
                        y={H * 0.38}
                        fill="#22D3EE"
                        fontSize={fontPx}
                        fontWeight="bold"
                      >
                        12시
                      </text>
                      <text
                        x={8}
                        y={H - 8}
                        fill="#94A3B8"
                        fontSize={fontPx}
                        fontWeight="bold"
                      >
                        L2 거리호=사람근사 · 태그/색=SSOT
                      </text>
                    </>
                  );
                })()}
              </svg>
            )}

            {/* Tactical GPS HUD Minimap Overlay */}
            {mapVisible && (
              <div className="hud-minimap-container">
                <div className="hud-minimap-header">
                  <div className="hud-header-left">
                    <span className="hud-pulse-dot"></span>
                    <span>GPS TRACKING HUD</span>
                    <span className="hud-gps-coords">
                      {lastGps
                        ? `${lastGps.lat.toFixed(5)}, ${lastGps.lon.toFixed(5)}`
                        : "앱 좌표 대기"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="hud-toggle-btn"
                    onClick={() => setMapVisible(false)}
                    title="HUD 끄기"
                  >
                    [CLOSE]
                  </button>
                </div>
                <iframe
                  ref={iframeRef}
                  src={NAV_MAP_URL}
                  title="스마트 가이드독 HUD 미니맵"
                  className="hud-minimap-iframe"
                  allow="geolocation; accelerometer; gyroscope"
                  onLoad={injectGpsToMap}
                ></iframe>
              </div>
            )}

            {!mapVisible && (
              <button
                type="button"
                className="hud-restore-btn"
                onClick={() => setMapVisible(true)}
              >
                HUD MAP ON
              </button>
            )}

            <div className="feed-overlay-scanner"></div>
          </div>
        ) : (
          <div className="feed-placeholder">
            <div className="placeholder-icon">VIDEO</div>
            <p className="placeholder-text">
              {connected
                ? "콘솔 연결됨. 앱이 서버에 연결되어 있고 '탐지 시작'이 켜져 있어야 영상이 옵니다."
                : "실시간 비디오 서버 연결을 시도하는 중..."}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
