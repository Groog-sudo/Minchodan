import { useEffect, useRef, useState } from "react";
import "./LiveCameraFeed.css";
import { resolveServiceUrl } from "../config/network";

interface LiveCameraFeedProps {
  imageUrl: string | null;
  latestDetections: any[];
  connected: boolean;
  lastGps?: { lat: number; lon: number; heading: number } | null;
}

const NAV_MAP_URL =
  resolveServiceUrl(
    import.meta.env.VITE_NAV_MAP_URL,
    "/navigation/?embed=true",
    import.meta.env.VITE_API_BASE_URL,
  );
// 2026-07-13 정정: jh가 Android 테스트 중(카메라 센서가 90도 꺾여 들어오는 기종)
// 이 값을 90으로 하드코딩해뒀는데, 콘솔은 iOS/Android 기기를 가리지 않고 보는
// 공용 화면이라 iPhone 프레임에는 이 보정이 오히려 잘못 적용됐다(실기기 실측
// 확인). 기기별 platform 정보가 WS 페이로드에 없어 자동 분기는 아직 불가하므로,
// 우선 0(무회전)으로 되돌린다. Android로 다시 테스트할 때 필요하면 90으로 바꿀 것.
const LIVE_FEED_ROTATE_DEG = 0;

function getDisplayBBox(
  bbox: { x: number; y: number; w: number; h: number },
  natural: { w: number; h: number },
): { leftPct: number; topPct: number; widthPct: number; heightPct: number } {
  const { x, y, w, h } = bbox;
  const srcW = natural.w;
  const srcH = natural.h;

  if (LIVE_FEED_ROTATE_DEG === 0) {
    return {
      leftPct: (x / srcW) * 100,
      topPct: (y / srcH) * 100,
      widthPct: (w / srcW) * 100,
      heightPct: (h / srcH) * 100,
    };
  }

  // 왼쪽으로 90도 꺾여 들어오는 프레임(Android 등)을 모바일 시점(CW 90도)으로 보정.
  const rotatedX = srcH - (y + h);
  const rotatedY = x;
  const rotatedW = h;
  const rotatedH = w;
  const dstW = srcH;
  const dstH = srcW;

  return {
    leftPct: (rotatedX / dstW) * 100,
    topPct: (rotatedY / dstH) * 100,
    widthPct: (rotatedW / dstW) * 100,
    heightPct: (rotatedH / dstH) * 100,
  };
}

function getColorForClass(className: string): string {
  const c = className.toLowerCase();
  if (c.includes("person") || c.includes("pedestrian")) return "#10b981"; // Emerald Green
  if (c.includes("car") || c.includes("truck") || c.includes("bus") || c.includes("motorcycle") || c.includes("vehicle")) return "#ef4444"; // Vivid Red
  if (c.includes("bollard") || c.includes("pole") || c.includes("tree") || c.includes("obstacle") || c.includes("barrier")) return "#f59e0b"; // Alert Amber
  if (c.includes("caution") || c.includes("warning") || c.includes("danger") || c.includes("construction")) return "#ec4899"; // Pink/Magenta
  if (c.includes("crosswalk") || c.includes("sidewalk") || c.includes("walkway")) return "#3b82f6"; // Blue
  return "#8b5cf6"; // Purple
}

export function LiveCameraFeed({ imageUrl, latestDetections, connected, lastGps }: LiveCameraFeedProps) {
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null);
  const [mapVisible, setMapVisible] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // 앱 실기기 GPS 좌표가 갱신될 때마다 HUD 미니맵 iframe으로 주입한다.
  // navigation/index.html의 window.message 리스너가 { type: 'inject_gps', lat, lon, heading }을 수신해
  // 지도 마커를 실기기 위치로 갱신한다. PC 브라우저 GPS 부정확 문제를 완전히 우회한다.
  useEffect(() => {
    if (!lastGps || !iframeRef.current?.contentWindow) return;
    iframeRef.current.contentWindow.postMessage(
      { type: "inject_gps", lat: lastGps.lat, lon: lastGps.lon, heading: lastGps.heading },
      "*"
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
        </div>
        <span className="panel-kicker">실기기 카메라 화면 (실시간 BBox 및 GPS HUD 오버레이)</span>
      </div>

      <div className="live-feed-viewport">
        {imageUrl ? (
          <div className="feed-image-container frame-overlay-wrap">
            <img
              src={imageUrl}
              alt="실기기 실시간 화면"
              className="feed-image frame-overlay-image live-feed-rotated"
              style={{ transform: `rotate(${LIVE_FEED_ROTATE_DEG}deg)` }}
              onLoad={(event) => {
                const img = event.currentTarget;
                setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
              }}
            />
            {naturalSize &&
              latestDetections.map((det: any, index: number) => {
                if (!det.bbox) return null;
                const { x, y, w, h } = det.bbox;
                const displayBBox = getDisplayBBox({ x, y, w, h }, naturalSize);
                const color = getColorForClass(det.className);
                return (
                  <div
                    key={index}
                    className="frame-overlay-box"
                    style={{
                      left: `${displayBBox.leftPct}%`,
                      top: `${displayBBox.topPct}%`,
                      width: `${displayBBox.widthPct}%`,
                      height: `${displayBBox.heightPct}%`,
                      borderColor: color,
                      boxShadow: `0 0 6px ${color}`,
                    }}
                  >
                    <span
                      className="frame-overlay-label"
                      style={{
                        backgroundColor: color,
                        color: "#000000",
                        fontWeight: 900
                      }}
                    >
                      {det.className.toUpperCase()} ({(det.confidence * 100).toFixed(0)}%)
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
                📡 HUD MAP ON
              </button>
            )}

            <div className="feed-overlay-scanner"></div>
          </div>
        ) : (
          <div className="feed-placeholder">
            <div className="placeholder-icon">📷</div>
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
