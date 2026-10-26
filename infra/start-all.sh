#!/bin/sh
set -eu

cd /app/api
uv run uvicorn research_agent.main:app --host 127.0.0.1 --port 8000 &

export API_INTERNAL_URL="${API_INTERNAL_URL:-http://127.0.0.1:8000}"
export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
export NODE_ENV="${NODE_ENV:-production}"

cd /app/web
exec node server.mjs
