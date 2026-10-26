# Prefer repo-root Dockerfile (Express + API). Kept for web-only local builds.
FROM node:22-slim AS build
WORKDIR /app
RUN corepack enable
COPY apps/web /app
RUN pnpm install --frozen-lockfile && pnpm build && pnpm prune --prod

FROM node:22-slim
WORKDIR /app
RUN useradd --create-home appuser
COPY --from=build /app ./
USER appuser
EXPOSE 3000
ENV PORT=3000 \
    NODE_ENV=production \
    API_BASE_URL=http://api:8000 \
    API_INTERNAL_URL=http://api:8000
CMD ["node", "server.mjs"]
