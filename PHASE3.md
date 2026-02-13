# Phase 3: Example Generation (Gated)

## Goal
Implement a gated `POST /v1/card/{card_id}/example` flow that generates schema-valid concept examples only when allowed by `example_possible`, persists them, and returns stable cached results for repeated identical requests.

By the end of this phase, users can open a generated deck, click **Show example** for eligible cards, and see deterministic examples with loading/error handling.

---

## Status

Planned (authored 2026-02-12). Not started.

---

## Prerequisites

Before starting Phase 3, ensure:

- [ ] You have reviewed `PLAN.md` (Phase 3 section) and `docs/schemas/example.schema.json`
- [ ] You have reviewed `docs/ERRORS.md` for the standardized error envelope
- [ ] Docker Compose services for backend/frontend/postgres/redis run locally
- [ ] OpenAI API key is configured in `.env`

---

## Phase 2 Readiness Gate

Phase 3 depends on Phase 2 runtime behavior. Do not start implementation until all checks below pass.

- [ ] `POST /v1/deck/generate` exists and returns:
  - `concepts[].card_id`
  - `concepts[].example_possible`
- [ ] `GET /v1/deck/{deck_id}` exists and returns a persisted deck payload
- [ ] Database contains `decks` and `cards` tables populated from deck generation
- [ ] Frontend renders deck/card data from API and can reference specific `card_id`
- [ ] Phase 2 backend and frontend tests are green

### Readiness Verification Commands

```bash
# Backend tests
cd backend && .venv\Scripts\python.exe -m pytest -v

# Frontend tests
cd frontend && npm test

# Deck generate smoke call (requires Phase 2 implementation)
curl -X POST http://localhost:8000/v1/deck/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Binary Search Trees", "difficulty_level": "beginner"}'
```

If any readiness check fails, return to `PHASE2.md` and complete missing work first.

---

## Deliverables Checklist

By the end of Phase 3, you should have:

- [ ] Pydantic models for example generation request/response
- [ ] Prompt templates and version tracking for example generation
- [ ] `card_examples` persistence model + migration
- [ ] `example_generator` service with cache-first immutable behavior
- [ ] `POST /v1/card/{card_id}/example` endpoint
- [ ] Backend error handling aligned with `docs/ERRORS.md`
- [ ] Frontend API client + TanStack Query integration
- [ ] Gated **Show example** UI with loading/error states
- [ ] Tests for schema, service caching, route behavior, and frontend interaction

---

## Detailed Steps

### Step 1: Add Example Schema Models

Create `backend/app/schemas/example.py`.

**1.1 Define request and response models**

- `ExampleGenerateRequest`:
  - `style: Literal["default", "analogy", "real_world"] = "default"`
  - `length: Literal["short", "medium", "long"] = "medium"`
  - `constraints: list[str] | None` (max 10 items, each 1-200 chars)
- `ExampleResponse` aligned to `docs/schemas/example.schema.json`
- `LLMExampleOutput` for structured LLM output (without transport metadata fields)

**1.2 Suggested model skeleton**

```python
"""Pydantic schemas for card example generation."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


Constraint = Annotated[str, Field(min_length=1, max_length=200)]
StepItem = Annotated[str, Field(min_length=1, max_length=300)]
PitfallItem = Annotated[str, Field(min_length=1, max_length=200)]
SourceRef = Annotated[str, Field(min_length=1, max_length=50)]


class ExampleGenerateRequest(SchemaBase):
    style: Literal["default", "analogy", "real_world"] = "default"
    length: Literal["short", "medium", "long"] = "medium"
    constraints: Annotated[list[Constraint] | None, Field(max_length=10)] = None


class TokenUsage(SchemaBase):
    prompt: int = Field(..., ge=0)
    completion: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class GenerationMetadata(SchemaBase):
    model: str
    prompt_version: str
    tokens: TokenUsage
    timestamp: datetime
    rag_used: bool = False


class ExampleResponse(SchemaBase):
    schema_version: Literal["1.0"] = "1.0"
    card_id: UUID
    example: Annotated[str, Field(min_length=1, max_length=2000)]
    steps: Annotated[list[StepItem] | None, Field(max_length=10)] = None
    pitfalls: Annotated[list[PitfallItem] | None, Field(max_length=5)] = None
    source_refs: list[SourceRef] | None = None
    generation_metadata: GenerationMetadata


class LLMExampleOutput(SchemaBase):
    example: Annotated[str, Field(min_length=1, max_length=2000)]
    steps: Annotated[list[StepItem] | None, Field(max_length=10)] = None
    pitfalls: Annotated[list[PitfallItem] | None, Field(max_length=5)] = None
    source_refs: list[SourceRef] | None = None
```

**1.3 Export symbols**

Update `backend/app/schemas/__init__.py` to export example schemas.

---

### Step 2: Extend Prompt Registry for Examples

Update `backend/app/prompts/registry.py`.

**2.1 Add prompt constants**

- `EXAMPLE_SYSTEM_PROMPT_V1`
- `EXAMPLE_USER_PROMPT_V1`

**2.2 Add helper**

Implement `get_example_prompts(...)` with inputs:

- `title: str`
- `bullets: list[str]`
- `example_hint: str | None`
- `style: str`
- `length: str`
- `constraints: list[str] | None`

**2.3 Extend prompt version map**

Include example entries in `PROMPT_VERSIONS`, e.g.:

```python
PROMPT_VERSIONS = {
    "deck_system": "v1",
    "deck_user": "v1",
    "example_system": "v1",
    "example_user": "v1",
}
```

**2.4 Prompt quality rules**

- Keep content grounded in the card title/bullets
- No contradiction with card bullets
- Keep examples concise and pedagogically actionable
- Follow constraints if provided; ignore invalid/unsafe constraints

---

### Step 3: Add DB Persistence for Example Cache

Add `CardExample` model in `backend/app/db/models.py`.

**3.1 Model requirements**

- Table: `card_examples`
- Fields:
  - `example_id` UUID primary key
  - `card_id` UUID FK to `cards.card_id` with cascade delete
  - `request_fingerprint` string length 64
  - `style` string
  - `length` string
  - `constraints` JSONB nullable
  - `payload` JSONB (full `ExampleResponse`)
  - `created_at` timezone-aware datetime
- Unique constraint: `(card_id, request_fingerprint)`

**3.2 Suggested SQLAlchemy fragment**

```python
class CardExample(Base):
    __tablename__ = "card_examples"
    __table_args__ = (
        UniqueConstraint("card_id", "request_fingerprint", name="uq_card_examples_card_req"),
    )

    example_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.card_id", ondelete="CASCADE"), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    style = Column(String(32), nullable=False)
    length = Column(String(32), nullable=False)
    constraints = Column(JSONB, nullable=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
```

**3.3 Migration**

```bash
cd backend
alembic revision --autogenerate -m "add_card_examples_table"
alembic upgrade head
```

---

### Step 4: Implement Example Generator Service

Create `backend/app/services/example_generator.py`.

**4.1 Service contract**

Create a method similar to:

```python
async def generate_or_get_example(
    card_id: UUID,
    request: ExampleGenerateRequest,
    db: Session,
) -> tuple[ExampleResponse, bool]:
    ...
```

Return tuple: `(example_response, from_cache)`.

**4.2 Core flow (required order)**

1. Compute deterministic request fingerprint
2. Load card row by `card_id`
3. If missing: raise `NOT_FOUND`
4. Read card payload, enforce `example_possible == true`
5. Lookup existing `CardExample` by `(card_id, request_fingerprint)`
6. If found: return cached payload with `from_cache=True`
7. Build prompts and call LLM with `temperature=0.7`
8. Validate with `LLMExampleOutput`
9. If validation fails, perform one repair pass
10. Build full `ExampleResponse` with metadata
11. Persist `CardExample` payload
12. Return response with `from_cache=False`

**4.3 Request fingerprint spec**

Canonical JSON + SHA-256 hex digest:

```python
fingerprint_payload = {
    "style": request.style,
    "length": request.length,
    "constraints": request.constraints or [],
}
request_fingerprint = hashlib.sha256(
    json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
```

**4.4 Caching policy**

Cache-first immutable for identical fingerprint:

- Same `card_id` + same fingerprint => always return persisted payload
- No regenerate behavior in Phase 3
- Regenerate endpoint/flag is deferred to a later phase

---

### Step 5: Add Card API Route

Create `backend/app/api/v1/routes_card.py`.

**5.1 Endpoint**

- `POST /v1/card/{card_id}/example`
- Body: `ExampleGenerateRequest` (optional body allowed; defaults apply)
- Response model: `ExampleResponse`

**5.2 Status code behavior**

- `201 Created`: new example generated and persisted
- `200 OK`: example returned from cache

**5.3 Error mapping**

Use top-level error object exactly as in `docs/ERRORS.md`:

- `NOT_FOUND` (404) when card does not exist
- `INVALID_INPUT` (400) when `example_possible` is false
- `SCHEMA_VALIDATION_FAILED` (502)
- `LLM_PROVIDER_ERROR` (502)
- `INTERNAL_ERROR` (500)

**5.4 Request tracing**

Do not bypass middleware. Ensure responses carry `X-Request-ID`.

---

### Step 6: Wire Router and Dependencies

Update `backend/app/api/v1/__init__.py`:

```python
from app.api.v1 import routes_card, routes_health

router = APIRouter(prefix="/v1")
router.include_router(routes_health.router, tags=["Health"])
router.include_router(routes_card.router, prefix="/card", tags=["Card"])
```

Ensure DB session dependency and service construction follow the same DI pattern used by deck generation work from Phase 2.

---

### Step 7: Frontend API Client and Types

Update `frontend/src/lib/api.ts`.

**7.1 Add types**

- `ExampleGenerateRequest`
- `ExampleResponse`
- Shared metadata/token subtypes if not already present

**7.2 Add API function**

```ts
export async function generateCardExample(
  cardId: string,
  request: ExampleGenerateRequest = {}
): Promise<ExampleResponse> {
  ...
}
```

**7.3 Error handling**

Preserve current `APIClientError` pattern and parse top-level `error` object.

---

### Step 8: Add TanStack Query for Example Caching

Install dependency:

```bash
cd frontend
npm install @tanstack/react-query
```

**8.1 Create provider**

Add `frontend/src/app/providers.tsx` with `QueryClientProvider` and one `QueryClient` instance.

**8.2 Wire provider**

Wrap app content in `frontend/src/app/layout.tsx`.

**8.3 Query key contract**

Use:

```ts
["card-example", cardId, style, length, constraintsHash]
```

Where `constraintsHash` is stable for identical constraints (e.g., canonical JSON string).

**8.4 Cache configuration**

- `staleTime`: 24 hours
- `gcTime`: 24 hours
- cache-first UI behavior with explicit retry option on error

---

### Step 9: Add Show Example UI Integration

Create `frontend/src/components/flashcards/ExamplePanel.tsx`.

**9.1 Render gating**

Only show **Show example** when `concept.example_possible === true`.

**9.2 UX states**

- Idle: button visible
- Loading: skeleton/placeholder visible
- Success: render `example`, optional `steps`, optional `pitfalls`
- Error: show actionable message with retry button

**9.3 Design alignment**

Follow existing dark/amber tokens in `frontend/src/app/globals.css`:

- `var(--bg-secondary)`
- `var(--text-primary)`
- `var(--accent-primary)`
- existing utility classes (`glass`, `stack-card`, etc.)

Do not introduce a separate purple/gray theme.

---

### Step 10: Testing and Verification

This step defines the full validation matrix for backend, frontend, and smoke testing.

---

## Testing

### Backend Unit Tests

Add tests for:

- `ExampleGenerateRequest` bounds and enum validation
- `ExampleResponse` schema conformance
- request fingerprint determinism

### Backend Service/API Tests

Add tests for:

- card not found -> `404 NOT_FOUND`
- `example_possible=false` -> `400 INVALID_INPUT`
- first call generates -> `201`
- second identical call returns cached payload -> `200`
- invalid LLM output after repair -> `502 SCHEMA_VALIDATION_FAILED`
- response includes `X-Request-ID`

### Frontend Tests

Add tests for:

- hidden button when `example_possible=false`
- click flow: loading -> success render
- cached re-open behavior for same query key
- error and retry behavior

### Manual Smoke Commands

```bash
# Backend tests
cd backend && .venv\Scripts\python.exe -m pytest -v

# Frontend tests
cd frontend && npm test

# Example endpoint smoke call
curl -X POST http://localhost:8000/v1/card/<card_id>/example \
  -H "Content-Type: application/json" \
  -d '{}'
```

Validate:

- First request returns `201`
- Subsequent identical request returns `200`
- Payload stays stable across repeated identical requests

---

## API Contract Changes

Phase 3 adds the following interfaces:

1. `POST /v1/card/{card_id}/example`
2. `ExampleGenerateRequest` request model
3. `ExampleResponse` response model
4. `CardExample` persistence model/table
5. Frontend `generateCardExample(...)` API client function
6. Frontend query key convention: `['card-example', cardId, style, length, constraintsHash]`

---

## Assumptions and Defaults

1. Hard readiness gate is required because Phase 2 implementation may be incomplete.
2. Cache policy is cache-first immutable for identical request fingerprint.
3. Endpoint remains `POST` per `PLAN.md`.
4. Cache hits return `200`; first creation returns `201`.
5. RAG-grounded examples are not required in Phase 3; `source_refs` remains forward-compatible.
6. Error envelope remains aligned to `docs/ERRORS.md`.

---

## Exit Criteria

Before moving to Phase 4, verify all are true:

- [ ] `/v1/card/{card_id}/example` returns schema-valid `ExampleResponse`
- [ ] Examples are generated only when `example_possible=true`
- [ ] First call persists and repeated identical calls return stable cached payload
- [ ] Frontend shows gated example flow with loading/error/success states
- [ ] TanStack Query caching is active with 24h policy
- [ ] Backend and frontend tests pass

---

## Troubleshooting

### Endpoint returns 404 for valid-looking card ID
- Verify `cards` table is populated by Phase 2 deck generation flow
- Verify card belongs to the same environment/database instance

### Endpoint returns 400 `INVALID_INPUT` unexpectedly
- Inspect `cards.payload.example_possible`
- Ensure Phase 2 prompt/model mapping preserves `example_possible` accurately

### Cache miss happens repeatedly for same request
- Verify canonical fingerprint generation (`sort_keys=True`, stable constraints ordering)
- Ensure constraints normalization treats `None` and `[]` consistently

### LLM output validation failures
- Review example prompt constraints and output schema size limits
- Confirm one repair pass is implemented before returning `SCHEMA_VALIDATION_FAILED`

### Frontend example state not reused
- Verify React Query key includes stable `constraintsHash`
- Ensure one shared `QueryClient` instance is used app-wide

---

## Next Steps

Once all Phase 3 exit criteria are met, proceed to **Phase 4: Token and Cost Controls**.

Recommended first Phase 4 items:

1. Add `/v1/deck/estimate`
2. Record token/cost/latency fields per generation
3. Add rate limiting and circuit breaker behavior
