# Phase 4: Token and Cost Controls

## Goal
Implement token estimation, cost tracking, rate limiting, quota enforcement, and circuit breaker protection so users can see cost before generation and the system can prevent runaway usage.

By the end of this phase:

- users can call `POST /v1/deck/estimate` before generating a deck
- backend persists actual usage and latency telemetry for deck/example generations
- `RATE_LIMITED`, `QUOTA_EXCEEDED`, and `CIRCUIT_BREAKER_OPEN` are enforced with consistent error envelopes
- frontend surfaces estimate and protection-state feedback clearly

---

## Status

Completed on **2026-02-15**.
Implementation verification: backend tests **99/99** and frontend tests **15/15**.

Guide revision audited and aligned to repository state on **2026-02-14**.

---

## Audit Notes For This Revision

This guide was updated to correct prior drift and implementation risks:

1. Updated readiness references to current passing suites (`backend 79`, `frontend 9`).
2. Aligned prerequisites with current runtime policy: Docker is optional; native local mode is supported.
3. Removed text encoding corruption (for example malformed UTF-8 sequences) and normalized to ASCII.
4. Corrected frontend API snippet drift (`API_BASE` vs `API_BASE_URL`, `APIClientError` constructor usage).
5. Corrected circuit-breaker half-open behavior (single probe request, not unlimited probes).
6. Clarified telemetry persistence strategy so schema contracts remain stable.
7. Tightened rate-limit guidance to avoid off-by-one and race-prone counter patterns.

---

## Prerequisites

Before implementing Phase 4, confirm:

- [x] Phase 3 is complete and exit criteria are met.
- [x] You have reviewed `PLAN.md` (Phase 4 section) and `docs/ERRORS.md`.
- [x] Backend and frontend run in either supported mode:
  - Docker mode (`docker compose -f docker-compose.dev.yml up`)
  - Native mode (local Python/Node + local Postgres/Redis)
- [x] OpenAI credentials are configured for generation endpoints.
- [x] Redis is reachable from backend (required for quotas/rate limiting).

### Readiness Verification Commands

```bash
# Backend
cd backend && .venv\Scripts\python.exe -m pytest -v

# Frontend
cd frontend && npm test

# Redis reachability (Docker mode)
docker compose -f docker-compose.dev.yml exec redis redis-cli ping
```

Expected baseline:

- backend tests pass (`99/99`)
- frontend tests pass (`15/15`)

If this baseline regresses, remediate Phase 3 behavior before Phase 4 work.

---

## Phase 4 Scope Decisions

To avoid ambiguity, follow these decisions:

1. `POST /v1/deck/estimate` is compute-only. It must not call OpenAI.
2. Response schemas for deck/example remain stable in Phase 4 (`schema_version = "1.0"`). Cost telemetry is persisted server-side.
3. Deck-level telemetry is persisted on `decks`; example-level telemetry is persisted on `card_examples`.
4. Rate limiting and quotas are Redis-backed and fail-open if Redis is unavailable.
5. Circuit breaker is process-local for Phase 4. Distributed breaker state is deferred.

---

## Deliverables Checklist

- [x] `backend/app/services/token_estimator.py`
- [x] `backend/app/services/cost_calculator.py`
- [x] `DeckEstimateRequest` / `DeckEstimateResponse` models in `backend/app/schemas/deck.py`
- [x] `POST /v1/deck/estimate` in `backend/app/api/v1/routes_deck.py`
- [x] Deck DB migration adding `api_cost_cents` to `decks`
- [x] Example DB migration adding telemetry columns to `card_examples`
- [x] Actual deck/example telemetry persistence (tokens, cost, latency)
- [x] Redis-backed rate limit + quota middleware in `backend/app/middleware/rate_limit.py`
- [x] OpenAI circuit breaker in `backend/app/services/circuit_breaker.py`
- [x] Frontend estimate preview and new error handling states
- [x] Backend and frontend tests for all new controls
- [x] Docs sync (`PHASE4.md`, `AGENTS.md`, and `README.md` only if behavior visible to users changed)

---

## Implementation Steps

### Step 1: Add Dependencies and Config Surface

#### 1.1 Backend dependency

Add `tiktoken` to `backend/pyproject.toml` dependencies.

#### 1.2 Environment variables

Add/update in `.env.example`:

```env
# Phase 4 - token/cost estimation
OPENAI_MODEL=gpt-5-nano

# Phase 4 - rate limits and quotas
REDIS_URL=redis://localhost:6379/1
RATE_LIMIT_REQUESTS_PER_HOUR=30
RATE_LIMIT_DECKS_PER_DAY=10

# Phase 4 - circuit breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_FAILURE_WINDOW_SECONDS=60
CIRCUIT_BREAKER_OPEN_DURATION_SECONDS=30
```

#### 1.3 Non-goal

Do not add billing or payment workflows in Phase 4.

---

### Step 2: Implement Token Estimation Utility

Create `backend/app/services/token_estimator.py`.

#### 2.1 Requirements

- count prompt tokens with `tiktoken`
- support known model mappings and fallback encoding
- return prompt/completion/total breakdown for deck estimates
- remain deterministic and side-effect free

#### 2.2 Suggested interface

```python
class TokenEstimator:
    def __init__(self, model: str) -> None: ...
    def count_tokens(self, text: str) -> int: ...
    def estimate_deck_request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_concepts: int,
    ) -> dict[str, int]: ...
```

#### 2.3 Implementation notes

- prefer `tiktoken.encoding_for_model(model)` with fallback to `o200k_base`
- include a documented schema-overhead constant (for structured output envelope)
- completion estimate should scale with `max_concepts`

---

### Step 3: Implement Cost Calculator Utility

Create `backend/app/services/cost_calculator.py`.

#### 3.1 Requirements

- pricing table keyed by model
- compute USD from prompt/completion tokens
- convert to integer cents for DB persistence
- expose one stable API used by deck/example flows and estimate endpoint

#### 3.2 Suggested interface

```python
@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


class CostCalculator:
    @staticmethod
    def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float: ...
    @staticmethod
    def cost_to_cents(cost_usd: float) -> int: ...
```

#### 3.3 Precision note

Very small requests can round to `0` cents. That is expected with cent-level storage.

---

### Step 4: Add Deck Estimate API Contract and Endpoint

#### 4.1 Add schemas

Extend `backend/app/schemas/deck.py` with:

- `DeckEstimateRequest`
- `DeckEstimateResponse`

Keep request validation aligned with `DeckGenerateRequest` (same topic/scope normalization and bounds).

#### 4.2 Add route

Add `POST /v1/deck/estimate` in `backend/app/api/v1/routes_deck.py`.

Flow:

1. Build prompts via `get_deck_prompts(...)`.
2. Estimate tokens via `TokenEstimator`.
3. Estimate cost via `CostCalculator`.
4. Return a `200` response with estimate payload.

#### 4.3 Critical behavior

- Do not instantiate `LLMClient` here.
- Do not require `OPENAI_API_KEY` for estimate endpoint.
- Keep error envelope consistent with existing `error_response(...)`.

---

### Step 5: Persist Actual Telemetry For Deck and Example Flows

#### 5.1 Deck telemetry

Update `backend/app/db/models.py` `Deck`:

- add `api_cost_cents` column (nullable `Integer`)
- retain existing `tokens_used` and `generation_time_ms`

Create Alembic migration.

#### 5.2 Example telemetry

Update `CardExample` model with telemetry columns:

- `tokens_used` (`Integer`, nullable)
- `api_cost_cents` (`Integer`, nullable)
- `generation_time_ms` (`Integer`, nullable)

Create Alembic migration.

#### 5.3 Deck generation persistence changes

In `backend/app/api/v1/routes_deck.py`:

- measure wall clock around `llm_client.generate_deck(...)`
- compute cost from `response.generation_metadata.tokens`
- persist `tokens_used`, `api_cost_cents`, `generation_time_ms`

#### 5.4 Example generation persistence changes

In `backend/app/services/example_generator.py`:

- measure generation duration for cache misses only
- compute cost from actual token usage
- persist telemetry on new `CardExample` rows
- on cache hit, return existing payload without regeneration

#### 5.5 Contract safety

Do not add cost/latency fields to response schemas in Phase 4 unless you also:

1. update `backend/app/schemas/*.py`
2. update `docs/schemas/*.json`
3. update frontend types and rendering
4. document schema/version implications

---

### Step 6: Implement Rate Limiting and Quotas

Create `backend/app/middleware/rate_limit.py`.

#### 6.1 Limits from PLAN

- hourly request limit: `30` per client
- daily deck generation quota: `10` per client

Client identity:

- authenticated user id when available
- otherwise client IP (respect proxy handling policy)

#### 6.2 Enforcement targets

- apply hourly limit to mutating endpoints (`POST`/`PUT`/`PATCH`/`DELETE`)
- apply daily deck quota to `POST /v1/deck/generate`
- exclude `/health`, `/v1/health`, `/docs`, `/redoc`, `/openapi.json`

#### 6.3 Counter strategy

Use Redis counters with TTL windows:

- hourly key example: `rl:hour:{client}:{YYYYMMDDHH}`
- daily deck key example: `quota:deck:{client}:{YYYYMMDD}`

For each key:

1. `INCR key`
2. if value is `1`, set `EXPIRE` to window length
3. reject when count exceeds limit
4. set `Retry-After` from remaining TTL

#### 6.4 Error mapping

- hourly limit -> `429 RATE_LIMITED`
- daily deck quota -> `429 QUOTA_EXCEEDED`
- include `Retry-After` for `RATE_LIMITED`

#### 6.5 Middleware order

In `backend/app/main.py`:

- add `RateLimitMiddleware` first
- add `RequestIDMiddleware` after it

Because Starlette executes middleware in reverse registration order, this ensures rate-limited responses still include `X-Request-ID`.

#### 6.6 Redis failure policy

If Redis is unavailable, fail-open and log a warning with request path and request id.

---

### Step 7: Implement Circuit Breaker For OpenAI Calls

Create `backend/app/services/circuit_breaker.py`.

#### 7.1 Required behavior

- closed state by default
- open after threshold failures in rolling window
- reject requests while open
- half-open after open duration
- allow exactly one probe request in half-open
- close and reset on successful probe
- reopen on failed probe

#### 7.2 Suggested configuration

- failure threshold: `5`
- failure window: `60s`
- open duration: `30s`

all configurable via env vars from Step 1.

#### 7.3 Integration points

Integrate into:

- `backend/app/services/llm_client.py`
- `backend/app/services/example_generator.py`

Pattern:

1. check `allow_request()`
2. perform provider call
3. record success/failure
4. raise `CircuitBreakerOpenError` when blocked

#### 7.4 Failure classification

Count only provider/transient failures (timeouts, connection errors, provider 429/5xx).
Do not count:

- input validation errors
- schema validation failures from application parsing
- DB persistence failures

#### 7.5 Route error mapping

In both `routes_deck.py` and `routes_card.py`:

- map `CircuitBreakerOpenError` to:
  - status `503`
  - code `CIRCUIT_BREAKER_OPEN`
  - `retryable=true`

---

### Step 8: Frontend Estimate UX and Error States

#### 8.1 API client updates

In `frontend/src/lib/api.ts`:

- add `DeckEstimateRequest` / `DeckEstimateResponse` types
- add `estimateDeck(...)` using `API_BASE`
- keep current `APIClientError` pattern via `toAPIError(...)`

#### 8.2 Estimate preview component

Create `frontend/src/components/flashcards/EstimatePreview.tsx`.

Display:

- estimated tokens
- estimated cost
- estimated time

Behavior:

- debounce topic/options input (about 300ms)
- non-blocking (user can submit while estimate is loading)
- silent failure (hide estimate on estimate request error)

#### 8.3 Home page wiring

In `frontend/src/app/page.tsx`:

- render estimate preview near generation controls
- gate estimation on meaningful input (`topic.trim().length >= 3`)

#### 8.4 Error message mapping

Handle these codes with user-friendly text:

- `RATE_LIMITED`: include countdown/retry hint
- `QUOTA_EXCEEDED`: daily limit reached
- `CIRCUIT_BREAKER_OPEN`: service recovering

---

### Step 9: Documentation and Wiring Sync

#### 9.1 Backend wiring

- ensure `routes_deck.py` exposes `/estimate`
- ensure schema exports include estimate models if needed by imports

#### 9.2 Docs to sync

- `PHASE4.md` (this guide)
- `AGENTS.md` recent updates log
- `README.md` only if user-visible behavior changed (new endpoint usage or env requirements)

---

## Testing Plan

### Backend Unit Tests (`backend/tests/unit/`)

Add:

- `test_token_estimator.py`
- `test_cost_calculator.py`
- `test_circuit_breaker.py`

Coverage:

- deterministic token counts and model fallback
- cost computation and cents conversion
- breaker state transitions and single-probe half-open behavior

### Backend API/Route Tests (`backend/tests/unit/`)

Add:

- `test_estimate.py`
- `test_rate_limit.py`
- `test_cost_tracking.py`

Coverage:

- `/v1/deck/estimate` success and input validation
- estimate endpoint does not invoke OpenAI client
- `429 RATE_LIMITED` and `429 QUOTA_EXCEEDED` behavior
- `Retry-After` header presence
- Redis fail-open behavior
- `503 CIRCUIT_BREAKER_OPEN` mapping
- `api_cost_cents` and `generation_time_ms` persistence

### Frontend Tests (`frontend/__tests__/`)

Add:

- `estimate-preview.test.tsx`
- `phase4-error-handling.test.tsx`

Coverage:

- estimate preview render/hide/loading states
- rate-limited/quota/circuit-breaker message rendering

---

## Manual Verification

### PowerShell

```powershell
# Backend tests
cd backend; .venv\Scripts\python.exe -m pytest -v

# Frontend tests
cd ../frontend; npm test

# Estimate endpoint smoke
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/deck/estimate" `
  -ContentType "application/json" `
  -Body '{"topic":"Binary Search Trees","difficulty_level":"beginner","max_concepts":5}'

# Rate-limit smoke (expect 429 after threshold)
1..35 | ForEach-Object {
  try {
    $resp = Invoke-WebRequest `
      -Method Post `
      -Uri "http://localhost:8000/v1/deck/estimate" `
      -ContentType "application/json" `
      -Body '{"topic":"Limit test","difficulty_level":"beginner"}'
    $resp.StatusCode
  } catch {
    $_.Exception.Response.StatusCode.value__
  }
}
```

### Bash

```bash
# Backend tests
cd backend && .venv/Scripts/python.exe -m pytest -v

# Frontend tests
cd ../frontend && npm test

# Estimate endpoint smoke
curl -X POST http://localhost:8000/v1/deck/estimate \
  -H "Content-Type: application/json" \
  -d '{"topic":"Binary Search Trees","difficulty_level":"beginner","max_concepts":5}'
```

---

## API Contract Changes Introduced In Phase 4

1. `POST /v1/deck/estimate`
2. `DeckEstimateRequest`
3. `DeckEstimateResponse`
4. `decks.api_cost_cents` persistence field
5. `card_examples` telemetry fields (`tokens_used`, `api_cost_cents`, `generation_time_ms`)
6. `RATE_LIMITED` (`429`) and `QUOTA_EXCEEDED` (`429`) enforcement behavior
7. `CIRCUIT_BREAKER_OPEN` (`503`) enforcement behavior
8. `Retry-After` header on rate-limited responses

---

## Risks and Mitigations

1. Risk: estimate drift from actual usage.
Mitigation: compare estimate vs actual in logs/tests and tune constants.

2. Risk: cost rounds to zero in cents for cheap requests.
Mitigation: expected at cent granularity; use aggregated metrics for budgeting.

3. Risk: Redis outage disables protections.
Mitigation: fail-open + high-signal logging + alerting.

4. Risk: in-process circuit breaker not shared across workers.
Mitigation: acceptable for Phase 4; plan Redis-backed breaker for multi-instance scale.

---

## Exit Criteria

Before starting Phase 5, verify all are true:

- [x] `POST /v1/deck/estimate` returns valid estimate payload and does not call OpenAI
- [x] deck generation persists `tokens_used`, `api_cost_cents`, and `generation_time_ms`
- [x] example generation persists telemetry for newly generated examples
- [x] rate limiting returns `429 RATE_LIMITED` + `Retry-After` when exceeded
- [x] daily deck quota returns `429 QUOTA_EXCEEDED` when exceeded
- [x] circuit breaker opens under repeated provider failures and returns `503 CIRCUIT_BREAKER_OPEN`
- [x] frontend shows estimate preview and handles Phase 4 error codes clearly
- [x] backend and frontend tests are green

---

## Troubleshooting

### Estimate endpoint fails without API key

Cause:

- route accidentally initializes LLM client

Fix:

- ensure estimate path uses prompt builder + token/cost utilities only

### Rate limits never trigger

Cause:

- Redis key not written, path not matched, or middleware not registered

Fix:

- verify middleware registration and key naming
- verify Redis connectivity and selected DB index

### Rate-limited response missing `X-Request-ID`

Cause:

- middleware order incorrect

Fix:

- ensure `RateLimitMiddleware` is added before `RequestIDMiddleware` in `main.py`

### Circuit breaker opens too aggressively

Cause:

- non-provider errors counted as breaker failures

Fix:

- narrow failure classification to provider/transient errors only

### `api_cost_cents` appears frequently as `0`

Cause:

- costs below one cent round down

Fix:

- expected for low-cost requests; verify larger requests and aggregate spend trends

---

## Next Steps

After Phase 4 exit criteria are satisfied, continue with **Phase 5: PDF Upload and Ingestion (RAG)**:

1. Implement resource upload + validation endpoints.
2. Add ingestion worker pipeline (extract, chunk, embed, upsert).
3. Wire retrieval context into deck generation with source attribution.
