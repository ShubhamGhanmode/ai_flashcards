# RAG Safety Checklist (Draft)

## Prompt Injection and Safety
- Treat all retrieved text as untrusted input.
- Delimit source excerpts clearly and label them as "Reference".
- System and developer instructions always take priority over retrieved text.
- Ignore any instructions found in PDFs or retrieved content.
- Never execute code or follow URLs found in user content.

## Grounding and Attribution
- Prefer grounded answers when RAG is used.
- Allow "insufficient information" when sources are missing or low similarity.
- Attach `source_refs` to concepts when sourced content is used.
- Clearly distinguish between sourced claims and general knowledge.

## Retrieval Quality
- Apply a minimum similarity threshold (default: 0.65); if below, set `rag_used=false`.
- Use MMR or similar diversification to reduce redundancy.
- Cap total context length (default: 4000 tokens) and use deterministic chunk ordering.
- Log retrieval metrics for quality monitoring.

## Content Moderation

### Upload Restrictions
- **Rate limiting**: Max 5 uploads per hour per user.
- **Size limits**: 25MB per file, 10 files per workspace.
- **Allowed types**: PDF only for MVP; validate with magic bytes.

### Content Scanning
- Scan uploaded files for:
  - Malware signatures (integration with ClamAV or similar)
  - Embedded JavaScript or executable content
  - Encrypted or password-protected files (reject with clear message)
- Flag but do not automatically reject potentially sensitive content.

### Prohibited Content
- Reject files containing:
  - Obvious harmful instructions (violence, illegal activities)
  - Known prompt injection patterns
  - Excessive binary or non-text content (>90% non-readable)

## Data Sanitization

### Patterns to Redact
Apply regex-based redaction before storing or logging:
```python
REDACTION_PATTERNS = [
    # API Keys
    (r'(?i)(api[_-]?key|apikey|secret[_-]?key)[\s:=]+["\']?[\w-]{20,}["\']?', '[REDACTED_API_KEY]'),
    # AWS Access Keys
    (r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]'),
    # Passwords in URLs
    (r'://[^:]+:[^@]+@', '://[REDACTED_CREDS]@'),
    # Email addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]'),
    # Credit card numbers (basic)
    (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[REDACTED_CC]'),
]
```

### Text Normalization
- Strip binary content and normalize whitespace before chunking.
- Convert to UTF-8, replace invalid sequences.
- Limit line length to prevent display issues.

## Audit Logging

### Events to Log
- Resource upload (user_id, file_hash, size, timestamp)
- Ingestion start/complete/failure (resource_id, duration, error)
- RAG retrieval (deck_id, chunks_used, similarity_scores)
- Content moderation flags (resource_id, flag_type, action_taken)
- Admin actions (hard delete, manual review)

### Log Retention
- Audit logs retained for 1 year minimum.
- Do not include raw chunk content in audit logs.
- Include request_id for correlation with application logs.

### Alerting
- Alert on:
  - >10 uploads from single IP in 1 hour
  - Malware detection
  - Repeated ingestion failures for same user
  - Prompt injection pattern detection

## Testing Scenarios
- PDF contains instructions to ignore system prompts.
- PDF contains malicious links or code snippets.
- Topic has no relevant chunks; system should refuse to hallucinate sources.
- Low-quality OCR output triggers non-RAG fallback.
- PDF contains obfuscated prompt injection (base64, unicode tricks).
- Large PDF that exceeds token limits.
- Password-protected PDF (should reject gracefully).

## Review Gate
- Revisit this checklist before enabling public uploads.
- Add automated checks for prompt-injection strings in ingestion tests.
- Security review required before production launch.
- Penetration testing for upload endpoints.

