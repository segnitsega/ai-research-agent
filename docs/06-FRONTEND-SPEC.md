# 06. Frontend Specification (Next.js)

Next.js (latest stable 16.x at time of writing; verify with `npm view next version`), App Router, TypeScript strict, Tailwind CSS, shadcn/ui, TanStack Query, Zod. Package manager: pnpm.

Next.js APIs changed across 14, 15 and 16 (async request APIs such as `await params`, caching model, `middleware.ts` renamed to `proxy.ts` in 16). **Check the official docs for the installed version before writing routing, caching, or proxy code** (see `AGENTS.md` §5).

## 1. Goals

- Make agent work visible: live timeline, plan, sources, findings, cost.
- Make citations auditable: one click from claim to quote to source.
- Be fast, accessible, responsive, and calm. Research tools should feel like a clean reading and working environment, not a chat toy.

## 2. Architecture

```
Browser ──▶ Next.js pages (Server + Client Components)
        ──▶ Next.js route handlers /api/*   (BFF)  ──▶ FastAPI /v1/*   (X-API-Key added server-side)
```

- **BFF route handlers** in `src/app/api/**/route.ts` forward to `API_BASE_URL` and attach `API_KEY`. They pass through status codes and problem+json bodies.
- **SSE proxy:** `src/app/api/runs/[id]/events/route.ts` streams the upstream response body through unchanged, forwarding `Last-Event-ID`, with `export const dynamic = "force-dynamic"` and runtime Node.js. It must not buffer. Abort the upstream request when the client disconnects.
- Server Components fetch lists and details directly from the API using a server-only client (`src/lib/api/server.ts`, `import "server-only"`).
- Client Components use the browser client (`src/lib/api/client.ts`) that talks to `/api/*` (the BFF).
- Environment: `API_BASE_URL`, `API_KEY` (server-only). **No `NEXT_PUBLIC_` secrets.**

## 3. Types and API client

- `make types` runs `openapi-typescript` against `apps/api/openapi.json` and writes `src/types/api.d.ts`. Event types come from the discriminated union in the OpenAPI schema.
- Thin typed client (`openapi-fetch` or hand-rolled `fetch` wrappers using the generated types). Zod schemas parse **SSE event payloads** at runtime before they reach the reducer (unknown events are ignored and logged in development).

## 4. Routes

| Route | Type | Content |
|---|---|---|
| `/` | Server + client form | New research form, 5 most recent runs |
| `/runs` | Server | History table with filters (status), cursor pagination |
| `/runs/[id]` | Server shell + client live view | The main screen (§5) |
| `/memory` | Server + client | Memory manager (§7) |
| `/settings` | Client | Local UI prefs (theme, default depth, default memory toggle); read-only server config |
| `/api/*` | Route handlers | BFF proxy |

## 5. Run page `/runs/[id]`

Layout (desktop, three regions; collapses to tabs on mobile):

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Question title · status badge · depth · [Cancel]/[Export .md]  Cost $0.23 │
├───────────────┬──────────────────────────────────────┬────────────────────┤
│ Activity      │ Main                                 │ Inspector          │
│ timeline      │  Tabs: Report | Plan | Sources |     │  Selected citation │
│ (grouped by   │        Findings                      │  or source detail  │
│  agent and    │                                      │  evidence quote    │
│  iteration)   │                                      │  link, fetch date  │
│               │                                      │  Budget meters     │
└───────────────┴──────────────────────────────────────┴────────────────────┘
```

### Activity timeline
- Event rows with icon, agent name, one-line summary, relative time. Grouped by iteration with collapsible groups. Auto-scroll follows the newest event unless the user scrolls up (then show a "Jump to latest" button).
- Rows: plan created, searching "query", found N sources, fetched domain (cache badge), finding extracted/rejected (collapsed counts by default, expandable), critic verdict with gaps, report started/completed, memory updated.
- Container has `role="log"` and `aria-live="polite"`; announcements are throttled (key milestones only).

### Main tabs
- **Report** (default once available): title, executive summary, sections, limitations. Citation markers `[n]` render as buttons; click or focus opens the Inspector with the quote and source. Also shows a "Copy as Markdown" and "Download .md" action. While running, shows a progress view: current phase stepper (Recall, Plan, Search, Read, Critique, Write, Memorize) with sub-progress counts.
- **Plan:** objective, sub-questions with priority chips and live coverage state (none/partial/good from the latest Critic review), success criteria.
- **Sources:** table (title, domain, sub-question, status, cache, quality, #findings), sort and filter; row click opens the Inspector.
- **Findings:** grouped by sub-question; each shows claim, quote (with highlight), confidence bar, stance, status; rejected findings behind a "Show rejected" toggle; a "Flag as wrong" action sends feedback.

### Inspector
- Citation selected: number, claim(s), verbatim quote, source title, domain, published/fetched date, "Open source" link (new tab, `rel="noopener noreferrer"`), "from memory" badge if applicable.
- Budget meters: cost, fetches, tokens, time versus limits with color thresholds (not color alone: also numbers and icons).

### States
Loading skeletons; empty states; failed run banner with sanitized message and "Retry as new run" (clones the request); cancelled banner; "Connection lost, reconnecting" indicator with automatic retry.

## 6. Stream handling (`useRunStream`)

Design for determinism and testability:

```ts
type RunViewState = {
  status, phase, iteration, plan?, review?, report?,
  sources: Record<id, SourceView>, findings: Record<id, FindingView>,
  timeline: TimelineItem[], usage?, budgetWarnings: [], lastSeq: number
}
function reduce(state: RunViewState, event: RunEvent): RunViewState   // pure, idempotent on seq
```

- On mount: fetch `RunDetail` (for finished runs, the page can render directly from detail plus a one-time events replay).
- Open `EventSource("/api/runs/{id}/events")`. The browser sends `Last-Event-ID` automatically on reconnect. The reducer ignores any event with `seq <= lastSeq` (idempotent).
- Close the stream on terminal events and on unmount. Cap reconnect attempts with backoff; after a cap show a manual "Reconnect".
- Batch updates: buffer events and flush with `requestAnimationFrame` (or at most every 100 ms) to avoid render storms during bursts.
- The same reducer builds state from a full replay, so a reload mid-run and an uninterrupted viewer end in identical state (acceptance test).
- Cache finished-run data with TanStack Query; invalidate the run list when a run starts or ends.

## 7. Memory page `/memory`

- Tabs: Preferences, Facts, Episodes. List items with content, importance, origin run (link), created/updated.
- Actions: edit (inline), delete (confirm), add preference/fact, search box (semantic), "Forget everything" (type-to-confirm dialog).
- A short explainer: what memory is, where it is used, how to disable per run.

## 8. New research form (`/`)

- Textarea (autofocus, 8 to 2000 chars with live counter), depth segmented control (Quick/Standard/Deep with estimated time and cost from `/v1/config`), "Use memory" switch, collapsible "Advanced budget" (max cost, max fetches, max iterations, validated against server maximums).
- Submit calls `POST /api/runs`, then `router.push('/runs/{id}')`. Show field-level errors from problem+json.
- Example questions as clickable chips.

## 9. Components (suggested structure)

```
src/components/
  ui/                     # shadcn primitives
  research/  QuestionForm, DepthSelector, RunHeader, StatusBadge, PhaseStepper,
             ActivityTimeline, TimelineItem, PlanView, SourcesTable, FindingsList,
             FindingCard, ReportView, CitationButton, Inspector, BudgetMeters
  memory/    MemoryList, MemoryItemRow, MemoryForm, ForgetAllDialog
  layout/    AppShell, Nav, ThemeToggle
src/lib/
  api/ (client.ts, server.ts, errors.ts)
  stream/ (useRunStream.ts, reducer.ts, schemas.ts)
  markdown/ (renderReport.tsx with sanitize and citation plugin)
  format.ts  cn.ts
```

## 10. Visual design guidance

- Calm, content-first. A readable report column (max about 72ch), generous spacing, clear hierarchy.
- Light and dark themes via CSS variables, respecting `prefers-color-scheme` with a manual toggle.
- One accent color; status colors (running, success, warning, error) with sufficient contrast and never color-only meaning.
- Distinct agent identities in the timeline (icon plus label, not only hue).
- Motion: subtle (new event fade-in), respect `prefers-reduced-motion`.
- If the coding agent has the `frontend-design` skill, use it for the visual pass after functionality works; avoid generic templated looks.

## 11. Accessibility requirements

- Landmarks, headings in order, labeled form controls, visible focus rings, keyboard access for all actions including citation buttons and the Inspector (Escape closes).
- Streaming status in an `aria-live="polite"` region; no focus stealing on updates.
- Contrast WCAG AA; touch targets at least 44px on mobile.
- Automated checks with `axe` in Playwright on the main pages.

## 12. Performance

- Server Components for lists and the initial run shell; client JS only for the live view and forms.
- Virtualize long lists (findings, timeline) above ~200 rows.
- Code-split the Markdown renderer; avoid heavy charting libraries (use simple CSS meters).

## 13. Frontend tests

| Level | Tool | What |
|---|---|---|
| Unit | Vitest | `reduce()` per event type, idempotency, replay equivalence, Zod schemas, markdown citation plugin, formatters |
| Component | Vitest + Testing Library | QuestionForm validation, CitationButton to Inspector, FindingCard states, Memory dialogs |
| E2E | Playwright | Start run against a **fake backend** (a small SSE server replaying a recorded event file), verify live updates, reconnect with `Last-Event-ID`, report with citations, cancel, memory CRUD, axe checks |
| Build | `next build` | Passes; grep the build output to confirm `API_KEY` is absent |

Keep a recorded event fixture (`tests/fixtures/run-standard.ndjson`) generated from a real backend run once the API exists; use it for reducer and E2E tests.
