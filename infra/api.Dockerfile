FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
WORKDIR /app
COPY apps/api /app
RUN uv sync --frozen --no-dev
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["uv", "run", "uvicorn", "research_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
