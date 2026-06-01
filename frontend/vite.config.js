import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/__BASE_PATH__/",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      "/auth":     "http://localhost:8000",
      "/employee": "http://localhost:8000",
      "/vendor":   "http://localhost:8000",
      "/admin":    "http://localhost:8000",
      "/health":   "http://localhost:8000",
      "/uploads":  "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
    },
  },
});
