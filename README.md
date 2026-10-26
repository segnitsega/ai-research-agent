# Research Agent

Multi-agent research app. Gemini plans, searches, reads, critiques, and writes a cited report. The Next.js app shows the live run.

## Run

Set `XAI_API_KEY` (for Grok), and an `API_KEY`, in `.env`. Gemini keys are optional if you switch models back to `google:…`.

```bash
cp .env.example .env
make setup
make up
make migrate
make dev
```

Open http://localhost:3000. The API is on http://localhost:8000.

`SEARCH_PROVIDER=duckduckgo` uses live DuckDuckGo results with no search API key. Use `fake` for a local sample page (Gemini key only), or `tavily` with `TAVILY_API_KEY` for Tavily.

## Check

```bash
curl -s http://localhost:8000/healthz
make test
make eval
```

From `apps/api`, after Postgres is up:

```bash
uv run research-agent run "Who develops the Gemini models?" --depth quick
```
