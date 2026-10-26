import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import next from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 3000);
const apiOrigin = process.env.API_INTERNAL_URL || process.env.API_BASE_URL || "http://127.0.0.1:8000";
const dev = process.env.NODE_ENV !== "production";

const app = next({ dev, dir: __dirname });
const handle = app.getRequestHandler();

await app.prepare();

const server = express();

server.use(
  createProxyMiddleware({
    target: apiOrigin,
    changeOrigin: true,
    xfwd: true,
    pathFilter: (pathname) =>
      pathname === "/healthz" || pathname === "/readyz" || pathname.startsWith("/v1"),
  }),
);

server.use((req, res) => {
  void handle(req, res);
});

server.listen(port, "0.0.0.0", () => {
  console.log(`express listening on :${port} (next ui + /api, api proxy → ${apiOrigin})`);
});
