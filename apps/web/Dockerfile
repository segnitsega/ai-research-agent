# Prefer the repo-root Dockerfile for Render (API + UI together).
# This file is for web-only local experiments with Root Directory = apps/web.
FROM node:22-slim
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY . .
RUN pnpm install --frozen-lockfile && pnpm build && pnpm prune --prod
ENV PORT=3000 \
    NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    API_BASE_URL=http://127.0.0.1:8000 \
    API_INTERNAL_URL=http://127.0.0.1:8000
EXPOSE 3000
CMD ["node", "server.mjs"]
