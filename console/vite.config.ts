import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 2026-07-19: 컨테이너 환경 지원. compose에서 VITE_PROXY_TARGET 환경 변수로
// FastAPI 컨테이너(http://fastapi:8000)를 가리키도록 주입. 호스트에서 실행할 때는
// 환경 변수가 없으므로 기본값 http://127.0.0.1:8000이 그대로 적용되어 기존 동작 유지.
const apiTarget = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";
const wsTarget = apiTarget.replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/ws": {
        target: wsTarget,
        ws: true,
      },
      "/navigation": {
        target: apiTarget,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
