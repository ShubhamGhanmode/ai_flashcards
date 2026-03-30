# Phase 5: PDF Upload and Ingestion (RAG)

## Goal
Implement the first end-to-end RAG flow so users can upload PDFs, wait for ingestion to complete, and generate deck responses grounded in those resources with citations.

By the end of this phase:

- users can upload PDFs into an anonymous workspace
- backend ingests those PDFs asynchronously and stores retrievable chunks
- `POST /v1/deck/generate` can ground deck generation in READY resources
- deck responses populate existing `sources`, `concepts[].source_refs`, and `generation_metadata.rag_used`
- frontend exposes a minimal resource-management flow without introducing auth yet

---

## Status

Not started. This guide was written on **2026-03-08** against the current Phase 4 baseline:

- backend tests: **99/99**
- frontend tests: **15/15**

Phase 4 remains the current implemented state. Phase 5 is the next delivery target.

---

## Prerequisites

Before starting Phase 5, confirm:

- [x] Phase 4 is complete and all Phase 4 exit criteria are still true
- [x] You have reviewed `PLAN.md` (Phase 5 section)
- [x] You have reviewed `docs/ERRORS.md`, `docs/RAG_SAFETY.md`, and `docs/DATA_RETENTION.md`
- [x] You have reviewed `docs/schemas/deck.schema.json` and understand that the existing deck schema already supports `sources`, `source_refs`, `rag_used`, and `retrieval_metrics`
- [x] PostgreSQL and Redis are available locally (Docker or native mode)
- [x] `OPENAI_API_KEY` is configured for generation and embeddings

### Readiness Verification Commands

```bash
# Backend
cd backend && .venv\Scripts\python.exe -m pytest -v

# Frontend
cd frontend && npm test
```

If Phase 4 behavior regresses, fix that first. Do not layer RAG work on a broken deck/example baseline.

---

## Phase 5 Scope Decisions

Use these decisions to keep the implementation small and consistent with the current repo.

1. Use anonymous workspaces for now.
   The frontend should create and persist a browser-local `workspace_id` UUID. Do not add user accounts or auth in Phase 5.

2. Use Redis Queue (`rq`) for ingestion jobs.
   Redis is already part of the stack. Do not add Celery in this phase.

3. Use filesystem-backed PDF storage in Phase 5.
   Store uploaded PDFs under a configurable local directory. Do not add MinIO or S3 wiring unless deployment work actually requires it. The existing object-storage placeholders in `.env.example` can remain reserved for later phases.

4. Use Chroma for vector storage.
   It is already present in backend dependencies and is enough for the current single-host architecture.

5. Keep chunk text and metadata in Chroma only.
   Postgres should store resource rows, status, and aggregate counts. Do not add a `resource_chunks` SQL table unless a real query need appears.

6. Keep public deck schema at `1.0`.
   Populate the existing schema fields instead of introducing a Phase 5-only schema version.

7. Keep deck orchestration close to the existing deck route.
   Add `rag_retriever.py` and ingestion worker modules, but do not add a generic `deck_generator.py` abstraction unless the route becomes unmanageable after a first implementation pass.

8. Degrade gracefully when retrieval is weak or slow.
   Retrieval timeout or low relevance should fall back to normal deck generation with `rag_used=false`. The only hard block is when the user explicitly supplied a workspace that still has uploads processing and no READY resources.

---

## Deliverables Checklist

- [ ] Backend dependencies and env surface for uploads, queueing, embeddings, and Chroma persistence
- [ ] `backend/app/schemas/resources.py`
- [ ] `backend/app/api/v1/routes_resources.py`
- [ ] `backend/app/services/rag_retriever.py`
- [ ] `backend/app/workers/ingestion_jobs.py`
- [ ] Resource persistence model + Alembic migration
- [ ] `DeckGenerateRequest` and `DeckEstimateRequest` accept optional `workspace_id`
- [ ] Deck generation can use READY workspace resources and populate citations
- [ ] Estimate endpoint stays compute-only and becomes workspace-aware
- [ ] Frontend workspace helper, resource API client functions, and resources page
- [ ] Frontend deck-builder wiring for resource-backed generation
- [ ] Tests for upload, ingestion, retrieval, fallback, and UI states
- [ ] Docs sync (`PHASE5.md`, `AGENTS.md`, and `README.md`; update schema docs if public API changes)

---

## Implementation Steps

### Step 1: Add Dependencies and Config Surface

Update `backend/pyproject.toml` with the minimum new packages:

- `python-multipart` for FastAPI file uploads
- `pypdf` for PDF text extraction
- `rq` for Redis-backed ingestion jobs

Do not add OCR packages yet. OCR is still a later enhancement.

Add these environment variables to `.env.example` when implementation starts:

```env
# Phase 5 - Resource uploads and ingestion
RESOURCE_UPLOAD_DIR=backend/.data/resources
CHROMA_PERSIST_DIR=backend/.data/chroma
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
INGESTION_QUEUE_NAME=resource-ingestion
MAX_UPLOAD_SIZE_MB=25
MAX_WORKSPACE_FILES=10
UPLOADS_PER_HOUR=5

# Phase 5 - Retrieval
RAG_TOP_K=6
RAG_SIMILARITY_THRESHOLD=0.65
RAG_MAX_CONTEXT_TOKENS=4000
RAG_RETRIEVAL_TIMEOUT_SECONDS=5
```

Keep the existing object-storage variables documented, but do not wire them into runtime behavior in this phase.

### Step 2: Add the Worker Process

Add a `worker` service to both Compose files.

Development command shape:

```bash
rq worker resource-ingestion
```

Use the same backend image / dependency set and the same Postgres, Redis, OpenAI, and Chroma env vars as the API container.

### Step 3: Define Resource API Schemas

Create `backend/app/schemas/resources.py` with:

- `ResourceStatus`: `Literal["UPLOADED", "PROCESSING", "READY", "FAILED", "DELETED"]`
- `ResourceUploadResponse`
- `ResourceStatusResponse`
- `ResourceListItem`

Recommended fields:

- `resource_id`
- `workspace_id`
- `filename`
- `status`
- `size_bytes`
- `page_count`
- `chunk_count`
- `error`
- `created_at`
- `updated_at`

Do not add a separate public schema for chunk-level debug data in Phase 5.

Also update `backend/app/schemas/deck.py`:

- add `workspace_id: UUID | None = None` to `DeckGenerateRequest`
- add `workspace_id: UUID | None = None` to `DeckEstimateRequest`
- extend `LLMConcept` so the model can emit `source_refs`

The response shape of `DeckResponse` already supports RAG citations. Reuse it.

### Step 4: Add Resource Persistence

Update `backend/app/db/models.py`.

Add a `Resource` model with the minimum fields needed for upload, status, and deletion:

- `resource_id` UUID primary key
- `workspace_id` UUID, indexed
- `filename`
- `storage_path`
- `file_hash`
- `mime_type`
- `size_bytes`
- `status`
- `page_count`
- `chunk_count`
- `error_message`
- `created_at`
- `updated_at`
- `deleted_at`

Add these constraints:

- unique active upload per `(workspace_id, file_hash)` to support duplicate detection
- filter deleted resources out of normal list/retrieval queries

Also add `workspace_id` to `decks` so persisted decks can be tied back to the resource scope used during generation.

Do not add a `Workspace` table in Phase 5. The workspace is just a UUID boundary for grouping resources.

### Step 5: Implement Upload, List, Status, and Delete Endpoints

Create `backend/app/api/v1/routes_resources.py` and mount it under `/v1/resources`.

Required endpoints:

1. `POST /v1/resources/upload`
2. `GET /v1/resources`
3. `GET /v1/resources/{resource_id}/status`
4. `DELETE /v1/resources/{resource_id}`

#### Upload behavior

Use `multipart/form-data` with:

- `workspace_id`
- `file`

Validate:

- file size against `MAX_UPLOAD_SIZE_MB`
- PDF magic bytes (`%PDF-`)
- workspace file count against `MAX_WORKSPACE_FILES`
- upload rate limit (`UPLOADS_PER_HOUR`) per workspace or client IP

On upload:

1. compute SHA-256 hash
2. reject duplicate active uploads in the same workspace with `409 CONFLICT`
3. save file under `RESOURCE_UPLOAD_DIR/<workspace_id>/<resource_id>.pdf`
4. create `Resource(status="UPLOADED")`
5. enqueue ingestion job
6. transition to `PROCESSING` as part of queue handoff

Error mappings must follow `docs/ERRORS.md`:

- too large -> `413 RESOURCE_TOO_LARGE`
- bad type / magic bytes mismatch -> `415 RESOURCE_UNSUPPORTED_TYPE`
- duplicate upload -> `409 CONFLICT`
- missing resource -> `404 NOT_FOUND`

#### Delete behavior

On delete:

1. mark row deleted (`deleted_at`)
2. remove stored PDF
3. remove Chroma documents for `resource_id`
4. return success even if the vector delete is already idempotent

This is the minimum safe behavior for Phase 5. Backup-retention cleanup remains later work.

### Step 6: Implement the Ingestion Worker

Create `backend/app/workers/ingestion_jobs.py`.

Keep the worker simple. One module is enough until the flow proves too large.

Required flow:

1. load resource row
2. mark status `PROCESSING`
3. open PDF with `pypdf.PdfReader`
4. reject encrypted or password-protected PDFs with `RESOURCE_FAILED`
5. extract page text
6. normalize whitespace and invalid Unicode
7. fail if extracted text is effectively empty
8. chunk text with page metadata
9. embed chunks with `OpenAIEmbeddings`
10. upsert chunks into Chroma
11. mark resource `READY` with `page_count` and `chunk_count`

Recommended chunking defaults:

- target size: about 800 tokens
- overlap: about 120 tokens
- preserve `page_start` / `page_end`

Chroma metadata per chunk should include:

- `resource_id`
- `workspace_id`
- `filename`
- `page_start`
- `page_end`
- `chunk_index`
- `content_hash`

If ingestion fails after partial vector writes, delete any inserted Chroma rows for that `resource_id` before marking the resource `FAILED`.

### Step 7: Add Retrieval and Prompt Context Injection

Create `backend/app/services/rag_retriever.py`.

The retriever should:

1. confirm the workspace has active resources
2. distinguish these cases:
   - no resources at all -> `400 INVALID_INPUT`
   - resources exist but none READY yet -> `409 RESOURCE_NOT_READY`
   - all resources failed and none READY -> `422 RESOURCE_FAILED`
3. query Chroma only across READY resources in the workspace
4. filter results below `RAG_SIMILARITY_THRESHOLD`
5. cap prompt context to `RAG_MAX_CONTEXT_TOKENS`
6. return deduplicated `sources[]`, concept-usable reference IDs, and retrieval metrics

Add a `RAG_CONTEXT_TEMPLATE_V1` entry to `backend/app/prompts/registry.py`.

Prompting rules:

- treat retrieved PDF text as untrusted reference material
- label every excerpt clearly as reference content
- tell the model it may only cite `source_id` values present in the provided context
- instruct the model to leave `source_refs` empty if a concept is not grounded in a retrieved excerpt
- update `generation_metadata.prompt_version` so RAG-backed generations identify the RAG prompt/template path rather than reusing the plain non-RAG version string

### Step 8: Extend Deck Generation and Estimate Flows

Update `backend/app/api/v1/routes_deck.py`.

#### `POST /v1/deck/generate`

When `workspace_id` is present:

1. call `rag_retriever.py`
2. if good chunks are found, append RAG context to the prompt path
3. call the existing `LLMClient`
4. populate:
   - `concepts[].source_refs`
   - top-level `sources`
   - `generation_metadata.rag_used`
   - `generation_metadata.retrieval_metrics`
5. persist `workspace_id` on the deck row

Fallback behavior:

- low relevance -> generate a normal deck with `rag_used=false`
- retrieval timeout -> generate a normal deck with `rag_used=false`
- uploads still processing and no READY resources -> return `RESOURCE_NOT_READY`

Do not convert low-relevance retrieval into a hard error.

#### `POST /v1/deck/estimate`

Keep this endpoint compute-only.

When `workspace_id` is present and READY resources exist:

1. run retrieval only
2. estimate prompt size including selected excerpts
3. return a workspace-aware estimate

Do not instantiate `LLMClient` from the estimate route.

### Step 9: Frontend Workspace and Resource Management

Add a small workspace helper, for example `frontend/src/lib/workspace.ts`.

Required behavior:

- create a UUID once in the browser
- persist it in `localStorage`
- reuse it across page loads

Update `frontend/src/lib/api.ts` with:

- `uploadResource(...)`
- `listResources(...)`
- `getResourceStatus(...)`
- `deleteResource(...)`

Add `frontend/src/app/workspace/[workspaceId]/resources/page.tsx`.

That page should provide:

- PDF upload control
- resource list
- status chips (`UPLOADED`, `PROCESSING`, `READY`, `FAILED`)
- delete action
- polling while any resource is processing

Keep the UI aligned with the current amber / glass visual language. Do not introduce a separate admin-looking theme.

Update `frontend/src/app/page.tsx` to:

- create or load the anonymous workspace
- link to the resources page
- pass `workspace_id` to `estimateDeck()` and `generateDeck()` when resource-backed generation is intended
- surface `RESOURCE_NOT_READY` and `RESOURCE_FAILED` messages cleanly

Minimal UI is enough in Phase 5. A richer RAG transparency panel belongs in Phase 6.

### Step 10: Testing and Verification

#### Backend unit tests

Add coverage for:

- resource schema validation
- duplicate file hash detection
- PDF magic-byte validation
- empty / encrypted PDF failure handling
- chunk metadata generation
- prompt assembly with RAG context and source IDs

#### Backend integration tests

Add coverage for:

- upload -> ingest -> READY transition
- upload duplicate -> `409 CONFLICT`
- deck generation with READY resources returns citations
- estimate with `workspace_id` remains compute-only
- retrieval timeout falls back to `rag_used=false`
- delete removes Chroma entries for the resource

#### Frontend tests

Add coverage for:

- workspace ID persistence
- resources page upload / list / status polling
- home page passes `workspace_id`
- RAG-specific errors render actionable messages

#### Manual verification

```powershell
# Upload a PDF
Invoke-WebRequest `
  -Method Post `
  -Uri "http://localhost:8000/v1/resources/upload" `
  -Form @{
    workspace_id = "<workspace-id>"
    file = Get-Item ".\\sample.pdf"
  }

# List resources
Invoke-RestMethod `
  -Uri "http://localhost:8000/v1/resources?workspace_id=<workspace-id>"

# Generate a resource-backed deck
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/deck/generate" `
  -ContentType "application/json" `
  -Body '{"topic":"Binary search trees","difficulty_level":"beginner","workspace_id":"<workspace-id>"}'
```

Validate:

- upload returns a resource ID
- resource transitions to `READY`
- generated deck includes `sources`
- at least some concepts include `source_refs`

---

## API Contract Changes Introduced In Phase 5

1. `POST /v1/resources/upload`
2. `GET /v1/resources`
3. `GET /v1/resources/{resource_id}/status`
4. `DELETE /v1/resources/{resource_id}`
5. `workspace_id` added to `DeckGenerateRequest`
6. `workspace_id` added to `DeckEstimateRequest`
7. `DeckResponse.sources` and `concepts[].source_refs` become populated for RAG-backed decks
8. `generation_metadata.rag_used` and `generation_metadata.retrieval_metrics` become meaningful for workspace-backed generation

If any public response field changes beyond the existing deck schema, update:

- `backend/app/schemas/*.py`
- `docs/schemas/*.json`
- frontend API types
- `README.md`

---

## Risks And Mitigations

1. Risk: bad PDF extraction yields empty or noisy chunks.
   Mitigation: fail clearly on empty extraction and keep OCR out of scope for now.

2. Risk: upload and ingestion add too many moving parts at once.
   Mitigation: keep storage local, keep one queue, keep one worker module, and avoid auth.

3. Risk: vector store and SQL drift after partial failures.
   Mitigation: delete partial Chroma rows on ingestion failure and on resource deletion.

4. Risk: weak retrieval gives misleading citations.
   Mitigation: enforce a similarity threshold and fall back to `rag_used=false` when confidence is low.

5. Risk: local disk growth from uploads and Chroma persistence.
   Mitigation: delete aggressively, store only PDFs + vectors, and document cleanup in Phase 7/8.

---

## Exit Criteria

Before moving to Phase 6, verify all are true:

- [ ] PDFs can be uploaded and listed by workspace
- [ ] ingestion runs asynchronously and transitions resources to `READY` or `FAILED`
- [ ] duplicate uploads are rejected per workspace
- [ ] `POST /v1/deck/generate` can use READY resources and return citations
- [ ] `POST /v1/deck/estimate` accepts `workspace_id` and stays compute-only
- [ ] low-relevance and retrieval-timeout paths fall back to `rag_used=false`
- [ ] frontend exposes a resource-management page and can trigger resource-backed generation
- [ ] backend and frontend tests are green

---

## Troubleshooting

### Upload fails with `RESOURCE_UNSUPPORTED_TYPE`

- verify the file is a real PDF and begins with `%PDF-`
- verify the upload route reads the file stream before saving it

### Resource stays stuck in `PROCESSING`

- verify the `worker` process is running
- verify the queue name matches `INGESTION_QUEUE_NAME`
- inspect worker logs for extraction or embedding failures

### Deck generation ignores uploaded PDFs

- confirm the request included `workspace_id`
- confirm at least one resource in that workspace is `READY`
- inspect retrieval scores and threshold filtering

### Citations appear but page numbers are wrong

- verify chunk metadata preserves page boundaries before overlap/merge
- do not derive page numbers from chunk order alone

### Delete removes the DB row but not vectors

- verify the delete path filters Chroma documents by `resource_id`
- make the delete operation idempotent and log vector delete counts

---

## Next Steps

Once Phase 5 exit criteria are satisfied, continue to **Phase 6: RAG Quality Signals and UX Transparency**.

Recommended first Phase 6 items:

1. make retrieval metrics consistently visible in persisted deck payloads
2. add a clear RAG summary to the deck UI
3. add a guarded developer debug path only if troubleshooting needs it
