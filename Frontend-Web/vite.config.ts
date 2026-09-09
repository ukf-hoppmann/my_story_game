/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Requests arrive proxied via nginx with Host: storygame.localhost (see
    // configs/nginx/storygame.conf); "localhost" stays allowed too so direct
    // access on FRONTEND_HOST_PORT (bypassing the proxy) keeps working.
    allowedHosts: ["storygame.localhost", "localhost"],
    hmr: {
      host: "storygame.localhost",
      clientPort: 80,
      protocol: "ws",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/setupTests.ts"],
    globals: true,
  },
});
