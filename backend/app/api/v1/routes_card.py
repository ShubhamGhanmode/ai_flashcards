"""Card example generation endpoints."""

from typing import Annotated, Any
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Body, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.request_id import request_id_var
from app.schemas.example import ExampleGenerateRequest, ExampleResponse
from app.services.circuit_breaker import CircuitBreakerOpenError
from app.services.example_generator import (
    CardNotFoundError,
    ExampleNotAllowedError,
    ExampleSchemaValidationFailedError,
    get_example_generator,
)

router = APIRouter()
logger = structlog.get_logger()


def error_response(
    *,
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
    "/{card_id}/example",
    response_model=ExampleResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    summary="Generate or fetch a card example",
    description="Generate an example for a card when example generation is allowed.",
)
async def generate_card_example(
    card_id: UUID,
    response: Response,
    request: Annotated[
        ExampleGenerateRequest,
        Body(default_factory=ExampleGenerateRequest),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> ExampleResponse | JSONResponse:
    """Generate or fetch a cached example for a card."""
    logger.info("card_example_requested", card_id=str(card_id))

    try:
        generator = get_example_generator()
        example, from_cache = await generator.generate_or_get_example(
            card_id=card_id,
            request=request,
            db=db,
        )
        if from_cache:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_201_CREATED
        return example

    except CardNotFoundError:
        return error_response(
            code="NOT_FOUND",
            message=f"Card {card_id} not found",
            retryable=False,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"card_id": str(card_id)},
            recovery_action="Verify the card ID and try again.",
        )
    except ExampleNotAllowedError:
        return error_response(
            code="INVALID_INPUT",
            message="Examples are not allowed for this card.",
            retryable=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "validation_errors": [
                    {
                        "field": "card_id",
                        "message": "Card has example_possible=false.",
                        "type": "invalid_state",
                    }
                ]
            },
            recovery_action="Choose a card marked as example available.",
        )
    except ExampleSchemaValidationFailedError as exc:
        return error_response(
            code="SCHEMA_VALIDATION_FAILED",
            message="Example output failed schema validation.",
            retryable=False,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=exc.details or None,
            recovery_action="Retry with shorter constraints or style=default.",
        )
    except CircuitBreakerOpenError as exc:
        return error_response(
            code="CIRCUIT_BREAKER_OPEN",
            message="The generation service is recovering. Please retry shortly.",
            retryable=True,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"retry_after_seconds": exc.retry_after_seconds},
            recovery_action="Retry after the suggested cooldown window.",
        )
    except (httpx.TimeoutException, TimeoutError) as exc:
        logger.warning(
            "card_example_generation_timeout",
            card_id=str(card_id),
            error=str(exc),
        )
        return error_response(
            code="LLM_TIMEOUT",
            message="Example generation timed out.",
            retryable=True,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            recovery_action="Retry in a few seconds.",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "card_example_persist_failed",
            card_id=str(card_id),
            error=str(exc),
        )
        return error_response(
            code="INTERNAL_ERROR",
            message="Failed to persist card example.",
            retryable=True,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            recovery_action="Retry the request. If this continues, contact support.",
        )
    except Exception as exc:
        db.rollback()
        logger.error(
            "card_example_generation_failed",
            card_id=str(card_id),
            error=str(exc),
        )
        return error_response(
            code="LLM_PROVIDER_ERROR",
            message="Failed to generate card example.",
            retryable=True,
            status_code=status.HTTP_502_BAD_GATEWAY,
            recovery_action="Retry in a few seconds.",
        )
