# Data Retention and Deletion Policy (Draft)

## Scope
This policy covers user-provided content (PDFs), generated decks/examples, embeddings, and logs.

## Defaults (MVP)
- Decks and examples: retained until user deletes or for 90 days of inactivity, whichever comes first.
- Uploaded PDFs and extracted text: retained until user deletes; subject to storage limits.
- Embeddings and vector store entries: deleted when the corresponding resource is deleted.
- Cache entries (examples, decks): 24 hours.
- Application logs: 30 days with minimal content data.
- Backups: 30 days rolling retention.

## Deletion Behavior

### Soft Delete vs Hard Delete
- **Soft delete** (default): Data is marked as deleted and hidden from user, retained for 7 days for recovery.
- **Hard delete**: Data is permanently removed from all storage layers. Available via admin action or after soft delete grace period.
- User-initiated deletion performs soft delete immediately.

### Cascade Behavior
- **Workspace deletion**: Cascades to all resources, decks, and cards within the workspace.
- **Resource deletion**: Removes associated embeddings and vector store entries.
- **Deck deletion**: Removes all cards and cached examples for that deck.

### Purge Process
- A background purge removes soft-deleted data from caches and vector stores within 24 hours.
- Backup copies are purged on the next backup cycle and fully removed within 30 days.
- Orphaned embeddings are cleaned up weekly.

## Access Controls
- Resource access is scoped to workspace membership.
- Decks and examples are accessible only to the creating user or workspace.

## Data Minimization
- Avoid storing raw prompts or full LLM responses in logs.
- Store only necessary metadata (token counts, timestamps, status, errors).
- Redact PII from error messages before logging.

## Data Export
- Users can request a full data export via `/user/export` endpoint.
- Export includes:
  - All decks and cards (JSON format)
  - Uploaded resources (original files)
  - Generation metadata
- Export is delivered as a downloadable ZIP file.
- Export requests are rate-limited (1 per 24 hours).

## Compliance Notes

### GDPR Considerations
- **Right to Access**: Users can view and export all their data.
- **Right to Erasure**: Users can delete their data; hard delete removes data from backups within 30 days.
- **Data Portability**: Export endpoint provides machine-readable format (JSON).
- **Lawful Basis**: Processing is based on legitimate interest for service provision.

### CCPA Considerations
- **Right to Know**: Users can access their stored data via export.
- **Right to Delete**: Deletion flow described above satisfies requirement.
- **Do Not Sell**: No data is sold to third parties.

### Pre-Production Checklist
- [ ] Implement user-facing deletion flow.
- [ ] Implement admin-only hard-delete path.
- [ ] Add export endpoint with rate limiting.
- [ ] Configure backup retention and purge schedules.
- [ ] Document data processing in privacy policy.

