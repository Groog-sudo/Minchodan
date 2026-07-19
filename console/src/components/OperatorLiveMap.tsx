// 관제 콘솔 실시간 보행 지도. 무거운 지도 라이브러리를 콘솔이 직접 들지 않고,
// 메인 FastAPI(8000) 하위에 마운트된 네비게이션 서브앱의 embed 모드 화면을
// iframe으로 가져와 렌더링 부하를 없앤다.
// 2026-07-11 정정: 구버전 8001 독립 포트 하드코딩을 8000 서브앱 경로로 교체
// (docs/dev-guides/integration/관제_UI_및_시나리오_연동_지침서.md §2).
// 원격(Tailscale) 관제 시에는 VITE_NAV_MAP_URL로 주소를 주입한다.
import { resolveServiceUrl } from "../config/network";

const NAV_MAP_URL =
  resolveServiceUrl(
    import.meta.env.VITE_NAV_MAP_URL,
    "/navigation/?embed=true",
    import.meta.env.VITE_API_BASE_URL,
  );

export function OperatorLiveMap() {
  return (
    <section className="panel" style={{ minHeight: "400px", padding: 0, overflow: "hidden" }}>
      <iframe
        src={NAV_MAP_URL}
        title="스마트 가이드독 실시간 보행 관제 지도"
        width="100%"
        height="100%"
        style={{ border: "none", display: "block", minHeight: "400px" }}
        allow="geolocation; accelerometer; gyroscope"
      ></iframe>
    </section>
  );
}
