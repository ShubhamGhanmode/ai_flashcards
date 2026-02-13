"""LangChain LLM client with structured output support."""

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.prompts.registry import PROMPT_VERSIONS, get_deck_prompts
from app.schemas.deck import (
    Concept,
    DeckGenerateRequest,
    DeckResponse,
    GenerationMetadata,
    LLMDeckOutput,
    TokenUsage,
)

logger = structlog.get_logger()

# Configuration
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT = 60


class SchemaValidationFailedError(Exception):
    """Raised when LLM output fails schema validation after one repair pass."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}


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

        # Create structured output chain with include_raw=True
        # so we can access AIMessage.usage_metadata for real token counts
        self.structured_llm = self.llm.with_structured_output(
            LLMDeckOutput, include_raw=True
        )
        self.model = model_name

    @staticmethod
    def _token_usage_from_raw(raw_message: Any) -> TokenUsage:
        """Extract token usage from the raw LangChain response message."""
        usage = getattr(raw_message, "usage_metadata", None) or {}
        return TokenUsage(
            prompt=int(usage.get("input_tokens", 0)),
            completion=int(usage.get("output_tokens", 0)),
            total=int(usage.get("total_tokens", 0)),
        )

    @staticmethod
    def _combine_tokens(first: TokenUsage, second: TokenUsage) -> TokenUsage:
        """Add token counts from two calls."""
        return TokenUsage(
            prompt=first.prompt + second.prompt,
            completion=first.completion + second.completion,
            total=first.total + second.total,
        )

    @staticmethod
    def _as_text(value: Any, max_chars: int = 1600) -> str:
        """Convert unknown payloads to truncated text for logging/details."""
        if value is None:
            return ""
        if isinstance(value, str):
            text = value
        else:
            try:
                text = json.dumps(value, ensure_ascii=True)
            except TypeError:
                text = str(value)
        return text[:max_chars]

    async def _invoke_structured(
        self, messages: list[tuple[str, str]]
    ) -> tuple[LLMDeckOutput | None, Any, Exception | None]:
        """Invoke structured output and return parsed payload with raw response."""
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
    ) -> tuple[LLMDeckOutput | None, Any, Exception | None]:
        """Perform one schema repair call."""
        schema_json = json.dumps(LLMDeckOutput.model_json_schema(), ensure_ascii=True)
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

        start_time = datetime.now(UTC)

        try:
            messages: list[tuple[str, str]] = [
                ("system", system_prompt),
                ("human", user_prompt),
            ]

            llm_output, raw_message, parsing_error = await self._invoke_structured(messages)
            actual_tokens = self._token_usage_from_raw(raw_message)

            if llm_output is None or parsing_error is not None:
                logger.warning(
                    "llm_output_needs_repair",
                    parsing_error=self._as_text(parsing_error),
                    has_raw_response=raw_message is not None,
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
                                "message": "Deck output failed schema validation after repair attempt.",
                                "type": "schema_validation_failed",
                            }
                        ],
                        "parsing_error": self._as_text(parsing_error),
                        "repair_error": self._as_text(repair_error),
                    }
                    logger.error(
                        "llm_output_validation_failed_after_repair",
                        details=details,
                    )
                    raise SchemaValidationFailedError(
                        "Deck output failed schema validation.",
                        details=details,
                    )

                llm_output = repaired_output
                logger.info("llm_output_repair_succeeded")

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
                scope=request.scope,
                concepts=concepts,
                generation_metadata=GenerationMetadata(
                    model=self.model,
                    prompt_version=PROMPT_VERSIONS["deck_system"],
                    tokens=actual_tokens,
                    timestamp=start_time,
                    rag_used=False,
                ),
            )

            logger.info(
                "llm_call_completed",
                model=self.model,
                concepts_count=len(concepts),
                tokens_prompt=actual_tokens.prompt,
                tokens_completion=actual_tokens.completion,
                tokens_total=actual_tokens.total,
            )

            return response

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
            logger.error("llm_output_validation_failed", details=details)
            raise SchemaValidationFailedError(
                "Deck output failed schema validation.",
                details=details,
            ) from e
        except SchemaValidationFailedError:
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
