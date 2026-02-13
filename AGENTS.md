# AGENTS.md
This is a guide for agentic ai tasks. Improve the instructions in this file so as to improve the quality and consistency of project code generated.

## Overview

Flashcard Learning Assistant: An AI-powered flashcard deck generator with optional RAG (Retrieval-Augmented Generation), schema-first JSON outputs, and a swipeable flashcard UI. Built with FastAPI + Next.js.

**Current Phase**: Phase 1 Complete ✅ (audited 2026-01-24) | Phase 2 Ready

---

## Project Structure

```
ai_flashcards/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # API routes (routes_health.py, v1/routes_health.py)
│   │   ├── db/              # Database models & Alembic migrations
│   │   ├── middleware/      # Request ID middleware
│   │   ├── prompts/         # LLM prompt templates
│   │   ├── schemas/         # Pydantic models
│   │   ├── services/        # Business logic
│   │   └── main.py          # FastAPI app entry point
│   ├── tests/               # pytest tests
│   ├── alembic.ini          # Migration config
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                # Next.js application
│   ├── src/app/             # App Router pages
│   ├── __tests__/           # Jest tests
│   ├── Dockerfile
│   └── next.config.ts
├── docs/                    # Documentation & schemas
│   ├── schemas/             # JSON Schema definitions
│   ├── ERRORS.md            # Error code catalog
│   ├── DATA_RETENTION.md    # GDPR/CCPA policy
│   └── RAG_SAFETY.md        # RAG safety checklist
├── docker-compose.yml       # Production compose
├── docker-compose.dev.yml   # Development with hot reload
├── .pre-commit-config.yaml  # Quality hooks
└── .env.example             # Environment template
```

---

## Key Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Project entry point and quick start |
| `PLAN.md` | Master plan: architecture, phases, API contracts |
| `PHASE1.md` | Repo setup, Docker, testing frameworks |
| `PHASE2.md` | Schema-first deck generation API |
| `PHASE3.md` | Example generation (gated), caching, and UI integration guide |
| `docs/schemas/*.json` | JSON Schema definitions for API responses |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Alembic |
| Frontend | Next.js 16+, React 19, TypeScript, Tailwind CSS (v4) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| LLM | OpenAI API via LangChain |
| RAG | LangChain document loaders, ChromaDB |
| Quality | Ruff, mypy, Prettier, pytest, Jest |

---

## Development Commands

```bash
# Start all services (development)
docker compose -f docker-compose.dev.yml up

# Start all services (production build)
docker compose up --build

# Backend tests
cd backend && .venv\Scripts\python.exe -m pytest -v

# Frontend tests
cd frontend && npm test

# Install pre-commit hooks
pip install pre-commit && pre-commit install
```

---

## API Conventions

- **Versioning**: All endpoints use `/v1/` prefix
- **Request Tracing**: All responses include `X-Request-ID` header
- **Schema Version**: Response payloads include `schema_version` field
- **Health Check**: `GET /health` (root) and `GET /v1/health` (versioned) return `{"status":"ok",...}`

---

## Workflow Rules

1. **Schema-first**: Define JSON schemas before implementing endpoints
2. **LLM Validation**: Validate all LLM outputs; attempt one repair pass before failing
3. **Documentation Sync**: Update `PLAN.md` when scope/phases/interfaces change.
4. **Schema Sync**: Keep `docs/schemas/` in sync with API changes
5. **Structured Logging**: Use structlog with request_id context

---

## Notes
- `.gitignore` includes Python/Node caches, coverage artifacts, and common debug logs.

## Recent Updates
- 2026-02-13: Completed the Phase 2 remediation pass from `PHASE2.md`: added one-pass LLM schema repair with structured failure details (`SCHEMA_VALIDATION_FAILED`), enriched deck route error envelopes with optional `details`/`recovery_action`, normalized request text inputs (`topic`, `scope`) server-side, enforced URI validation for deck source URLs, and added `backend/app/schemas/example.py` plus exports for PLAN deck/example schema alignment. Verification: backend `58/58` tests passed and frontend `4/4` tests passed.
- 2026-02-13: Audited Phase 2 implementation against `PHASE2.md` and `PLAN.md`; updated Phase 2 checklist status with an implementation score of **8/10**. Confirmed passing test suites (`backend`: 43/43, `frontend`: 4/4) and documented remaining gaps: missing LLM schema-repair pass, incomplete error payload enrichment (`details`/`recovery_action`), missing server-side input sanitization, and missing `backend/app/schemas/example.py` for full PLAN Phase 2 alignment.
- 2026-02-12: Reconfirmed Phase 2 against `PHASE2.md` and aligned gaps: added initial Alembic migration for `decks`/`cards`, normalized request validation failures to `400 INVALID_INPUT` with top-level `error` payload/details, and excluded `None` fields from `/v1/deck` responses to keep API output aligned with `docs/schemas/deck.schema.json`.
- 2026-02-12: Completed a Phase 2 hardening pass: fixed frontend Jest App Router mocking, repaired encoded UI text in deck/card components, moved font loading to `next/font/google`, improved API client error normalization for FastAPI validation payloads, and resolved backend Ruff+mypy issues (typed DB session helpers, timezone alias updates, dependency annotations, migration import order, and `scope` persistence on deck writes).
- 2026-02-12: Added `PHASE3.md` with a decision-complete implementation guide for gated example generation (`POST /v1/card/{card_id}/example`), cache-first immutable persistence, TanStack Query integration, and explicit Phase 2 readiness gates.
- 2026-02-12: Added versioned health endpoint wiring (`GET /v1/health`) with backend test coverage, removed deprecated Compose `version` keys, aligned Phase docs with audited completion status, and clarified Phase 2 theme/UI mapping guidance.
- 2026-01-24: Improved the frontend deck builder UX with topic suggestions, deck settings (card count + toggles), sticky preview panels, and a live deck summary while preserving the existing color scheme.
