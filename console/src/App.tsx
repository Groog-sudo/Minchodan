import { BrowserRouter, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useState, useEffect } from "react";
import { StatusBadge } from "./components/StatusBadge";
import {
  ADMIN_TOKEN_KEY,
  readAdminToken,
  subscribeAdminAuthExpired,
} from "./api/adminAuth";
import { useMonitorStream } from "./api/useMonitorStream";
import { useLiveFeed } from "./api/useLiveFeed";
import { Login } from "./components/Login";
import { DashboardPage } from "./pages/DashboardPage";
import { MembersPage } from "./pages/MembersPage";

function connectionTone(connection: string) {
  if (connection === "connected") return "good";
  if (connection === "connecting") return "warn";
  if (connection === "error") return "bad";
  return "idle";
}

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return isActive ? "main-nav-link main-nav-link-active" : "main-nav-link";
}

function Layout({
  connection,
  isDemoMode,
  onInjectDemo,
  onLogout,
}: {
  connection: string;
  isDemoMode: boolean;
  onInjectDemo: () => void;
  onLogout: () => void;
}) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <img src="/gildang-logo.jpeg" alt="GILDANG Logo" className="gildang-logo" />
          <div>
            <p className="eyebrow">GILDANG Operator Console</p>
            <h1>스마트 가이드독 실시간 관제</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <StatusBadge label={connection} tone={connectionTone(connection)} />
          {isDemoMode && (
            <button type="button" onClick={onInjectDemo}>샘플 이벤트</button>
          )}
          <button type="button" className="logout-btn" onClick={onLogout}>
            [ LOGOUT ]
          </button>
        </div>
      </header>

      <nav className="main-nav">
        <NavLink to="/" end className={navLinkClassName}>
          관제 대시보드
        </NavLink>
        <NavLink to="/members" className={navLinkClassName}>
          회원 관리
        </NavLink>
      </nav>

      <Outlet />
    </main>
  );
}

export default function App() {
  // 새로고침 시 로그인 풀림 방지를 위해 localStorage에 토큰을 영속 보존합니다.
  // 만료된 JWT는 읽기 시점에 제거해 401 스팸을 막는다.
  const [token, setToken] = useState<string | null>(() => readAdminToken());

  // 토큰 변경 시 localStorage 반영 사이드 이펙트를 useEffect로 격리
  useEffect(() => {
    if (token) {
      localStorage.setItem(ADMIN_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    }
  }, [token]);

  // API/SSE에서 401이 나면 forceAdminRelogin → 로그인 화면으로 복귀
  useEffect(() => {
    return subscribeAdminAuthExpired(() => {
      setToken(null);
    });
  }, []);

  const { state, streamUrl, injectDemoEvents } = useMonitorStream(token);
  // 대시보드/회원관리 두 화면이 같은 실시간 연결(SSE+WS)을 공유하도록 App 최상단에서
  // 1번만 구독한다(페이지 전환마다 재연결되지 않게).
  const liveFeed = useLiveFeed(token);
  const isDemoMode =
    import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEMO_DATA === "true";

  // 토큰이 없으면 무조건 로그인 화면만 띄움!
  if (!token) {
    return (
      <Login
        onLogin={(newToken) => {
          setToken(newToken);
        }}
      />
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <Layout
              connection={state.connection}
              isDemoMode={isDemoMode}
              onInjectDemo={injectDemoEvents}
              onLogout={() => {
                setToken(null);
              }}
            />
          }
        >
          <Route
            index
            element={
              <DashboardPage
                token={token}
                state={state}
                streamUrl={streamUrl}
                liveFeed={liveFeed}
                isDemoMode={isDemoMode}
              />
            }
          />
          <Route path="members" element={<MembersPage token={token} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
