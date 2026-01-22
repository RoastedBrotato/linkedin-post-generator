# Web UI Plan (Astro + FastAPI)

## Goals
- Let a user enter keywords/phrases and choose sources to build a tailored research feed.
- Provide a trends browser with filters, previews, and history of past runs.
- Keep post generation and LinkedIn publishing as secondary actions from a selected trend.

## Non-goals (v1)
- Multi-user auth, hosted deployment, or OAuth flows in the UI.
- Reddit as a source (disabled).

## Architecture
- **Backend**: FastAPI REST API over existing services + database.
- **Frontend**: Astro app with client-side islands for forms, results, and actions.
- **Storage**: Extend SQLite schema to persist query runs and their results.
- **Processing**: In-process background jobs for fetch/generate; API exposes job status.

## Data Model Changes (SQLite)
Add tables to support history and per-run results:
- `query_runs`
  - `id` (PK), `keywords_raw` (TEXT), `phrases_raw` (TEXT),
    `sources_json` (TEXT), `options_json` (TEXT),
    `status` (TEXT: queued|running|complete|failed),
    `created_at` (TIMESTAMP), `completed_at` (TIMESTAMP)
- `query_run_trends`
  - `id` (PK), `query_run_id` (FK), `trend_id` (FK),
    `match_score` (REAL), `matched_terms_json` (TEXT)

Notes:
- Keep existing `trends` table as the canonical store for fetched items.
- `sources_json` captures per-source options (e.g., RSS feed list, GitHub timeframe).

## Keyword/Phrase Matching
Input rules:
- Support phrases with quotes: `"vector database"` is a single phrase.
- Support plain keywords: `llm agents`.
- Normalize: lowercase, trim, collapse whitespace.
Matching:
- Match against `title` + `description` (existing trend fields).
- A trend is included if it matches **any phrase** or **any keyword**.
- `match_score` = base relevance + bonus:
  - +0.2 per matched phrase, +0.05 per matched keyword (cap at 1.0)
- Store `matched_terms_json` for UI highlighting.

## Backend API (FastAPI)
Sources:
- `GET /api/sources`
  - Returns available sources: Hacker News, RSS, GitHub.
  - Includes options schema (e.g., RSS feeds list, GitHub timeframe).

Query Runs:
- `POST /api/query-runs`
  - Body: `{ keywords: string, phrases: string[], sources: string[], options: {...} }`
  - Creates a run, starts background fetch, returns `{ id, status }`.
- `GET /api/query-runs`
  - Lists recent runs for history.
- `GET /api/query-runs/{id}`
  - Returns run metadata and status.
- `GET /api/query-runs/{id}/results`
  - Returns ordered trends with match metadata.

Trends:
- `GET /api/trends/{id}`
  - Returns trend details and source metadata.

Posts (secondary actions):
- `POST /api/trends/{id}/generate-post`
  - Generates a draft post for the trend.
- `GET /api/posts?status=pending|approved|published`
  - List posts for history.
- `POST /api/posts/{id}`
  - Update edited content.
- `POST /api/posts/{id}/publish`
  - Publish to LinkedIn using existing `.env` tokens.

## Frontend (Astro)
Routes:
- `/` (Query Builder)
  - Keywords input, phrases input, source toggles.
  - Optional RSS feed selection, GitHub timeframe.
- `/runs/:id` (Results)
  - Trend list with filters (source, recency, score).
  - Trend detail panel with match highlights.
- `/history`
  - List past query runs with summary counts.
- `/trend/:id`
  - Trend detail + actions (generate/edit/publish).

Client-side islands:
- Query form submission + status polling.
- Results list + filters.
- Post editor + publish action.

## Background Jobs
Simplest v1: in-process queue (threaded executor).
- `query_run` job: fetch sources → store trends → match keywords → link results.
- `generate_post` job: use existing generator pipeline.
Expose job status via `GET /api/query-runs/{id}`.

## Milestones
M1: API scaffolding + schema changes for query runs.
M2: Implement query run execution and matching logic.
M3: Astro UI for query builder + results.
M4: History view and trend detail panel.
M5: Post generation/edit/publish integration.
M6: Tests + docs.

## Testing
- Unit tests for matching logic and query run orchestration.
- API contract tests for `/api/query-runs` and `/api/query-runs/{id}/results`.
- Frontend smoke tests for query, results, and history pages.
