/**
 * API client for the Flashcard backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// Types
// =============================================================================

export interface DeckGenerateRequest {
  topic: string;
  difficulty_level: "beginner" | "intermediate" | "advanced";
  max_concepts?: number;
  scope?: string;
}

export interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

export interface GenerationMetadata {
  model: string;
  prompt_version: string;
  tokens: TokenUsage;
  timestamp: string;
  rag_used: boolean;
}

export interface Concept {
  card_id: string;
  title: string;
  bullets: string[];
  example_possible: boolean;
  example_hint?: string;
}

export interface DeckResponse {
  schema_version: string;
  deck_id: string;
  topic: string;
  scope?: string;
  difficulty_level: string;
  concepts: Concept[];
  generation_metadata: GenerationMetadata;
}

export interface APIError {
  code: string;
  message: string;
  retryable: boolean;
  request_id?: string;
  details?: Record<string, unknown>;
  recovery_action?: string;
}

// =============================================================================
// Error Handling
// =============================================================================

export class APIClientError extends Error {
  constructor(
    public error: APIError,
    public status: number,
  ) {
    super(error.message);
    this.name = "APIClientError";
  }
}

function toAPIError(
  payload: unknown,
  status: number,
  requestId: string | null,
): APIError {
  const fallback: APIError = {
    code: "HTTP_ERROR",
    message: `Request failed with status ${status}`,
    retryable: status >= 500,
    request_id: requestId ?? undefined,
  };

  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const data = payload as Record<string, unknown>;

  if (data.error && typeof data.error === "object") {
    const structured = data.error as Record<string, unknown>;
    return {
      code:
        typeof structured.code === "string" ? structured.code : fallback.code,
      message:
        typeof structured.message === "string"
          ? structured.message
          : fallback.message,
      retryable:
        typeof structured.retryable === "boolean"
          ? structured.retryable
          : fallback.retryable,
      request_id:
        requestId ||
        (typeof structured.request_id === "string"
          ? structured.request_id
          : undefined),
      details:
        structured.details && typeof structured.details === "object"
          ? (structured.details as Record<string, unknown>)
          : undefined,
      recovery_action:
        typeof structured.recovery_action === "string"
          ? structured.recovery_action
          : undefined,
    };
  }

  if (typeof data.detail === "string") {
    return {
      ...fallback,
      code: status === 422 ? "VALIDATION_ERROR" : fallback.code,
      message: data.detail,
    };
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const first = data.detail[0];
    const firstDetail =
      first && typeof first === "object"
        ? (first as Record<string, unknown>)
        : null;
    if (firstDetail && typeof firstDetail.msg === "string") {
      return {
        ...fallback,
        code: "VALIDATION_ERROR",
        message: firstDetail.msg,
        details: { detail: data.detail },
      };
    }
  }

  if (typeof data.message === "string") {
    return {
      ...fallback,
      message: data.message,
    };
  }

  return fallback;
}

// =============================================================================
// API Functions
// =============================================================================

export async function generateDeck(
  request: DeckGenerateRequest,
): Promise<DeckResponse> {
  const response = await fetch(`${API_BASE}/v1/deck/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const requestId = response.headers.get("X-Request-ID");
    const error = toAPIError(payload, response.status, requestId);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  return response.json();
}

export async function getDeck(deckId: string): Promise<DeckResponse> {
  const response = await fetch(`${API_BASE}/v1/deck/${deckId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const requestId = response.headers.get("X-Request-ID");
    const error = toAPIError(payload, response.status, requestId);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  return response.json();
}
