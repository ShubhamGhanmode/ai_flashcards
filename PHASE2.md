# Phase 2: Schema-first Deck Generation (No RAG)

## Goal
Implement strict schema validation and a working `/v1/deck/generate` flow that always returns valid JSON responses and renders in the UI. By the end of this phase, you'll be able to generate flashcard decks from any topic.

---

## Prerequisites

Before starting Phase 2, ensure:

- [ ] Phase 1 is complete and all exit criteria are met
- [ ] Docker Compose is running with all services healthy
- [ ] You have a valid OpenAI API key in your `.env` file
- [ ] You've reviewed `docs/schemas/deck.schema.json`

---

## Deliverables Checklist

By the end of Phase 2, you should have:

- [ ] Pydantic models matching the JSON schemas
- [ ] `/v1/deck/generate` endpoint with OpenAI Structured Outputs
- [ ] `/v1/deck/{deck_id}` endpoint to retrieve saved decks
- [ ] Database tables for decks and cards
- [ ] Structured logging with request tracing
- [ ] Input validation and sanitization
- [ ] Flashcard UI that renders deck responses
- [ ] Tests covering core functionality

---

## Detailed Steps

### Step 1: API Versioning Setup

We'll organize routes under `/v1/` for future API versioning. Keep the root `/health` endpoint for Docker health checks and add `/v1/health` for the versioned API.

**1.1 Create the versioned API structure:**

```bash
# Navigate to backend
cd d:/Projects/ai_flashcards/backend

# Create v1 API directory
mkdir -p app/api/v1
```

**1.2 Create `backend/app/api/v1/__init__.py`:**

```python
"""API v1 routes package."""

from fastapi import APIRouter

from app.api.v1 import routes_deck, routes_health

router = APIRouter(prefix="/v1")

# Include all v1 routes
router.include_router(routes_health.router, tags=["Health"])
router.include_router(routes_deck.router, prefix="/deck", tags=["Deck"])
```

**1.3 Create `backend/app/api/v1/routes_health.py`:**

```python
"""Health check endpoint for API v1."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    timestamp: str
    version: str
    api_version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check for v1 API."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
        api_version="v1",
    )
```

**1.4 Update `backend/app/main.py` to use versioned routes:**

Replace the router inclusion section:

```python
"""Main FastAPI application entry point."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.api.routes_health import router as health_router
from app.middleware.request_id import RequestIDMiddleware

# ... (keep the structlog configuration)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Flashcard Learning Assistant API",
        description="Generate flashcard decks from topics with optional RAG",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(RequestIDMiddleware)

    # Include routers
    app.include_router(health_router, tags=["Health"])  # Root health check
    app.include_router(v1_router)  # All v1 routes

    # ... (keep startup/shutdown events)

    return app

app = create_app()
```

---

### Step 2: Pydantic Schema Models

**2.1 Create `backend/app/schemas/deck.py`:**

```python
"""Pydantic models for deck generation."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    """Base schema that forbids extra fields to match JSON Schema."""

    model_config = ConfigDict(extra="forbid")


Bullet = Annotated[str, Field(min_length=1, max_length=300)]
BulletList = Annotated[list[Bullet], Field(min_length=5, max_length=5)]
SourceRef = Annotated[str, Field(min_length=1, max_length=50)]


# =============================================================================
# Request Models
# =============================================================================

class DeckGenerateRequest(SchemaBase):
    """Request model for deck generation."""

    topic: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="The topic to generate flashcards for",
            examples=["Binary Search Trees", "Photosynthesis"],
        ),
    ]
    difficulty_level: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="Target difficulty level",
    )
    max_concepts: Annotated[int, Field(ge=3, le=7)] = 5
    scope: Annotated[str | None, Field(min_length=1, max_length=200)] = None

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "topic": "Binary Search Trees",
                "difficulty_level": "intermediate",
                "max_concepts": 5,
            }
        },
    )


# =============================================================================
# Response Models
# =============================================================================

class TokenUsage(SchemaBase):
    """Token usage statistics."""

    prompt: int = Field(..., ge=0)
    completion: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class RetrievalMetrics(SchemaBase):
    """Retrieval metrics when RAG is used."""

    chunks_retrieved: int = Field(..., ge=0)
    avg_similarity: float = Field(..., ge=0.0, le=1.0)
    distinct_pages: int = Field(..., ge=0)


class GenerationMetadata(SchemaBase):
    """Metadata about the generation process."""

    model: str
    prompt_version: str
    tokens: TokenUsage
    timestamp: datetime
    rag_used: bool = False
    retrieval_metrics: RetrievalMetrics | None = None


class Source(SchemaBase):
    """Source reference for RAG-backed responses."""

    source_id: str = Field(..., min_length=1)
    resource_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    snippet: str | None = Field(default=None, min_length=1)
    url: str | None = None
    content_hash: str | None = Field(default=None, min_length=8)


class Concept(SchemaBase):
    """A single concept card."""

    card_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=100)
    bullets: BulletList
    example_possible: bool
    example_hint: str | None = Field(default=None, max_length=200)
    source_refs: list[SourceRef] | None = None


class DeckResponse(SchemaBase):
    """Response model for a generated deck."""

    schema_version: Literal["1.0"] = "1.0"
    deck_id: UUID
    topic: str
    scope: str | None = None
    difficulty_level: Literal["beginner", "intermediate", "advanced"]
    concepts: Annotated[list[Concept], Field(min_length=3, max_length=7)]
    sources: list[Source] | None = None
    generation_metadata: GenerationMetadata


# =============================================================================
# LLM Output Models (for Structured Output)
# =============================================================================

class LLMConcept(SchemaBase):
    """Concept as generated by the LLM (without card_id)."""

    title: str = Field(..., min_length=1, max_length=100)
    bullets: BulletList
    example_possible: bool
    example_hint: str | None = Field(default=None, max_length=200)


class LLMDeckOutput(SchemaBase):
    """Raw LLM output for deck generation."""

    concepts: Annotated[list[LLMConcept], Field(min_length=3, max_length=7)]
```

---

### Step 3: Prompt Templates

**3.1 Create `backend/app/prompts/registry.py`:**

```python
"""Prompt templates for LLM generation."""

# =============================================================================
# Deck Generation Prompts
# =============================================================================

DECK_SYSTEM_PROMPT_V1 = """You are an expert educational content creator.
Your task is to create a set of flashcard concepts for learning.

Rules:
1. Generate between 3-7 concept cards based on the topic.
2. Each concept must have exactly 5 bullet points.
3. Bullets should progress from basic to more nuanced understanding.
4. Set example_possible to true only if a concrete example would help.
5. If example_possible is true, provide a brief example_hint.
6. Keep bullet points concise (under 100 characters each).
7. Ensure concepts are distinct and don't overlap.
8. Match content difficulty to the specified level.

Output valid JSON only. No markdown, no code blocks."""


DECK_USER_PROMPT_V1 = """Create flashcard concepts for:

Topic: {topic}
Difficulty: {difficulty_level}
Number of concepts: {max_concepts}
{scope_line}

Generate educational flashcard concepts following the schema exactly."""


# =============================================================================
# Prompt Version Tracking
# =============================================================================

PROMPT_VERSIONS = {
    "deck_system": "v1",
    "deck_user": "v1",
}


def get_deck_prompts(
    topic: str,
    difficulty_level: str,
    max_concepts: int,
    scope: str | None = None,
) -> tuple[str, str]:
    """Get system and user prompts for deck generation."""
    scope_line = f"Scope: {scope}" if scope else ""
    user_prompt = DECK_USER_PROMPT_V1.format(
        topic=topic,
        difficulty_level=difficulty_level,
        max_concepts=max_concepts,
        scope_line=scope_line,
    )
    return DECK_SYSTEM_PROMPT_V1, user_prompt
```

---

### Step 4: LLM Client Service (LangChain)

**4.1 Create `backend/app/services/llm_client.py`:**

```python
"""LangChain LLM client with structured output support."""

import os
from datetime import datetime, timezone

import structlog
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.schemas.deck import (
    Concept,
    DeckGenerateRequest,
    DeckResponse,
    GenerationMetadata,
    LLMDeckOutput,
    TokenUsage,
)
from app.prompts.registry import get_deck_prompts, PROMPT_VERSIONS

logger = structlog.get_logger()

# Configuration
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT = 60


class LLMClient:
    """Client for LLM with LangChain structured outputs."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

        # Initialize LangChain ChatOpenAI
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=DEFAULT_TEMPERATURE,
            timeout=DEFAULT_TIMEOUT,
            max_retries=2,
        )

        # Create structured output chain
        self.structured_llm = self.llm.with_structured_output(LLMDeckOutput)
        self.model = model_name

    async def generate_deck(
        self,
        request: DeckGenerateRequest,
        deck_id: UUID,
    ) -> DeckResponse:
        """Generate a deck using LangChain with structured output."""

        system_prompt, user_prompt = get_deck_prompts(
            topic=request.topic,
            difficulty_level=request.difficulty_level,
            max_concepts=request.max_concepts,
            scope=request.scope,
        )

        logger.info(
            "llm_call_started",
            model=self.model,
            topic=request.topic,
            difficulty=request.difficulty_level,
        )

        start_time = datetime.now(timezone.utc)

        try:
            # Use LangChain with structured output
            messages = [
                ("system", system_prompt),
                ("human", user_prompt),
            ]

            # Invoke the structured LLM
            llm_output: LLMDeckOutput = await self.structured_llm.ainvoke(messages)

            if llm_output is None:
                raise ValueError("LLM returned empty response")

            # Estimate token usage (LangChain doesn't always provide this)
            # In production, use callbacks for accurate token counting
            estimated_tokens = TokenUsage(
                prompt=len(system_prompt + user_prompt) // 4,  # Rough estimate
                completion=500,  # Placeholder
                total=len(system_prompt + user_prompt) // 4 + 500,
            )

            # Convert to full response with IDs
            concepts = [
                Concept(
                    title=c.title,
                    bullets=c.bullets,
                    example_possible=c.example_possible,
                    example_hint=c.example_hint,
                )
                for c in llm_output.concepts
            ]

            response = DeckResponse(
                deck_id=deck_id,
                topic=request.topic,
                difficulty_level=request.difficulty_level,
                concepts=concepts,
                generation_metadata=GenerationMetadata(
                    model=self.model,
                    prompt_version=PROMPT_VERSIONS["deck_system"],
                    tokens=estimated_tokens,
                    timestamp=start_time,
                    rag_used=False,
                ),
            )

            logger.info(
                "llm_call_completed",
                model=self.model,
                concepts_count=len(concepts),
            )

            return response

        except ValidationError as e:
            logger.error("llm_output_validation_failed", error=str(e))
            raise
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            raise


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
```

**Implementation notes:**
- On `ValidationError`, run a single repair pass using the JSON schema and validation errors. If the repair still fails, surface `SCHEMA_VALIDATION_FAILED` per `docs/ERRORS.md`.
- Capture token usage via LangChain callbacks (e.g., `get_openai_callback`) or response metadata; avoid placeholder counts in production.

> **Note**: LangChain's `with_structured_output()` automatically validates the response against your Pydantic model. This replaces OpenAI's native Structured Outputs with a more portable solution that works with multiple LLM providers.

---

### Step 5: Database Models and Migration

**5.1 Create `backend/app/db/models.py`:**

```python
"""SQLAlchemy database models."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Deck(Base):
    """Deck model for storing generated flashcard decks."""
    
    __tablename__ = "decks"

    deck_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic = Column(String(200), nullable=False)
    difficulty_level = Column(String(20), nullable=False)
    scope = Column(String(200), nullable=True)
    payload = Column(JSONB, nullable=False)  # Full response JSON
    tokens_used = Column(Integer, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    """Card model for individual flashcards."""
    
    __tablename__ = "cards"

    card_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    deck_id = Column(
        UUID(as_uuid=True),
        ForeignKey("decks.deck_id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)  # Full concept JSON
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    deck = relationship("Deck", back_populates="cards")
```

**Note:** Storing the full JSON payload is required; consider adding separate `schema_version` and `generation_metadata` columns later if you want to query or index those fields.

**5.2 Create `backend/app/db/session.py`:**

```python
"""Database session management."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/flashcards"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**5.3 Update Alembic to use the models:**

Edit `backend/app/db/migrations/env.py`, add this near the top:

```python
from app.db.models import Base
target_metadata = Base.metadata
```

**5.4 Create the initial migration:**

```bash
cd backend

# Activate virtual environment
.venv\Scripts\activate

# Create migration
alembic revision --autogenerate -m "create_decks_and_cards_tables"

# Run migration
alembic upgrade head
```

---

### Step 6: Deck Generation Route

**6.1 Create `backend/app/api/v1/routes_deck.py`:**

```python
"""Deck generation endpoints."""

from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Card, Deck
from app.db.session import get_db
from app.middleware.request_id import request_id_var
from app.schemas.deck import DeckGenerateRequest, DeckResponse
from app.services.llm_client import get_llm_client

router = APIRouter()
logger = structlog.get_logger()


def error_response(
    code: str,
    message: str,
    retryable: bool,
    status_code: int,
) -> JSONResponse:
    """Build a standardized error response payload."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id_var.get(),
                "retryable": retryable,
            }
        },
    )


@router.post(
    "/generate",
    response_model=DeckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new flashcard deck",
    description="Generate a deck of flashcard concepts for the given topic.",
)
async def generate_deck(
    request: DeckGenerateRequest,
    db: Session = Depends(get_db),
) -> DeckResponse | JSONResponse:
    """Generate a new flashcard deck."""
    
    deck_id = uuid4()
    logger.info(
        "deck_generation_started",
        deck_id=str(deck_id),
        topic=request.topic,
    )

    try:
        # Generate deck using LLM
        llm_client = get_llm_client()
        response = await llm_client.generate_deck(request, deck_id)

        # Save to database
        deck = Deck(
            deck_id=deck_id,
            topic=request.topic,
            difficulty_level=request.difficulty_level,
            payload=response.model_dump(mode="json"),
            tokens_used=response.generation_metadata.tokens.total,
        )
        db.add(deck)

        # Save individual cards
        for concept in response.concepts:
            card = Card(
                card_id=concept.card_id,
                deck_id=deck_id,
                title=concept.title,
                payload=concept.model_dump(mode="json"),
            )
            db.add(card)

        db.commit()

        logger.info(
            "deck_generation_completed",
            deck_id=str(deck_id),
            concepts_count=len(response.concepts),
        )

        return response

    except ValidationError as e:
        logger.error(
            "deck_generation_validation_failed",
            deck_id=str(deck_id),
            error=str(e),
        )
        return error_response(
            code="SCHEMA_VALIDATION_FAILED",
            message="Deck output failed schema validation.",
            retryable=False,
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            "deck_persist_failed",
            deck_id=str(deck_id),
            error=str(e),
        )
        return error_response(
            code="INTERNAL_ERROR",
            message="Failed to persist deck.",
            retryable=True,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(
            "deck_generation_failed",
            deck_id=str(deck_id),
            error=str(e),
        )
        return error_response(
            code="LLM_PROVIDER_ERROR",
            message="Failed to generate deck",
            retryable=True,
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


@router.get(
    "/{deck_id}",
    response_model=DeckResponse,
    summary="Get a deck by ID",
    description="Retrieve a previously generated deck.",
)
async def get_deck(
    deck_id: UUID,
    db: Session = Depends(get_db),
) -> DeckResponse | JSONResponse:
    """Get a deck by ID."""
    
    deck = db.query(Deck).filter(Deck.deck_id == deck_id).first()
    
    if not deck:
        return error_response(
            code="NOT_FOUND",
            message=f"Deck {deck_id} not found",
            retryable=False,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return DeckResponse.model_validate(deck.payload)
```

---

### Step 7: Frontend API Client

**7.1 Create `frontend/src/lib/api.ts`:**

```typescript
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
    public status: number
  ) {
    super(error.message);
    this.name = "APIClientError";
  }
}

// =============================================================================
// API Functions
// =============================================================================

export async function generateDeck(
  request: DeckGenerateRequest
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
    const error = payload.error || payload.detail || payload;
    const requestId = response.headers.get("X-Request-ID") || error.request_id;
    throw new APIClientError({ ...error, request_id: requestId }, response.status);
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
    const error = payload.error || payload.detail || payload;
    const requestId = response.headers.get("X-Request-ID") || error.request_id;
    throw new APIClientError({ ...error, request_id: requestId }, response.status);
  }

  return response.json();
}
```

---

### Step 8: Flashcard UI Components

Follow the existing design tokens in `frontend/src/app/globals.css` (dark/amber palette and glass styles) to keep the UI consistent.

**8.1 Create `frontend/src/components/flashcards/Flashcard.tsx`:**

```tsx
"use client";

import { useState } from "react";
import type { Concept } from "@/lib/api";

interface FlashcardProps {
  concept: Concept;
  index: number;
  total: number;
}

export function Flashcard({ concept, index, total }: FlashcardProps) {
  const [showAllBullets, setShowAllBullets] = useState(false);
  
  // Show first 2 bullets initially, then reveal rest
  const visibleBullets = showAllBullets
    ? concept.bullets
    : concept.bullets.slice(0, 2);

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6 max-w-lg mx-auto">
      {/* Card Header */}
      <div className="flex justify-between items-start mb-4">
        <span className="text-sm text-gray-500">
          {index + 1} / {total}
        </span>
        {concept.example_possible && (
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
            Example available
          </span>
        )}
      </div>

      {/* Title */}
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        {concept.title}
      </h2>

      {/* Bullets */}
      <ul className="space-y-3 mb-4">
        {visibleBullets.map((bullet, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="text-purple-500 mt-1">•</span>
            <span className="text-gray-700">{bullet}</span>
          </li>
        ))}
      </ul>

      {/* Show More Button */}
      {!showAllBullets && concept.bullets.length > 2 && (
        <button
          onClick={() => setShowAllBullets(true)}
          className="text-purple-600 hover:text-purple-700 text-sm font-medium"
        >
          Show {concept.bullets.length - 2} more points →
        </button>
      )}

      {/* Example Hint */}
      {concept.example_hint && showAllBullets && (
        <div className="mt-4 p-3 bg-purple-50 rounded-lg">
          <p className="text-sm text-purple-700">
            💡 {concept.example_hint}
          </p>
        </div>
      )}
    </div>
  );
}
```

**8.2 Create `frontend/src/components/flashcards/DeckSwiper.tsx`:**

```tsx
"use client";

import { useState } from "react";
import type { DeckResponse } from "@/lib/api";
import { Flashcard } from "./Flashcard";

interface DeckSwiperProps {
  deck: DeckResponse;
}

export function DeckSwiper({ deck }: DeckSwiperProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const goNext = () => {
    if (currentIndex < deck.concepts.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const goPrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const currentConcept = deck.concepts[currentIndex];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">{deck.topic}</h1>
          <p className="text-purple-200">
            {deck.difficulty_level} • {deck.concepts.length} concepts
          </p>
        </div>

        {/* Card */}
        <Flashcard
          concept={currentConcept}
          index={currentIndex}
          total={deck.concepts.length}
        />

        {/* Navigation */}
        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={goPrev}
            disabled={currentIndex === 0}
            className="px-6 py-3 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all"
          >
            ← Previous
          </button>
          <button
            onClick={goNext}
            disabled={currentIndex === deck.concepts.length - 1}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all"
          >
            Next →
          </button>
        </div>

        {/* Progress Dots */}
        <div className="flex justify-center gap-2 mt-6">
          {deck.concepts.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentIndex(i)}
              className={`w-3 h-3 rounded-full transition-all ${
                i === currentIndex
                  ? "bg-purple-500 scale-125"
                  : "bg-white/30 hover:bg-white/50"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

### Step 9: Deck Page

**9.1 Create the deck page `frontend/src/app/deck/[deckId]/page.tsx`:**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDeck, DeckResponse, APIClientError } from "@/lib/api";
import { DeckSwiper } from "@/components/flashcards/DeckSwiper";

export default function DeckPage() {
  const params = useParams();
  const router = useRouter();
  const deckId = params.deckId as string;

  const [deck, setDeck] = useState<DeckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDeck() {
      try {
        const data = await getDeck(deckId);
        setDeck(data);
      } catch (err) {
        if (err instanceof APIClientError) {
          setError(err.error.message);
        } else {
          setError("Failed to load deck");
        }
      } finally {
        setLoading(false);
      }
    }

    loadDeck();
  }, [deckId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-purple-200">Loading deck...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!deck) return null;

  return <DeckSwiper deck={deck} />;
}
```

---

### Step 10: Update Home Page

**10.1 Update `frontend/src/app/page.tsx` to call the API:**

Add this import at the top:
```tsx
import { useRouter } from "next/navigation";
import { generateDeck, APIClientError } from "@/lib/api";
```

Update the `handleSubmit` function:
```tsx
const router = useRouter();

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError(null);

  if (!topic.trim()) {
    setError("Please enter a topic");
    return;
  }

  setIsLoading(true);

  try {
    const deck = await generateDeck({
      topic: topic.trim(),
      difficulty_level: difficulty,
    });
    
    // Navigate to deck page
    router.push(`/deck/${deck.deck_id}`);
  } catch (err) {
    if (err instanceof APIClientError) {
      setError(err.error.message);
    } else {
      setError("Failed to generate deck. Please try again.");
    }
    setIsLoading(false);
  }
};
```

---

### Step 11: Testing

**11.1 Run the backend tests:**

```bash
cd backend
pytest -v
```

**11.2 Start the services:**

```bash
cd d:/Projects/ai_flashcards
docker compose up --build
```

**11.3 Test the API directly:**

```bash
# Generate a deck
curl -X POST http://localhost:8000/v1/deck/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python Basics", "difficulty_level": "beginner"}'
```

**11.4 Test via the UI:**

1. Open http://localhost:3000
2. Enter a topic (e.g., "Binary Search Trees")
3. Select difficulty
4. Click "Generate Flashcards"
5. View the generated deck with swipe navigation

---

## Exit Criteria ✅

Before moving to Phase 3, verify:

- [ ] `/v1/deck/generate` returns valid JSON matching the schema
- [ ] Decks are persisted to PostgreSQL
- [ ] `/v1/deck/{deck_id}` retrieves saved decks
- [ ] Frontend generates and displays decks
- [ ] Flashcard UI shows concepts with progressive disclosure
- [ ] Logs include request IDs
- [ ] Error responses match `docs/ERRORS.md` (top-level `error` object)
- [ ] All tests pass

---

## Troubleshooting

### "OPENAI_API_KEY not set"
- Check your `.env` file has the correct key
- Restart Docker Compose after changing `.env`

### Database connection errors
- Ensure PostgreSQL container is healthy: `docker compose ps`
- Run migrations: `alembic upgrade head`

### LLM returns invalid schema
- Check the prompt templates in `registry.py`
- Review the LLM output in logs

---

## Next Steps

Once all exit criteria are met, proceed to **Phase 3: Example Generation (Gated)**.
