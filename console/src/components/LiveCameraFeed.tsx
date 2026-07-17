import { useEffect, useRef, useState } from "react";
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

  // platform에 따른 동적 회전 각도 결정 (Android는 기본 90도, iOS 및 기타는 0도)
  const defaultRotate = platform === "android" ? 90 : 0;
  const [rotateDeg, setRotateDeg] = useState<number>(defaultRotate);

  // platform prop이 변경되면 (예: 다른 세션 연결) 기본값으로 재설정
  useEffect(() => {
    setRotateDeg(platform === "android" ? 90 : 0);
  }, [platform]);

  // 앱 실기기 GPS 좌표가 갱신될 때마다 HUD 미니맵 iframe으로 주입한다.
  // navigation/index.html의 window.message 리스너가 { type: 'inject_gps', lat, lon, heading }을 수신해
  // 지도 마커를 실기기 위치로 갱신한다. PC 브라우저 GPS 부정확 문제를 완전히 우회한다.
  useEffect(() => {
    if (!lastGps || !iframeRef.current?.contentWindow) return;
    iframeRef.current.contentWindow.postMessage(
      {
        type: "inject_gps",
        lat: lastGps.lat,
        lon: lastGps.lon,
        heading: lastGps.heading,
      },
      "*",
    );
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
                const color = getColorForClass(det.className);
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
                    </span>
                  </div>
                );
              })}

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
                ? "실기기 영상 프레임을 수신 대기 중입니다..."
                : "실시간 비디오 서버 연결을 시도하는 중..."}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
