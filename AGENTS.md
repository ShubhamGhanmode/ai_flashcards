# AGENTS.md

## Overview

Flashcard Learning Assistant: An AI-powered flashcard deck generator with optional RAG (Retrieval-Augmented Generation), schema-first JSON outputs, and a swipeable flashcard UI. Built with FastAPI + Next.js.

**Current Phase**: Phase 1 Complete ✅ (audited 2026-01-24) | Phase 2 Ready

---

## Project Structure

```
ai_flashcards/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # API routes (routes_health.py)
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
- 2026-01-24: Improved the frontend deck builder UX with topic suggestions, deck settings (card count + toggles), sticky preview panels, and a live deck summary while preserving the existing color scheme.
