"""Deck generation endpoints."""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Annotated, Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Card, Deck
from app.db.session import get_db
from app.middleware.request_id import request_id_var
from app.prompts.registry import get_deck_prompts
from app.schemas.deck import (
    DeckEstimateRequest,
    DeckEstimateResponse,
    DeckGenerateRequest,
    DeckResponse,
    TokenUsage,
)
from app.services.circuit_breaker import CircuitBreakerOpenError
from app.services.cost_calculator import CostCalculator
from app.services.llm_client import SchemaValidationFailedError, get_llm_client
from app.services.token_estimator import TokenEstimator

router = APIRouter()
logger = structlog.get_logger()

DEFAULT_MODEL = "gpt-5-nano"
STREAM_STAGE_TOTAL = 3


def build_error_payload(
    code: str,
    message: str,
    retryable: bool,
    details: dict[str, Any] | None = None,
    recovery_action: str | None = None,
) -> dict[str, Any]:
    """Build a standardized error payload."""
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

    return payload


def error_response(
    code: str,
    message: str,
    retryable: bool,
    status_code: int,
    details: dict[str, Any] | None = None,
    recovery_action: str | None = None,
) -> JSONResponse:
    """Build a standardized error response payload."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": build_error_payload(
                code=code,
                message=message,
                retryable=retryable,
                details=details,
                recovery_action=recovery_action,
            )
        },
    )


def _estimate_duration_seconds(total_tokens: int) -> float:
    """Estimate request duration from total token count."""
    estimated_seconds = total_tokens / 220
    return round(max(0.5, estimated_seconds), 1)


def _estimate_generation_seconds(request: DeckGenerateRequest) -> float:
    """Estimate how long a deck request will take."""
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    system_prompt, user_prompt = get_deck_prompts(
        topic=request.topic,
        difficulty_level=request.difficulty_level,
        max_concepts=request.max_concepts,
        scope=request.scope,
    )
    estimator = TokenEstimator(model=model)
    estimated_tokens = estimator.estimate_deck_request(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_concepts=request.max_concepts,
    )
    return _estimate_duration_seconds(estimated_tokens["total"])


def _stream_event(event: str, payload: dict[str, Any]) -> str:
    """Serialize an SSE event payload."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"


async def _generate_deck_response(
    request: DeckGenerateRequest,
    deck_id: UUID,
) -> tuple[DeckResponse, int, float]:
    """Generate a deck and return response plus telemetry."""
    llm_client = get_llm_client()
    generation_start = perf_counter()
    response = await llm_client.generate_deck(request, deck_id)
    generation_time_ms = int((perf_counter() - generation_start) * 1000)
    tokens = response.generation_metadata.tokens
    cost_usd = CostCalculator.estimate_cost_usd(
        response.generation_metadata.model,
        tokens.prompt,
        tokens.completion,
    )
    return response, generation_time_ms, cost_usd


def _persist_deck_response(
    *,
    db: Session,
    request: DeckGenerateRequest,
    deck_id: UUID,
    response: DeckResponse,
    generation_time_ms: int,
    cost_usd: float,
) -> None:
    """Persist a generated deck and its cards."""
    deck = Deck(
        deck_id=deck_id,
        topic=request.topic,
        difficulty_level=request.difficulty_level,
        scope=request.scope,
        payload=response.model_dump(mode="json"),
        tokens_used=response.generation_metadata.tokens.total,
        api_cost_cents=CostCalculator.cost_to_cents(cost_usd),
        api_cost_usd=cost_usd,
        generation_time_ms=generation_time_ms,
    )
    db.add(deck)

    for concept in response.concepts:
        card = Card(
            card_id=concept.card_id,
            deck_id=deck_id,
            title=concept.title,
            payload=concept.model_dump(mode="json"),
        )
        db.add(card)

    db.commit()


def _stream_status_payload(
    *,
    phase: str,
    message: str,
    stage_index: int,
    elapsed_seconds: float,
    estimated_seconds: float,
) -> dict[str, Any]:
    """Build a status or heartbeat payload for the generation stream."""
    return {
        "phase": phase,
        "message": message,
        "stage_index": stage_index,
        "stage_total": STREAM_STAGE_TOTAL,
        "elapsed_seconds": elapsed_seconds,
        "estimated_seconds": estimated_seconds,
        "request_id": request_id_var.get(),
    }


@router.post(
    "/estimate",
    response_model=DeckEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate deck generation token and cost usage",
    description="Estimate deck generation usage without calling the LLM provider.",
)
async def estimate_deck(
    request: DeckEstimateRequest,
) -> DeckEstimateResponse:
    """Estimate token usage, latency, and cost for deck generation."""
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    system_prompt, user_prompt = get_deck_prompts(
        topic=request.topic,
        difficulty_level=request.difficulty_level,
        max_concepts=request.max_concepts,
        scope=request.scope,
    )

    estimator = TokenEstimator(model=model)
    estimated_tokens = estimator.estimate_deck_request(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_concepts=request.max_concepts,
    )
    estimated_cost_usd = CostCalculator.estimate_cost_usd(
        model,
        estimated_tokens["prompt"],
        estimated_tokens["completion"],
    )

    return DeckEstimateResponse(
        model=model,
        estimated_tokens=TokenUsage(
            prompt=estimated_tokens["prompt"],
            completion=estimated_tokens["completion"],
            total=estimated_tokens["total"],
        ),
        estimated_cost_usd=estimated_cost_usd,
        estimated_cost_cents=CostCalculator.cost_to_cents(estimated_cost_usd),
        estimated_seconds=_estimate_duration_seconds(estimated_tokens["total"]),
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
        response, generation_time_ms, cost_usd = await _generate_deck_response(
            request,
            deck_id,
        )
        _persist_deck_response(
            db=db,
            request=request,
            deck_id=deck_id,
            response=response,
            generation_time_ms=generation_time_ms,
            cost_usd=cost_usd,
        )

        logger.info(
            "deck_generation_completed",
            deck_id=str(deck_id),
            concepts_count=len(response.concepts),
        )

        return response

    except CircuitBreakerOpenError as exc:
        logger.warning(
            "deck_generation_blocked_circuit_breaker",
            deck_id=str(deck_id),
            retry_after_seconds=exc.retry_after_seconds,
        )
        return error_response(
            code="CIRCUIT_BREAKER_OPEN",
            message="The generation service is recovering. Please retry shortly.",
            retryable=True,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"retry_after_seconds": exc.retry_after_seconds},
            recovery_action="Retry after the suggested cooldown window.",
        )
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


@router.post(
    "/generate/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream deck generation lifecycle events",
    description=(
        "Stream deck generation status updates and the completed deck using "
        "server-sent events over a POST request."
    ),
)
async def stream_generate_deck(
    request: DeckGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Stream deck generation progress and the completed deck payload."""

    deck_id = uuid4()
    estimated_seconds = _estimate_generation_seconds(request)

    logger.info(
        "deck_generation_stream_started",
        deck_id=str(deck_id),
        topic=request.topic,
        estimated_seconds=estimated_seconds,
    )

    async def event_stream() -> AsyncIterator[str]:
        stream_started = perf_counter()
        yield _stream_event(
            "status",
            _stream_status_payload(
                phase="queued",
                message="Shaping the prompt and sequencing the study arc.",
                stage_index=1,
                elapsed_seconds=0.0,
                estimated_seconds=estimated_seconds,
            ),
        )
        yield _stream_event(
            "status",
            _stream_status_payload(
                phase="generating",
                message="Drafting concept cards in structured JSON.",
                stage_index=2,
                elapsed_seconds=0.0,
                estimated_seconds=estimated_seconds,
            ),
        )

        generation_task = asyncio.create_task(
            _generate_deck_response(request, deck_id)
        )

        try:
            while not generation_task.done():
                await asyncio.sleep(0.8)
                if generation_task.done():
                    break
                elapsed_seconds = round(perf_counter() - stream_started, 1)
                yield _stream_event(
                    "heartbeat",
                    _stream_status_payload(
                        phase="generating",
                        message="Drafting concept cards in structured JSON.",
                        stage_index=2,
                        elapsed_seconds=elapsed_seconds,
                        estimated_seconds=estimated_seconds,
                    ),
                )

            response, generation_time_ms, cost_usd = await generation_task

            yield _stream_event(
                "status",
                _stream_status_payload(
                    phase="finalizing",
                    message="Saving cards and preparing the deck view.",
                    stage_index=3,
                    elapsed_seconds=round(perf_counter() - stream_started, 1),
                    estimated_seconds=estimated_seconds,
                ),
            )

            _persist_deck_response(
                db=db,
                request=request,
                deck_id=deck_id,
                response=response,
                generation_time_ms=generation_time_ms,
                cost_usd=cost_usd,
            )

            logger.info(
                "deck_generation_stream_completed",
                deck_id=str(deck_id),
                concepts_count=len(response.concepts),
            )
            yield _stream_event(
                "complete",
                {
                    "deck": response.model_dump(mode="json"),
                    "request_id": request_id_var.get(),
                },
            )
        except CircuitBreakerOpenError as exc:
            logger.warning(
                "deck_generation_stream_blocked_circuit_breaker",
                deck_id=str(deck_id),
                retry_after_seconds=exc.retry_after_seconds,
            )
            yield _stream_event(
                "error",
                {
                    "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "error": build_error_payload(
                        code="CIRCUIT_BREAKER_OPEN",
                        message=(
                            "The generation service is recovering. Please retry "
                            "shortly."
                        ),
                        retryable=True,
                        details={"retry_after_seconds": exc.retry_after_seconds},
                        recovery_action=(
                            "Retry after the suggested cooldown window."
                        ),
                    ),
                },
            )
        except SchemaValidationFailedError as exc:
            logger.error(
                "deck_generation_stream_schema_validation_failed",
                deck_id=str(deck_id),
                details=exc.details,
            )
            yield _stream_event(
                "error",
                {
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "error": build_error_payload(
                        code="SCHEMA_VALIDATION_FAILED",
                        message="Deck output failed schema validation.",
                        retryable=False,
                        details=exc.details or None,
                        recovery_action=(
                            "Try a narrower topic and regenerate the deck."
                        ),
                    ),
                },
            )
        except ValidationError as exc:
            details = {
                "validation_errors": [
                    {
                        "field": ".".join(str(part) for part in err.get("loc", []))
                        or "response",
                        "message": err.get("msg", "Invalid response field"),
                        "type": err.get("type", "validation_error"),
                    }
                    for err in exc.errors()
                ]
            }
            logger.error(
                "deck_generation_stream_validation_failed",
                deck_id=str(deck_id),
                details=details,
            )
            yield _stream_event(
                "error",
                {
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "error": build_error_payload(
                        code="SCHEMA_VALIDATION_FAILED",
                        message="Deck output failed schema validation.",
                        retryable=False,
                        details=details,
                        recovery_action=(
                            "Try a narrower topic and regenerate the deck."
                        ),
                    ),
                },
            )
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(
                "deck_generation_stream_persist_failed",
                deck_id=str(deck_id),
                error=str(exc),
            )
            yield _stream_event(
                "error",
                {
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": build_error_payload(
                        code="INTERNAL_ERROR",
                        message="Failed to persist deck.",
                        retryable=True,
                        recovery_action=(
                            "Retry the request. If this continues, contact support."
                        ),
                    ),
                },
            )
        except Exception as exc:
            db.rollback()
            logger.error(
                "deck_generation_stream_failed",
                deck_id=str(deck_id),
                error=str(exc),
            )
            yield _stream_event(
                "error",
                {
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "error": build_error_payload(
                        code="LLM_PROVIDER_ERROR",
                        message="Failed to generate deck",
                        retryable=True,
                        recovery_action="Retry in a few seconds.",
                    ),
                },
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
