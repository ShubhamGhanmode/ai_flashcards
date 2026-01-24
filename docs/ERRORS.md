# Error Codes

## Error Response Shape
```json
{
  "error": {
    "code": "SCHEMA_VALIDATION_FAILED",
    "message": "Deck output failed schema validation.",
    "request_id": "req_123",
    "retryable": false,
    "details": {
      "fields": ["concepts[2].bullets"],
      "reason": "Expected 5 items."
    },
    "recovery_action": "Please try again with a simpler topic."
  }
}
```

## Codes
| Code | HTTP | Retryable | When it happens |
| --- | --- | --- | --- |
| INVALID_INPUT | 400 | No | Missing or invalid request fields, invalid difficulty, or malformed JSON. |
| SCHEMA_VALIDATION_FAILED | 502 | No | LLM output does not conform to schema after a repair attempt. |
| LLM_PROVIDER_ERROR | 502 | Yes | Upstream LLM error that is not a rate limit (5xx). |
| LLM_TIMEOUT | 504 | Yes | LLM call exceeded time limit. |
| CIRCUIT_BREAKER_OPEN | 503 | Yes | System is temporarily refusing requests due to repeated failures. Wait 30-60 seconds. |
| RATE_LIMITED | 429 | Yes | User or system rate limit exceeded. |
| QUOTA_EXCEEDED | 429 | No | Daily or monthly quota exceeded. |
| RESOURCE_TOO_LARGE | 413 | No | Uploaded file exceeds configured size. |
| RESOURCE_UNSUPPORTED_TYPE | 415 | No | File type not supported or magic bytes mismatch. |
| RESOURCE_NOT_READY | 409 | Yes | Resource ingestion still processing. |
| RESOURCE_FAILED | 422 | No | Resource ingestion failed; error details in response. |
| RAG_RETRIEVAL_TIMEOUT | 504 | Yes | Vector retrieval timed out; system may fall back to non-RAG. |
| RAG_NO_RELEVANT_CHUNKS | 200 | No | Retrieval produced low similarity; `rag_used=false`. |
| AUTH_REQUIRED | 401 | No | Endpoint requires authentication. |
| FORBIDDEN | 403 | No | Access to workspace or resource denied. |
| NOT_FOUND | 404 | No | Deck, card, or resource ID not found. |
| CONFLICT | 409 | No | Duplicate upload or conflicting operation. |
| INTERNAL_ERROR | 500 | Yes | Unhandled server error. |

## Validation Error Details
When `INVALID_INPUT` is returned, the `details` object includes:
```json
{
  "details": {
    "validation_errors": [
      {
        "field": "topic",
        "message": "String should have at least 1 character",
        "type": "string_too_short"
      },
      {
        "field": "difficulty_level",
        "message": "Input should be 'beginner', 'intermediate', or 'advanced'",
        "type": "literal_error"
      }
    ]
  }
}
```

## Recovery Actions by Error Code
| Code | Suggested UI Action |
| --- | --- |
| INVALID_INPUT | Show field-level errors, highlight invalid inputs. |
| SCHEMA_VALIDATION_FAILED | "We couldn't generate this deck. Try a different topic." |
| LLM_PROVIDER_ERROR | "Service temporarily unavailable. Retrying..." (auto-retry) |
| LLM_TIMEOUT | "Generation is taking longer than expected. Retrying..." |
| CIRCUIT_BREAKER_OPEN | "System is recovering. Please wait a moment and try again." |
| RATE_LIMITED | "Too many requests. Please wait X seconds." (show countdown) |
| QUOTA_EXCEEDED | "Daily limit reached. Upgrade plan or wait until tomorrow." |
| RESOURCE_TOO_LARGE | "File too large. Maximum size is 25MB." |
| RESOURCE_NOT_READY | Show processing spinner, poll for status. |
| NOT_FOUND | "Deck not found. It may have been deleted." |
| INTERNAL_ERROR | "Something went wrong. Please try again." (with "Report Issue" link) |

## Notes
- `request_id` should be logged on the server and returned in responses.
- Use a consistent `code` for client-side handling; do not rely on `message` parsing.
- When `rag_used=false`, prefer a successful response with a warning rather than an error.
- Include `recovery_action` in responses when applicable to guide user behavior.

