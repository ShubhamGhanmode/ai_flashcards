"""Service for gated, cached card example generation."""

import hashlib
import json
import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID

import structlog
from langchain_openai import ChatOpenAI
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Card, CardExample
from app.prompts.registry import PROMPT_VERSIONS, get_example_prompts
from app.schemas.example import (
    ExampleGenerateRequest,
    ExampleResponse,
    GenerationMetadata,
    LLMExampleOutput,
    TokenUsage,
)

logger = structlog.get_logger()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 60
EXAMPLE_TEMPERATURE = 0.7


class CardNotFoundError(Exception):
    """Raised when the requested card ID does not exist."""

    def __init__(self, card_id: UUID) -> None:
        super().__init__(f"Card {card_id} not found")
        self.card_id = card_id


class ExampleNotAllowedError(Exception):
    """Raised when card does not permit example generation."""

    def __init__(self, card_id: UUID) -> None:
        super().__init__(f"Card {card_id} does not allow example generation")
        self.card_id = card_id


class ExampleSchemaValidationFailedError(Exception):
    """Raised when example output fails schema validation after repair."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}


class ExampleGenerator:
    """Generate or return cached examples for a card."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=EXAMPLE_TEMPERATURE,
            timeout=DEFAULT_TIMEOUT,
            max_retries=2,
        )
        self.structured_llm = self.llm.with_structured_output(
            LLMExampleOutput,
            include_raw=True,
        )
        self.model = model_name

    @staticmethod
    def _token_usage_from_raw(raw_message: Any) -> TokenUsage:
        """Extract token usage from a raw LangChain response message."""
        usage = getattr(raw_message, "usage_metadata", None) or {}
        return TokenUsage(
            prompt=int(usage.get("input_tokens", 0)),
            completion=int(usage.get("output_tokens", 0)),
            total=int(usage.get("total_tokens", 0)),
        )

    @staticmethod
    def _combine_tokens(first: TokenUsage, second: TokenUsage) -> TokenUsage:
        """Add token usage from two calls."""
        return TokenUsage(
            prompt=first.prompt + second.prompt,
            completion=first.completion + second.completion,
            total=first.total + second.total,
        )

    @staticmethod
    def _as_text(value: Any, max_chars: int = 1600) -> str:
        """Convert unknown payload values to safely truncated text."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value[:max_chars]
        try:
            return json.dumps(value, ensure_ascii=True)[:max_chars]
        except TypeError:
            return str(value)[:max_chars]

    @staticmethod
    def compute_request_fingerprint(request: ExampleGenerateRequest) -> str:
        """Build deterministic SHA-256 fingerprint for request cache key."""
        fingerprint_payload = {
            "style": request.style,
            "length": request.length,
            "constraints": request.constraints or [],
        }
        payload = json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_card_fields(card: Card) -> tuple[str, list[str], str | None, bool]:
        """Extract generation inputs from persisted card payload."""
        payload = card.payload if isinstance(card.payload, dict) else {}

        title = payload.get("title", card.title)
        if not isinstance(title, str) or not title.strip():
            title = card.title

        bullets_raw = payload.get("bullets")
        bullets = (
            [item for item in bullets_raw if isinstance(item, str) and item.strip()]
            if isinstance(bullets_raw, list)
            else []
        )
        if not bullets:
            bullets = [card.title]

        example_hint = payload.get("example_hint")
        if not isinstance(example_hint, str) or not example_hint.strip():
            example_hint = None

        example_possible = payload.get("example_possible", False) is True

        return title, bullets, example_hint, example_possible

    @staticmethod
    def _get_cached_example(
        *,
        db: Session,
        card_id: UUID,
        request_fingerprint: str,
    ) -> CardExample | None:
        """Lookup a cached example by card and request fingerprint."""
        return (
            db.query(CardExample)
            .filter(
                CardExample.card_id == card_id,
                CardExample.request_fingerprint == request_fingerprint,
            )
            .first()
        )

    async def _invoke_structured(
        self,
        messages: list[tuple[str, str]],
    ) -> tuple[LLMExampleOutput | None, Any, Exception | None]:
        """Invoke structured output chain."""
        result = await self.structured_llm.ainvoke(messages)
        parsed = result.get("parsed")
        raw = result.get("raw")
        parsing_error = result.get("parsing_error")
        return parsed, raw, parsing_error

    async def _repair_once(
        self,
        *,
        base_system_prompt: str,
        base_user_prompt: str,
        raw_output: str,
        parsing_error: str,
    ) -> tuple[LLMExampleOutput | None, Any, Exception | None]:
        """Attempt one schema repair pass for invalid LLM output."""
        schema_json = json.dumps(LLMExampleOutput.model_json_schema(), ensure_ascii=True)
        repair_system_prompt = (
            "You repair invalid JSON payloads to exactly match a schema. "
            "Return JSON only. Do not add markdown or explanations."
        )
        repair_user_prompt = (
            "Repair the following invalid LLM output.\n\n"
            f"Original system prompt:\n{base_system_prompt}\n\n"
            f"Original user prompt:\n{base_user_prompt}\n\n"
            f"Validation/parsing error:\n{parsing_error}\n\n"
            f"Required schema:\n{schema_json}\n\n"
            f"Invalid output to repair:\n{raw_output}"
        )

        return await self._invoke_structured(
            [
                ("system", repair_system_prompt),
                ("human", repair_user_prompt),
            ]
        )

    async def generate_or_get_example(
        self,
        *,
        card_id: UUID,
        request: ExampleGenerateRequest,
        db: Session,
    ) -> tuple[ExampleResponse, bool]:
        """Generate an example or return cached payload for same request."""
        request_fingerprint = self.compute_request_fingerprint(request)

        card = db.query(Card).filter(Card.card_id == card_id).first()
        if card is None:
            raise CardNotFoundError(card_id)

        title, bullets, example_hint, example_possible = self._extract_card_fields(card)
        if not example_possible:
            raise ExampleNotAllowedError(card_id)

        cached_example = self._get_cached_example(
            db=db,
            card_id=card_id,
            request_fingerprint=request_fingerprint,
        )
        if cached_example is not None:
            logger.info(
                "example_cache_hit",
                card_id=str(card_id),
                style=request.style,
                length=request.length,
            )
            return ExampleResponse.model_validate(cached_example.payload), True

        system_prompt, user_prompt = get_example_prompts(
            title=title,
            bullets=bullets,
            example_hint=example_hint,
            style=request.style,
            length=request.length,
            constraints=request.constraints,
        )
        start_time = datetime.now(UTC)

        logger.info(
            "example_generation_started",
            card_id=str(card_id),
            style=request.style,
            length=request.length,
        )

        try:
            llm_output, raw_message, parsing_error = await self._invoke_structured(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ]
            )
            actual_tokens = self._token_usage_from_raw(raw_message)

            if llm_output is None or parsing_error is not None:
                logger.warning(
                    "example_output_needs_repair",
                    card_id=str(card_id),
                    parsing_error=self._as_text(parsing_error),
                )
                repaired_output, repaired_raw, repair_error = await self._repair_once(
                    base_system_prompt=system_prompt,
                    base_user_prompt=user_prompt,
                    raw_output=self._as_text(getattr(raw_message, "content", raw_message)),
                    parsing_error=self._as_text(parsing_error),
                )
                repair_tokens = self._token_usage_from_raw(repaired_raw)
                actual_tokens = self._combine_tokens(actual_tokens, repair_tokens)

                if repaired_output is None or repair_error is not None:
                    details: dict[str, Any] = {
                        "validation_errors": [
                            {
                                "field": "response",
                                "message": "Example output failed schema validation after repair attempt.",
                                "type": "schema_validation_failed",
                            }
                        ],
                        "parsing_error": self._as_text(parsing_error),
                        "repair_error": self._as_text(repair_error),
                    }
                    logger.error(
                        "example_output_validation_failed_after_repair",
                        card_id=str(card_id),
                        details=details,
                    )
                    raise ExampleSchemaValidationFailedError(
                        "Example output failed schema validation.",
                        details=details,
                    )

                llm_output = repaired_output
                logger.info("example_output_repair_succeeded", card_id=str(card_id))

            response = ExampleResponse(
                card_id=card_id,
                example=llm_output.example,
                steps=llm_output.steps,
                pitfalls=llm_output.pitfalls,
                source_refs=llm_output.source_refs,
                generation_metadata=GenerationMetadata(
                    model=self.model,
                    prompt_version=PROMPT_VERSIONS["example_system"],
                    tokens=actual_tokens,
                    timestamp=start_time,
                    rag_used=False,
                ),
            )

            db.add(
                CardExample(
                    card_id=card_id,
                    request_fingerprint=request_fingerprint,
                    style=request.style,
                    length=request.length,
                    constraints=request.constraints,
                    payload=response.model_dump(mode="json"),
                )
            )
            try:
                db.commit()
            except IntegrityError:
                # Concurrent identical requests may race to insert the same unique key.
                db.rollback()
                cached_after_race = self._get_cached_example(
                    db=db,
                    card_id=card_id,
                    request_fingerprint=request_fingerprint,
                )
                if cached_after_race is not None:
                    logger.info(
                        "example_cache_hit_after_integrity_error",
                        card_id=str(card_id),
                        style=request.style,
                        length=request.length,
                    )
                    return ExampleResponse.model_validate(cached_after_race.payload), True
                raise

            logger.info(
                "example_generation_completed",
                card_id=str(card_id),
                tokens_total=actual_tokens.total,
            )

            return response, False

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
                "example_output_validation_failed",
                card_id=str(card_id),
                details=details,
            )
            raise ExampleSchemaValidationFailedError(
                "Example output failed schema validation.",
                details=details,
            ) from exc
        except ExampleSchemaValidationFailedError:
            raise
        except Exception as exc:
            logger.error(
                "example_generation_failed",
                card_id=str(card_id),
                error=str(exc),
            )
            raise


@lru_cache(maxsize=1)
def get_example_generator() -> ExampleGenerator:
    """Get singleton example generator service."""
    return ExampleGenerator()
