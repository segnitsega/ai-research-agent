#!/bin/sh
set -eu

export API_INTERNAL_URL="${API_INTERNAL_URL:-http://127.0.0.1:8000}"
export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
export NODE_ENV="${NODE_ENV:-production}"

cd /app/api

echo "running database migrations..."
uv run alembic upgrade head

echo "starting FastAPI on 127.0.0.1:8000..."
uv run uvicorn research_agent.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

i=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" 2>/dev/null; do
  i=$((i + 1))
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "FastAPI exited before becoming ready" >&2
    wait "$API_PID" || true
    exit 1
  fi
  if [ "$i" -gt 60 ]; then
    echo "FastAPI did not become ready within 60s" >&2
    kill "$API_PID" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done
echo "FastAPI is ready"

cd /app/web
echo "starting Express on 0.0.0.0:${PORT:-3000}..."
node server.mjs &
WEB_PID=$!

shutdown() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap shutdown INT TERM

while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  sleep 2
done

echo "a process exited; shutting down" >&2
shutdown
wait || true
exit 1
