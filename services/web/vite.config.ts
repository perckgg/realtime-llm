import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev server proxies /api to services/api (FastAPI, doc 01 §6.6). Until that
// service exists the app runs on fixtures — see src/api/client.ts.
const apiProxy = {
  "/api": {
    target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Alias `@/` phải khai ở CẢ hai nơi: tsconfig `paths` chỉ dạy TypeScript,
  // còn Vite phân giải import lúc chạy hoàn toàn độc lập với nó.
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: apiProxy,
  },
  preview: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: apiProxy,
  },
});
