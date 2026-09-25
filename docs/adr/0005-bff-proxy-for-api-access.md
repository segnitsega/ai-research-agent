# ADR-0005: Next.js BFF proxy between browser and API

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
The FastAPI service is protected by an API key. A browser calling it directly would expose that key.

## Decision
Browser calls Next.js route handlers (`/api/*`), which call FastAPI server-side and attach `X-API-Key`. The SSE route is proxied as a non-buffered stream.

## Rationale
- Keeps secrets server-side with no `NEXT_PUBLIC_` exposure.
- One origin for the browser; no CORS complexity.
- A natural place for future real auth (session cookies), request shaping, and rate limiting.

## Consequences
- Long-lived SSE connections pass through the Next.js server, so it must stream without buffering and abort upstream on client disconnect.
- On serverless hosts with function duration limits (for example Vercel), proxied SSE may be cut off. Mitigation (Phase 12 option): `POST /v1/runs/{id}/stream-token` returns a short-lived signed token that lets the browser open the SSE connection directly to the API for that one run. Reconnection with `Last-Event-ID` makes brief cut-offs harmless either way.
- Self-hosted Docker deployment (the default) has no such limit.
