# Research Agent

Multi-agent research app. Gemini plans, searches, reads, critiques, and writes a cited report. The Next.js app shows the live run.

## Run

Set `GOOGLE_API_KEY` or `GEMINI_API_KEY`, and an `API_KEY`, in `.env`.

```bash
cp .env.example .env
make setup
make up
make migrate
make dev
```

Open http://localhost:3000. The API is on http://localhost:8000.

`SEARCH_PROVIDER=fake` uses a local sample page so the first run only needs the Gemini key. Set `SEARCH_PROVIDER=tavily` and `TAVILY_API_KEY` for live web search.

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
