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

export type DeckEstimateRequest = DeckGenerateRequest;

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

export interface DeckGenerationStatusEvent {
  type: "status" | "heartbeat";
  phase: "queued" | "generating" | "finalizing";
  message: string;
  stage_index: number;
  stage_total: number;
  elapsed_seconds: number;
  estimated_seconds: number;
  request_id?: string;
}

export interface DeckGenerationCompleteEvent {
  type: "complete";
  deck: DeckResponse;
  request_id?: string;
}

export interface DeckGenerationErrorEvent {
  type: "error";
  status_code: number;
  error: APIError;
}

export type DeckGenerationEvent =
  | DeckGenerationStatusEvent
  | DeckGenerationCompleteEvent
  | DeckGenerationErrorEvent;

export interface DeckEstimateResponse {
  schema_version: string;
  model: string;
  estimated_tokens: TokenUsage;
  estimated_cost_usd: number;
  estimated_cost_cents: number;
  estimated_seconds: number;
}

export interface ExampleGenerateRequest {
  style?: "default" | "analogy" | "real_world";
  length?: "short" | "medium" | "long";
  constraints?: string[];
}

export interface ExampleResponse {
  schema_version: string;
  card_id: string;
  example: string;
  steps?: string[];
  pitfalls?: string[];
  source_refs?: string[];
  generation_metadata: GenerationMetadata;
}

export interface APIError {
  code: string;
  message: string;
  retryable: boolean;
  request_id?: string;
  retry_after_seconds?: number;
  details?: Record<string, unknown>;
  recovery_action?: string;
}

interface StreamDeckGenerationOptions {
  signal?: AbortSignal;
  onEvent?: (event: DeckGenerationEvent) => void;
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
  retryAfter: string | null,
): APIError {
  const retryAfterSeconds = retryAfter
    ? Number.parseInt(retryAfter, 10)
    : Number.NaN;
  const parsedRetryAfter = Number.isNaN(retryAfterSeconds)
    ? undefined
    : Math.max(0, retryAfterSeconds);

  const fallback: APIError = {
    code: "HTTP_ERROR",
    message: `Request failed with status ${status}`,
    retryable: status >= 500,
    request_id: requestId ?? undefined,
    retry_after_seconds: parsedRetryAfter,
  };

  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const data = payload as Record<string, unknown>;

  if (data.error && typeof data.error === "object") {
    const structured = data.error as Record<string, unknown>;
    const details =
      structured.details && typeof structured.details === "object"
        ? (structured.details as Record<string, unknown>)
        : undefined;
    const detailRetryAfter =
      details && typeof details.retry_after_seconds === "number"
        ? details.retry_after_seconds
        : undefined;

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
      retry_after_seconds: parsedRetryAfter ?? detailRetryAfter,
      details,
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

function parseStreamEvent(rawEvent: string): DeckGenerationEvent | null {
  const lines = rawEvent
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  let eventName = "";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null;
  }

  const payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;

  if (eventName === "status" || eventName === "heartbeat") {
    return {
      type: eventName,
      phase: payload.phase as DeckGenerationStatusEvent["phase"],
      message: String(payload.message ?? ""),
      stage_index: Number(payload.stage_index ?? 0),
      stage_total: Number(payload.stage_total ?? 0),
      elapsed_seconds: Number(payload.elapsed_seconds ?? 0),
      estimated_seconds: Number(payload.estimated_seconds ?? 0),
      request_id:
        typeof payload.request_id === "string" ? payload.request_id : undefined,
    };
  }

  if (eventName === "complete" && payload.deck) {
    return {
      type: "complete",
      deck: payload.deck as DeckResponse,
      request_id:
        typeof payload.request_id === "string" ? payload.request_id : undefined,
    };
  }

  if (eventName === "error" && payload.error) {
    return {
      type: "error",
      status_code:
        typeof payload.status_code === "number" ? payload.status_code : 500,
      error: payload.error as APIError,
    };
  }

  return null;
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
    const retryAfter = response.headers.get("Retry-After");
    const error = toAPIError(payload, response.status, requestId, retryAfter);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  return response.json();
}

export async function streamDeckGeneration(
  request: DeckGenerateRequest,
  options: StreamDeckGenerationOptions = {},
): Promise<DeckResponse> {
  const response = await fetch(`${API_BASE}/v1/deck/generate/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal: options.signal,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const requestId = response.headers.get("X-Request-ID");
    const retryAfter = response.headers.get("Retry-After");
    const error = toAPIError(payload, response.status, requestId, retryAfter);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  if (!response.body) {
    throw new APIClientError(
      {
        code: "STREAM_ERROR",
        message: "Deck stream ended before any progress could be read.",
        retryable: true,
        request_id: response.headers.get("X-Request-ID") ?? undefined,
      },
      502,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);

      if (rawEvent) {
        const event = parseStreamEvent(rawEvent);
        if (event) {
          options.onEvent?.(event);

          if (event.type === "complete") {
            return event.deck;
          }

          if (event.type === "error") {
            throw new APIClientError(event.error, event.status_code);
          }
        }
      }

      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }

  throw new APIClientError(
    {
      code: "STREAM_ERROR",
      message: "Deck stream ended unexpectedly before completion.",
      retryable: true,
      request_id: response.headers.get("X-Request-ID") ?? undefined,
    },
    502,
  );
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
    const retryAfter = response.headers.get("Retry-After");
    const error = toAPIError(payload, response.status, requestId, retryAfter);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  return response.json();
}

export async function generateCardExample(
  cardId: string,
  request: ExampleGenerateRequest = {},
): Promise<ExampleResponse> {
  const response = await fetch(`${API_BASE}/v1/card/${cardId}/example`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const requestId = response.headers.get("X-Request-ID");
    const retryAfter = response.headers.get("Retry-After");
    const error = toAPIError(payload, response.status, requestId, retryAfter);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  return response.json();
}

export async function estimateDeck(
  request: DeckEstimateRequest,
): Promise<DeckEstimateResponse> {
  const response = await fetch(`${API_BASE}/v1/deck/estimate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const requestId = response.headers.get("X-Request-ID");
    const retryAfter = response.headers.get("Retry-After");
    const error = toAPIError(payload, response.status, requestId, retryAfter);
    throw new APIClientError(
      error,
      response.status,
    );
  }

  return response.json();
}
