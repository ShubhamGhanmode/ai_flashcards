# Phase 6: RAG Quality Signals and UX Transparency

## Goal
Make RAG behavior inspectable and understandable after Phase 5 so users can tell when uploaded material actually influenced a deck, and developers can verify retrieval quality without turning the product into a debug console.

By the end of this phase:

- deck payloads consistently expose useful retrieval metrics
- the deck UI clearly communicates whether RAG helped
- source usage is understandable at a glance
- optional developer-only inspection remains gated behind an env flag

---

## Status

Not started. This phase depends on Phase 5 being complete first.

This guide intentionally assumes the public deck schema remains at `1.0` and builds on the existing fields:

- `sources`
- `generation_metadata.rag_used`
- `generation_metadata.retrieval_metrics`
- `concepts[].source_refs`

---

## Prerequisites

Before starting Phase 6, confirm:

- [ ] Phase 5 exit criteria are all met
- [ ] resource upload, ingestion, and RAG-backed deck generation work end to end
- [ ] persisted deck payloads already include citations for successful RAG generations
- [ ] you have reviewed `PLAN.md` (Phase 6 section)
- [ ] you have reviewed `docs/schemas/deck.schema.json` and will not change schema version casually

Recommended verification:

```bash
cd backend && .venv\Scripts\python.exe -m pytest -v
cd frontend && npm test
```

---

## Phase 6 Scope Decisions

1. Do not bump the public deck schema version.
   Reuse `rag_used`, `retrieval_metrics`, `sources`, and `source_refs`.

2. Do not add duplicate RAG metric columns to `decks`.
   The persisted JSON payload remains the source of truth for Phase 6.

3. Distinguish three user-facing states:
   - no resource-backed generation attempted
   - RAG applied successfully
   - RAG attempted but the system fell back to general generation

4. Keep the UI summary concise.
   Show a short explanation and a source list, not an analytics dashboard.

5. Keep deep inspection optional.
   Only add a debug endpoint or hidden page if logs and the normal UI are not enough for active development.

---

## Deliverables Checklist

- [ ] Retrieval metrics are populated consistently for workspace-aware generation attempts
- [ ] `GET /v1/deck/{deck_id}` preserves and returns those metrics unchanged
- [ ] Deck UI renders a clear RAG summary when relevant
- [ ] Deck UI renders fallback messaging when RAG was attempted but not used
- [ ] Source list UX is polished enough to be understandable without raw JSON
- [ ] Optional debug route is gated by env flag if implemented
- [ ] Backend and frontend tests cover success, fallback, and hidden states
- [ ] Docs sync (`PHASE6.md`, `AGENTS.md`, and `README.md` if user-visible behavior changes)

---

## Implementation Steps

### Step 1: Normalize Retrieval Metric Semantics

Keep the public metric contract small and stable:

- `chunks_retrieved`
- `avg_similarity`
- `distinct_pages`

Phase 6 should define exactly when those fields appear.

Recommended rule:

- if `workspace_id` was not part of generation, leave `retrieval_metrics=None`
- if `workspace_id` was present and retrieval ran, populate `retrieval_metrics`
  - successful RAG: real values
  - low-relevance fallback: zero or filtered values, with `rag_used=false`
  - timeout fallback: zero values, with `rag_used=false`

This lets the UI distinguish "plain non-RAG deck" from "RAG attempted but not used" without adding new public fields.

If you adopt this rule, also update the schema descriptions and backend comments that currently imply `retrieval_metrics` only appears when RAG succeeds.

### Step 2: Keep Persistence Minimal

The deck payload already stores `generation_metadata` and `sources`.

Phase 6 should not add new SQL columns for:

- chunks used
- pages used
- similarity score
- source counts

Those are either already persisted in the JSON payload or can be derived from it.

Only add new persistence if the optional debug route truly needs a separate payload and logs prove the current information is insufficient.

### Step 3: Add User-Facing RAG Summary UI

Update the deck experience in the existing `frontend/src/components/flashcards` area.

You may add a small component such as `RagSummary.tsx` if it keeps `DeckSwiper.tsx` readable.

Required display states:

#### RAG used

Show a short summary such as:

`Generated from 4 excerpts across 3 pages from 2 PDFs.`

Derive:

- excerpts from `retrieval_metrics.chunks_retrieved`
- pages from `retrieval_metrics.distinct_pages`
- PDF count from unique `sources[].resource_id`

#### RAG attempted but not used

Show a concise fallback message such as:

`Resources were checked, but no relevant excerpts were used. This deck was generated from model knowledge.`

Only show this if:

- `retrieval_metrics` is present
- `rag_used` is `false`

#### Plain non-RAG deck

Show nothing. Do not add noise to decks that were never resource-backed.

### Step 4: Improve Source Transparency

Render sources in a human-readable way on the deck page.

Minimum source list behavior:

- filename / title
- page range
- short snippet when available

Recommended UX:

- compact summary banner above the deck
- collapsible source list below or beside the swiper
- per-card citation chips only if they stay visually light

Do not dump raw `source_id` strings without context.

### Step 5: Optional Developer Debug Route

This is optional. Only implement it if normal logs plus the user-facing summary are not enough.

If implemented:

- route: `GET /v1/deck/{deck_id}/rag-debug`
- env flag: `ENABLE_RAG_DEBUG=1`
- default behavior when disabled: `404 NOT_FOUND` or `403 FORBIDDEN`

Debug payload may include:

- selected chunk metadata
- similarity scores
- page spans
- snippet previews
- resource IDs

Do not expose this route in the normal frontend navigation.

If you must persist debug data, prefer a single nullable JSON payload associated with the deck instead of a new table hierarchy.

### Step 6: Keep Frontend State Management Simple

Continue using the existing API client and query patterns.

Do not add a separate global store for RAG transparency.

The deck page already has what it needs:

- fetched deck payload
- sources
- retrieval metadata

This phase is presentation and semantics work, not a state-management rewrite.

### Step 7: Testing And Verification

#### Backend tests

Add coverage for:

- successful RAG generation persists metrics
- low-relevance fallback still persists `retrieval_metrics` with `rag_used=false`
- timeout fallback preserves the same semantics
- `GET /v1/deck/{deck_id}` returns metrics unchanged
- debug route is hidden when `ENABLE_RAG_DEBUG` is off, if implemented

#### Frontend tests

Add coverage for:

- RAG summary renders for `rag_used=true`
- fallback message renders for `rag_used=false` with `retrieval_metrics`
- no summary renders for plain non-RAG decks
- source list shows page ranges and snippets when present

#### Manual verification

Check these three scenarios:

1. workspace-backed generation with good matches
2. workspace-backed generation with no relevant matches
3. plain generation without `workspace_id`

The resulting deck pages should be visually and semantically distinct.

---

## API Contract Semantics Updated In Phase 6

Phase 6 does not need a large public API expansion.

The main contract change is semantic:

1. `generation_metadata.retrieval_metrics` should be interpreted as "RAG retrieval was attempted"
2. `generation_metadata.rag_used=true` means retrieved excerpts materially influenced the generated deck
3. `generation_metadata.rag_used=false` with populated `retrieval_metrics` means retrieval ran but the system fell back

Optional addition:

4. `GET /v1/deck/{deck_id}/rag-debug` behind `ENABLE_RAG_DEBUG`

If you add the optional debug route, document it in `README.md`.

---

## Risks And Mitigations

1. Risk: the UI implies sources were used when they were only searched.
   Mitigation: tie the main success message strictly to `rag_used=true`.

2. Risk: fallback decks look broken rather than intentional.
   Mitigation: render a specific fallback explanation when `retrieval_metrics` exists but `rag_used=false`.

3. Risk: too much debug information leaks to normal users.
   Mitigation: keep deep inspection behind an explicit env flag.

4. Risk: metric values drift from the actual selected chunks.
   Mitigation: calculate metrics from the final filtered chunk set, not the raw candidate set.

---

## Exit Criteria

Before moving to Phase 7, verify all are true:

- [ ] resource-backed decks clearly show whether uploaded material was used
- [ ] deck UI shows a concise summary for successful RAG generations
- [ ] deck UI shows a clear fallback notice when retrieval ran but was not used
- [ ] plain non-RAG decks remain visually quiet
- [ ] source list rendering is readable and grounded in the response payload
- [ ] optional debug path is hidden by default if implemented
- [ ] backend and frontend tests are green

---

## Troubleshooting

### Summary banner never appears

- verify the deck payload includes `generation_metadata.retrieval_metrics`
- verify the frontend type includes `retrieval_metrics`

### Fallback decks look identical to non-RAG decks

- ensure the backend populates `retrieval_metrics` even when `rag_used=false` after a retrieval attempt

### Source list duplicates the same PDF many times

- deduplicate display groups by `resource_id`
- keep the raw `sources[]` array intact if concept-level refs depend on individual source IDs

### Debug route exposes too much information

- remove it from normal navigation
- require `ENABLE_RAG_DEBUG=1`
- trim snippet length and never expose raw full chunks by default

---

## Next Steps

After Phase 6, move to **Phase 7: Production Hardening and Testing**.

Recommended first Phase 7 items:

1. PDF torture tests and retrieval evals
2. CI coverage for upload, ingestion, and fallback paths
3. load testing for worker throughput and deck-generation latency
