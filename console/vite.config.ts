import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://100.85.229.93:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://100.85.229.93:8000",
        ws: true,
      },
      "/navigation": {
        target: "http://100.85.229.93:8000",
        changeOrigin: true,
      },
    },
  },
});
