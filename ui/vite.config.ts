import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The coordinator serves the API on 127.0.0.1:8787; in dev, Vite proxies to it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    fs: { allow: [".."] },
    proxy: {
      "/api": { target: "http://127.0.0.1:8787", changeOrigin: false },
      "/media": { target: "http://127.0.0.1:8787", changeOrigin: false },
    },
  },
});
