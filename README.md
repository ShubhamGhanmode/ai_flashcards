# Flashcard Learning Assistant

AI-powered flashcard deck generator with optional RAG, schema-first JSON outputs, and a swipeable UI. Built with FastAPI (backend) and Next.js (frontend).

## Status
Phase 1 complete (audited 2026-01-24). Phase 2 ready.

## Quick start (development)
```bash
docker compose -f docker-compose.dev.yml up
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
- `docs/schemas/` (JSON schema definitions)

## API conventions
- Versioned endpoints use `/v1/*`
- Root health check: `GET /health` (infra)
- Versioned health: `GET /v1/health`
- Responses include `X-Request-ID`
