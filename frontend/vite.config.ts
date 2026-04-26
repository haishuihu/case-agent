import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/** LLM 多阶段生成可能持续数分钟；默认代理超时过短会导致连接被掐断（浏览器报 ERR_NETWORK_IO_SUSPENDED 等） */
const LONG_RUNNING_PROXY_MS = 60 * 60 * 1000; // 60 分钟

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
    timeout: LONG_RUNNING_PROXY_MS,
    proxyTimeout: LONG_RUNNING_PROXY_MS,
  },
  // /api/v1/... 等子路径也需要代理，dev 模式下 Vite 只精确匹配 /api
  "^/api/v1": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
    timeout: LONG_RUNNING_PROXY_MS,
    proxyTimeout: LONG_RUNNING_PROXY_MS,
    rewrite: (path: string) => path,
  },
} as const;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { ...apiProxy },
  },
  /** `vite preview` 默认不转发 /api，会把 /api/* 当成 SPA 返回 index.html（JSON 解析报 Unexpected token '<'） */
  preview: {
    proxy: { ...apiProxy, "/api/v1": apiProxy["^/api/v1"] },
  },
});
