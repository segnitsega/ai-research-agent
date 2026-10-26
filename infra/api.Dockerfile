# Prefer repo-root Dockerfile (Express + API). Kept for API-only local builds.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
COPY apps/api/src ./src
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./
RUN rm -rf .venv && uv sync --frozen --no-dev --no-editable \
 && useradd --create-home appuser \
 && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENV PORT=8000
HEALTHCHECK CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8000'))"
CMD ["sh", "-c", "uv run uvicorn research_agent.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
