"""Deck generation endpoints."""

from typing import Annotated, Any
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
from app.services.llm_client import SchemaValidationFailedError, get_llm_client

router = APIRouter()
logger = structlog.get_logger()


def error_response(
    code: str,
    message: str,
    retryable: bool,
    status_code: int,
    details: dict[str, Any] | None = None,
    recovery_action: str | None = None,
) -> JSONResponse:
    """Build a standardized error response payload."""
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id_var.get(),
        "retryable": retryable,
    }
    if details is not None:
        payload["details"] = details
    if recovery_action is not None:
        payload["recovery_action"] = recovery_action

    return JSONResponse(
        status_code=status_code,
        content={"error": payload},
    )


@router.post(
    "/generate",
    response_model=DeckResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new flashcard deck",
    description="Generate a deck of flashcard concepts for the given topic.",
)
async def generate_deck(
    request: DeckGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
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
            scope=request.scope,
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

    except SchemaValidationFailedError as e:
        logger.error(
            "deck_generation_schema_validation_failed",
            deck_id=str(deck_id),
            details=e.details,
        )
        return error_response(
            code="SCHEMA_VALIDATION_FAILED",
            message="Deck output failed schema validation.",
            retryable=False,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=e.details or None,
            recovery_action="Try a narrower topic and regenerate the deck.",
        )
    except ValidationError as e:
        details = {
            "validation_errors": [
                {
                    "field": ".".join(str(part) for part in err.get("loc", []))
                    or "response",
                    "message": err.get("msg", "Invalid response field"),
                    "type": err.get("type", "validation_error"),
                }
                for err in e.errors()
            ]
        }
        logger.error(
            "deck_generation_validation_failed",
            deck_id=str(deck_id),
            details=details,
        )
        return error_response(
            code="SCHEMA_VALIDATION_FAILED",
            message="Deck output failed schema validation.",
            retryable=False,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
            recovery_action="Try a narrower topic and regenerate the deck.",
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
            recovery_action="Retry the request. If this continues, contact support.",
        )
    except Exception as e:
        db.rollback()
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
            recovery_action="Retry in a few seconds.",
        )


@router.get(
    "/{deck_id}",
    response_model=DeckResponse,
    response_model_exclude_none=True,
    summary="Get a deck by ID",
    description="Retrieve a previously generated deck.",
)
async def get_deck(
    deck_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DeckResponse | JSONResponse:
    """Get a deck by ID."""

    deck = db.query(Deck).filter(Deck.deck_id == deck_id).first()

    if not deck:
        return error_response(
            code="NOT_FOUND",
            message=f"Deck {deck_id} not found",
            retryable=False,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"deck_id": str(deck_id)},
            recovery_action="Verify the deck ID and try again.",
        )

    return DeckResponse.model_validate(deck.payload)
