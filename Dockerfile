# Single Render Web Service: Express serves Next.js and proxies /v1 to FastAPI in-process.
FROM ghcr.io/astral-sh/uv:0.9.26 AS uv

FROM python:3.12-slim-bookworm AS api-deps
COPY --from=uv /uv /uvx /bin/
WORKDIR /api
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
COPY apps/api/src ./src
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./
RUN uv sync --frozen --no-dev

FROM node:22-bookworm-slim AS web-build
WORKDIR /web
RUN corepack enable
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build && pnpm prune --prod

FROM python:3.12-slim-bookworm
COPY --from=uv /uv /uvx /bin/
COPY --from=node:22-bookworm-slim /usr/local /usr/local
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home appuser \
 && node --version

WORKDIR /app
COPY --from=api-deps /api /app/api
COPY --from=web-build /web /app/web
COPY infra/start-all.sh /app/start-all.sh
RUN chmod +x /app/start-all.sh && chown -R appuser:appuser /app

USER appuser
ENV PORT=3000 \
    NODE_ENV=production \
    API_INTERNAL_URL=http://127.0.0.1:8000 \
    API_BASE_URL=http://127.0.0.1:8000 \
    NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
HEALTHCHECK CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','3000'))"
CMD ["/app/start-all.sh"]
