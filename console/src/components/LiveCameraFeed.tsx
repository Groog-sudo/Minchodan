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

  // platform에 따른 동적 회전 각도 결정 (Android는 기본 90도, iOS 및 기타는 0도)
  const defaultRotate = platform === "android" ? 90 : 0;
  const [rotateDeg, setRotateDeg] = useState<number>(defaultRotate);

  // platform prop이 변경되면 (예: 다른 세션 연결) 기본값으로 재설정
  useEffect(() => {
    setRotateDeg(platform === "android" ? 90 : 0);
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
          실기기 카메라 화면 (실시간 BBox 및 GPS HUD 오버레이)
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

            {/* 2026-07-19: Near/Medium/Far 거리 구역 호 오버레이 (SVG).
                호 끝점을 좌·우 화면 가장자리(x=0, x=W)에 고정. 측면선은 제거. */}
            {naturalSize && (
              <svg
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
                  const edgeArc = (edgeYRatio: number) => {
                    const edgeY = H * edgeYRatio;
                    const r = Math.sqrt(apexX ** 2 + (edgeY - apexY) ** 2);
                    return {
                      d: `M 0 ${edgeY} A ${r} ${r} 0 0 1 ${W} ${edgeY}`,
                      edgeY,
                    };
                  };
                  const nearArc = edgeArc(0.78);
                  const medArc = edgeArc(0.52);
                  return (
                    <>
                      <path d={nearArc.d} fill="none" stroke="#EF4444" strokeWidth={2} strokeOpacity={0.75} />
                      <path d={medArc.d} fill="none" stroke="#F59E0B" strokeWidth={2} strokeOpacity={0.75} />
                      {/* 12시 방향 중심선 (Near/Med 호 유지, cyan 추가) */}
                      <line
                        x1={apexX}
                        y1={apexY}
                        x2={apexX}
                        y2={H}
                        stroke="#22D3EE"
                        strokeWidth={3}
                        strokeOpacity={0.95}
                      />
                      <text x={W - 44} y={nearArc.edgeY - 6} fill="#EF4444" fontSize={11} fontWeight="bold">NEAR</text>
                      <text x={W - 40} y={medArc.edgeY - 6} fill="#F59E0B" fontSize={11} fontWeight="bold">MED</text>
                      <text x={apexX + 8} y={apexY - 4} fill="#3B82F6" fontSize={11} fontWeight="bold">FAR</text>
                      <text x={apexX + 8} y={H * 0.38} fill="#22D3EE" fontSize={11} fontWeight="bold">12시</text>
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
