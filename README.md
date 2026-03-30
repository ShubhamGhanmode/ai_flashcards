# Flashcard Learning Assistant

AI-powered flashcard deck generator with optional RAG, schema-first JSON outputs, a live generation stream, and an animated card-stack UI. Built with FastAPI (backend) and Next.js (frontend).

## Status
Phase 1 complete (audited 2026-01-24). Phase 2 and Phase 3 implemented (audited 2026-02-13). Phase 4 implemented and verified on 2026-02-15. Phase 5 and Phase 6 implementation guides were added on 2026-03-08; implementation has not started yet.

## Quick start (development)
```bash
docker compose -f docker-compose.dev.yml up
```

## Docker policy
Docker is optional. The project supports both:
- Docker-based runs (`docker compose ...`)
- Native local runs (no Docker), as long as PostgreSQL is available locally

## Manual start (backend + frontend)
Use this when you want to run app code locally (without backend/frontend Docker containers) and validate changes quickly.

### 1. Start local infrastructure (Postgres + Redis)
```bash
docker compose -f docker-compose.dev.yml up -d postgres redis
```

### 2. Start backend (FastAPI)
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Required environment variables are in `.env.example` (`OPENAI_API_KEY`, `OPENAI_MODEL`, `DATABASE_URL`, `REDIS_URL`, `RATE_LIMIT_REQUESTS_PER_HOUR`, `RATE_LIMIT_DECKS_PER_DAY`, `CIRCUIT_BREAKER_FAILURE_THRESHOLD`, `CIRCUIT_BREAKER_FAILURE_WINDOW_SECONDS`, `CIRCUIT_BREAKER_OPEN_DURATION_SECONDS`).
Use `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/flashcards`.
If your local Postgres uses a different password, set `DB_PASSWORD=<your_password>` in `.env`.
When any `DB_*` variable is set, backend/Alembic build the DB URL from `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`.

### 3. Start frontend (Next.js)
Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```

If needed, set API URL before starting frontend:
```bash
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
```

### 4. Verify app is running
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Full local run (no Docker at all)
Use this mode if you do not want Docker running for any service.

### 1. Ensure local services are installed and running
- PostgreSQL 16+ running on `localhost:5432`
- Redis 7+ running on `localhost:6379` (recommended for upcoming phases)

### 2. Configure environment
Set:
- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/flashcards`
- `REDIS_URL=redis://localhost:6379/0`
- `OPENAI_API_KEY=<your_key>`
- `OPENAI_MODEL=gpt-5-nano`
- `RATE_LIMIT_REQUESTS_PER_HOUR=30`
- `RATE_LIMIT_DECKS_PER_DAY=10`
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD=5`
- `CIRCUIT_BREAKER_FAILURE_WINDOW_SECONDS=60`
- `CIRCUIT_BREAKER_OPEN_DURATION_SECONDS=30`
- If needed for local auth: `DB_PASSWORD=<your_postgres_password>`

Example database creation (once):
```bash
psql -U postgres -c "CREATE DATABASE flashcards;"
```

### 3. Start backend and frontend natively
Backend terminal:
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend terminal:
```bash
cd frontend
npm install
npm run dev
```

### 4. Verify
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## LLM Model And Provider Configuration

### Current implementation
- LLM provider is currently wired to **OpenAI** via LangChain `ChatOpenAI`.
- Wiring lives in:
  - `backend/app/services/llm_client.py`
  - `backend/app/services/example_generator.py`

### Change model within OpenAI (no code change)
1. Set `OPENAI_MODEL` in `.env`:
```env
OPENAI_MODEL=gpt-5-nano
```
2. Keep `OPENAI_API_KEY` set.
3. Restart backend after changes.

Native run:
```bash
cd backend && .venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docker run:
- Ensure backend container receives `OPENAI_MODEL` (for example by adding `- OPENAI_MODEL=${OPENAI_MODEL}` under `backend.environment` in Compose).
- Rebuild/restart:
```bash
docker compose -f docker-compose.dev.yml up --build
```

Verification:
- Call `POST /v1/deck/generate` and confirm `generation_metadata.model` in response matches your configured model.

### Switch LLM provider (example: OpenAI -> Anthropic)
Provider switching is **not** environment-only in the current codebase. It requires code updates.

Recommended steps:
1. Add Anthropic LangChain package in backend dependencies (for example `langchain-anthropic` in `backend/pyproject.toml`).
2. Add provider env variables (example):
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```
3. Update provider wiring in:
  - `backend/app/services/llm_client.py`
  - `backend/app/services/example_generator.py`
4. Implement provider selection logic (openai vs anthropic) and ensure schema-output flow still works with `with_structured_output(..., include_raw=True)`.
5. Pass provider env vars to Docker backend service if running via Compose.
6. Re-run tests:
```bash
cd backend && .venv\Scripts\python.exe -m pytest -v
cd frontend && npm test
```

Notes:
- Error and metadata contracts should stay unchanged (`docs/ERRORS.md`, `docs/schemas/*.json`).
- If you add provider-level options (timeouts/retries/model names), keep defaults explicit and document them.

## Database migrations
Run migrations before using deck endpoints against a fresh database:
```bash
cd backend && .venv\Scripts\alembic.exe upgrade head
```

## Tests
```bash
cd backend && .venv\Scripts\python.exe -m pytest -v
cd frontend && npm test
```

## Key docs
- `PLAN.md` (architecture and phases)
- `PHASE1.md` (repo setup and foundations)
- `PHASE2.md` (schema-first deck generation)
- `PHASE3.md` (gated example generation, caching, and UI integration)
- `PHASE4.md` (token estimation, cost tracking, rate limiting, circuit breaker)
- `PHASE5.md` (PDF upload, ingestion, Chroma retrieval, and RAG deck generation)
- `PHASE6.md` (retrieval metrics, RAG transparency, and optional debug surfaces)
- `docs/schemas/` (JSON schema definitions)

## API conventions
- Versioned endpoints use `/v1/*`
- Root health check: `GET /health` (infra)
- Versioned health: `GET /v1/health`
- Responses include `X-Request-ID`

## Deck generation UX
- Home page deck generation now uses `POST /v1/deck/generate/stream` to stream `status`, `heartbeat`, `complete`, and `error` events over `text/event-stream`.
- The frontend uses those events to drive a full-screen generation overlay instead of leaving the user on a static button spinner.
- On stream completion, the deck payload is cached in session storage so `/deck/[deckId]` can render immediately without a second blocking fetch.
- The deck page now uses a stacked-card presentation: flip the active card to reveal notes, then move it to the back of the pack to expose the next concept.
- The builder only exposes controls that currently change real runtime behavior: topic, difficulty, and card count.

## Phase 3 API
- `POST /v1/card/{card_id}/example`
- Request body (optional): `{ style?, length?, constraints? }`
- First generate call returns `201`; identical cached call returns `200`
- Timeout failures return `504` with `error.code = "LLM_TIMEOUT"`
- Error envelope follows `docs/ERRORS.md` with top-level `error` object

## Phase 4 API and controls
- `POST /v1/deck/estimate`
- Request body: `{ topic, difficulty_level?, max_concepts?, scope? }`
- Response includes `estimated_tokens`, `estimated_cost_usd`, `estimated_cost_cents`, and `estimated_seconds`
- Estimate endpoint is compute-only and does not require `OPENAI_API_KEY`
- `POST /v1/deck/generate/stream` accepts the same request body as `POST /v1/deck/generate` and streams lifecycle events plus the completed deck payload
- Hourly mutating-request rate limit returns `429 RATE_LIMITED` with `Retry-After`
- Daily deck-generation quota returns `429 QUOTA_EXCEEDED` for both `POST /v1/deck/generate` and `POST /v1/deck/generate/stream`
- Circuit breaker protection returns `503 CIRCUIT_BREAKER_OPEN` during provider recovery windows
- Deck/example generations now persist telemetry server-side (`tokens_used`, `api_cost_cents`, `generation_time_ms`)

## Frontend caching
- TanStack Query is configured app-wide in `frontend/src/app/providers.tsx`
- Example query key: `["card-example", cardId, style, length, constraintsKey]`
- Example cache policy: `staleTime=24h`, `gcTime=24h`
