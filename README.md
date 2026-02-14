# Flashcard Learning Assistant

AI-powered flashcard deck generator with optional RAG, schema-first JSON outputs, and a swipeable UI. Built with FastAPI (backend) and Next.js (frontend).

## Status
Phase 1 complete (audited 2026-01-24). Phase 2 and Phase 3 implemented (audited 2026-02-13). Phase 4 ready (guide created 2026-02-14).

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

Required environment variables are in `.env.example` (`OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL`).
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
- `docs/schemas/` (JSON schema definitions)

## API conventions
- Versioned endpoints use `/v1/*`
- Root health check: `GET /health` (infra)
- Versioned health: `GET /v1/health`
- Responses include `X-Request-ID`

## Phase 3 API
- `POST /v1/card/{card_id}/example`
- Request body (optional): `{ style?, length?, constraints? }`
- First generate call returns `201`; identical cached call returns `200`
- Timeout failures return `504` with `error.code = "LLM_TIMEOUT"`
- Error envelope follows `docs/ERRORS.md` with top-level `error` object

## Frontend caching
- TanStack Query is configured app-wide in `frontend/src/app/providers.tsx`
- Example query key: `["card-example", cardId, style, length, constraintsKey]`
- Example cache policy: `staleTime=24h`, `gcTime=24h`
