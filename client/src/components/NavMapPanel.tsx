/**
 * 하단 T맵 지도 패널 (운영자/데모용 시각 자료).
 * 정적 표시 전용: 지도 인터랙션은 완전히 비활성화하고(터치는 STT press-and-hold
 * 레이어 소유), 현재 위치 마커만 주기 갱신한다. 종단 사용자는 시각장애인이므로
 * 이 패널은 발표·모니터링 보조 용도다.
 *
 * 성능 원칙(2026-07-11 합의):
 * - 인터랙션 없음: pointerEvents="none" + 지도 드래그/줌 비활성
 * - 마커 갱신 2초 스로틀: WebView injectJavaScript 호출 빈도 제한
 * - 토글 표시: 꺼져 있으면 WebView 자체를 마운트하지 않아 부하 0
 */

import { useEffect, useMemo, useRef } from "react";
import { StyleSheet, Text, View } from "react-native";
import { WebView } from "react-native-webview";

export interface NavMapWaypoint {
  lat: number;
  lon: number;
}

interface NavMapPanelProps {
  appKey: string;
  waypoints: NavMapWaypoint[];
  /** 현재 GPS 좌표 (호출측에서 이미 2초 스로틀 적용) */
  current: NavMapWaypoint | null;
}

const MARKER_INJECT_MIN_INTERVAL_MS = 2000;

function buildMapHtml(appKey: string, waypoints: NavMapWaypoint[]): string {
  const pointsJson = JSON.stringify(waypoints.map((w) => [w.lat, w.lon]));
  const center = waypoints.length > 0 ? [waypoints[0].lat, waypoints[0].lon] : [37.5665, 126.978];
  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no" />
<style>
  html, body, #map { margin:0; padding:0; width:100%; height:100%; background:#111; }
  /* 정적 표시 전용: 지도 내부 터치/제스처 전면 차단 */
  #map { pointer-events: none; }
  /* Release 빌드는 JS 콘솔을 볼 수 없어 로딩 단계/오류를 패널 위에 직접 표시한다 */
  #st { position:fixed; top:2px; left:4px; z-index:9999; color:#9CA3AF;
        font:10px monospace; background:rgba(0,0,0,0.5); padding:1px 4px;
        border-radius:3px; pointer-events:none; }
</style>
</head>
<body>
<div id="map"></div>
<div id="st">SDK 로딩...</div>
<script>
  function st(msg) {
    var el = document.getElementById("st");
    if (el) el.textContent = msg;
  }
  window.onerror = function (m, s, l) { st("오류: " + m + " @" + l); return true; };
</script>
<script src="https://apis.openapi.sk.com/tmap/jsv2?version=1&appKey=${appKey}"
        onerror="st('SDK 스크립트 로드 실패(네트워크/키)')"></script>
<script>
  var map = null;
  var marker = null;
  var points = ${pointsJson};
  var waited = 0;

  function init() {
    if (!window.Tmapv2 || !window.Tmapv2.Map) {
      waited += 200;
      if (waited >= 8000) { st("SDK 미로드(8초 초과) - 키/네트워크 확인"); return; }
      setTimeout(init, 200);
      return;
    }
    st("지도 생성 중...");
    map = new Tmapv2.Map("map", {
      center: new Tmapv2.LatLng(${center[0]}, ${center[1]}),
      zoom: 16,
      width: "100%",
      height: "100%"
    });
    st("경로 " + points.length + "pt");
    setTimeout(function () {
      var el = document.getElementById("st");
      if (el && el.textContent.indexOf("오류") < 0) el.style.display = "none";
    }, 4000);
    if (points.length > 1) {
      var path = points.map(function (p) { return new Tmapv2.LatLng(p[0], p[1]); });
      new Tmapv2.Polyline({
        path: path,
        strokeColor: "#2563EB",
        strokeWeight: 5,
        map: map
      });
      var bounds = new Tmapv2.LatLngBounds();
      path.forEach(function (ll) { bounds.extend(ll); });
      map.fitBounds(bounds);
    }
  }

  /* RN에서 injectJavaScript로 호출: 현재 위치 마커 갱신 */
  window.__setPos = function (lat, lon) {
    if (!map) return;
    var ll = new Tmapv2.LatLng(lat, lon);
    if (!marker) {
      marker = new Tmapv2.Marker({ position: ll, map: map });
    } else {
      marker.setPosition(ll);
    }
  };

  init();
</script>
</body>
</html>`;
}

export function NavMapPanel({ appKey, waypoints, current }: NavMapPanelProps) {
  const webRef = useRef<WebView>(null);
  const lastInjectTsRef = useRef(0);

  // 경로가 바뀔 때만 HTML을 재생성한다(마커 갱신은 injectJavaScript로 처리해
  // WebView 리로드를 유발하지 않는다).
  const html = useMemo(() => buildMapHtml(appKey, waypoints), [appKey, waypoints]);

  useEffect(() => {
    if (!current || !webRef.current) return;
    const now = Date.now();
    if (now - lastInjectTsRef.current < MARKER_INJECT_MIN_INTERVAL_MS) return;
    lastInjectTsRef.current = now;
    webRef.current.injectJavaScript(
      `window.__setPos && window.__setPos(${current.lat}, ${current.lon}); true;`,
    );
  }, [current]);

  if (!appKey) {
    return (
      <View style={styles.placeholder}>
        <Text style={styles.placeholderText}>경로를 설정하면 지도가 표시됩니다</Text>
      </View>
    );
  }

  return (
    <View style={styles.container} pointerEvents="none">
      {/* Release 빌드 진단용 캡션: nav_route 수신 여부를 패널에서 직접 확인 */}
      <Text style={styles.caption}>
        {`경로 ${waypoints.length}pt / key ${appKey ? "OK" : "없음"}`}
      </Text>
      <WebView
        ref={webRef}
        originWhitelist={["*"]}
        source={{ html }}
        style={styles.webview}
        scrollEnabled={false}
        bounces={false}
        javaScriptEnabled
        domStorageEnabled
        androidLayerType="hardware"
        setSupportMultipleWindows={false}
        allowsInlineMediaPlayback={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    borderRadius: 8,
    overflow: "hidden",
    backgroundColor: "#111827",
  },
  webview: {
    flex: 1,
    backgroundColor: "#111827",
  },
  placeholder: {
    flex: 1,
    borderRadius: 8,
    backgroundColor: "rgba(17, 24, 39, 0.85)",
    alignItems: "center",
    justifyContent: "center",
  },
  placeholderText: {
    color: "#9CA3AF",
    fontSize: 12,
    fontFamily: "monospace",
  },
  caption: {
    position: "absolute",
    bottom: 2,
    right: 6,
    zIndex: 10,
    color: "#9CA3AF",
    fontSize: 9,
    fontFamily: "monospace",
  },
});
