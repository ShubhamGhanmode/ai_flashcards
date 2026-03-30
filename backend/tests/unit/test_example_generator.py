"""Tests for ExampleGenerator service behavior."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.schemas.example import (
    ExampleGenerateRequest,
    ExampleResponse,
    GenerationMetadata,
    LLMExampleOutput,
    TokenUsage,
)
from app.services.example_generator import (
    CardNotFoundError,
    ExampleGenerator,
    ExampleNotAllowedError,
    ExampleSchemaValidationFailedError,
)


class _RawMessage:
    """Minimal stub for LangChain raw message objects."""

    def __init__(self, usage_metadata: dict[str, int], content: str) -> None:
        self.usage_metadata = usage_metadata
        self.content = content


def _valid_llm_output() -> LLMExampleOutput:
    return LLMExampleOutput(
        example="Use a sorted contact list as an analogy for BST lookups.",
        steps=["Start with a root value", "Branch left/right by comparison"],
        pitfalls=["Do not confuse balanced and complete trees"],
    )


def _cached_response(card_id: UUID) -> ExampleResponse:
    return ExampleResponse(
        card_id=card_id,
        example="Cached example",
        generation_metadata=GenerationMetadata(
            model="gpt-5-nano",
            prompt_version="v1",
            tokens=TokenUsage(prompt=1, completion=2, total=3),
            timestamp="2026-01-01T00:00:00Z",
            rag_used=False,
        ),
    )


@pytest.fixture
def env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide API key expected by ExampleGenerator constructor."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_request_fingerprint_is_deterministic() -> None:
    request_a = ExampleGenerateRequest(style="default", length="medium")
    request_b = ExampleGenerateRequest(
        style="default",
        length="medium",
        constraints=[],
    )
    request_c = ExampleGenerateRequest(style="analogy", length="medium")

    fingerprint_a = ExampleGenerator.compute_request_fingerprint(request_a)
    fingerprint_b = ExampleGenerator.compute_request_fingerprint(request_b)
    fingerprint_c = ExampleGenerator.compute_request_fingerprint(request_c)

    assert fingerprint_a == fingerprint_b
    assert fingerprint_a != fingerprint_c


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_or_get_example_returns_cached_payload(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock()
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    generator = ExampleGenerator()
    card_id = uuid4()
    card = MagicMock()
    card.payload = {
        "title": "Binary Search Tree",
        "bullets": ["b1", "b2", "b3", "b4", "b5"],
        "example_possible": True,
    }
    card.title = "Binary Search Tree"

    cached = MagicMock()
    cached.payload = _cached_response(card_id).model_dump(mode="json")

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = card

    query_cached = MagicMock()
    query_cached.filter.return_value.first.return_value = cached

    db = MagicMock()
    db.query.side_effect = [query_card, query_cached]

    response, from_cache = await generator.generate_or_get_example(
        card_id=card_id,
        request=ExampleGenerateRequest(),
        db=db,
    )

    assert from_cache is True
    assert response.example == "Cached example"
    assert mock_structured.ainvoke.await_count == 0
    db.add.assert_not_called()
    db.commit.assert_not_called()


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_or_get_example_raises_not_found(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    generator = ExampleGenerator()

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = None

    db = MagicMock()
    db.query.side_effect = [query_card]

    with pytest.raises(CardNotFoundError):
        await generator.generate_or_get_example(
            card_id=uuid4(),
            request=ExampleGenerateRequest(),
            db=db,
        )


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_or_get_example_raises_invalid_input_when_not_allowed(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    generator = ExampleGenerator()
    card = MagicMock()
    card.payload = {
        "title": "Binary Search Tree",
        "bullets": ["b1", "b2", "b3", "b4", "b5"],
        "example_possible": False,
    }
    card.title = "Binary Search Tree"

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = card

    db = MagicMock()
    db.query.side_effect = [query_card]

    with pytest.raises(ExampleNotAllowedError):
        await generator.generate_or_get_example(
            card_id=uuid4(),
            request=ExampleGenerateRequest(),
            db=db,
        )


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_or_get_example_persists_on_cache_miss(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value={
            "parsed": _valid_llm_output(),
            "raw": _RawMessage(
                usage_metadata={"input_tokens": 10, "output_tokens": 15, "total_tokens": 25},
                content='{"example":"text"}',
            ),
            "parsing_error": None,
        }
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    generator = ExampleGenerator()
    card_id = uuid4()
    card = MagicMock()
    card.payload = {
        "title": "Binary Search Tree",
        "bullets": ["b1", "b2", "b3", "b4", "b5"],
        "example_possible": True,
        "example_hint": "Try insertion order [10, 6, 14]",
    }
    card.title = "Binary Search Tree"

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = card

    query_cached = MagicMock()
    query_cached.filter.return_value.first.return_value = None

    db = MagicMock()
    db.query.side_effect = [query_card, query_cached]

    response, from_cache = await generator.generate_or_get_example(
        card_id=card_id,
        request=ExampleGenerateRequest(style="real_world", length="short"),
        db=db,
    )

    assert from_cache is False
    assert "sorted contact list" in response.example
    assert response.generation_metadata.tokens.total == 25
    db.add.assert_called_once()
    db.commit.assert_called_once()


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_or_get_example_returns_cached_row_on_integrity_race(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value={
            "parsed": _valid_llm_output(),
            "raw": _RawMessage(
                usage_metadata={"input_tokens": 6, "output_tokens": 9, "total_tokens": 15},
                content='{"example":"text"}',
            ),
            "parsing_error": None,
        }
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    generator = ExampleGenerator()
    card_id = uuid4()
    card = MagicMock()
    card.payload = {
        "title": "Binary Search Tree",
        "bullets": ["b1", "b2", "b3", "b4", "b5"],
        "example_possible": True,
    }
    card.title = "Binary Search Tree"

    cached = MagicMock()
    cached.payload = _cached_response(card_id).model_dump(mode="json")

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = card

    query_cache_miss = MagicMock()
    query_cache_miss.filter.return_value.first.return_value = None

    query_cache_after_conflict = MagicMock()
    query_cache_after_conflict.filter.return_value.first.return_value = cached

    db = MagicMock()
    db.query.side_effect = [query_card, query_cache_miss, query_cache_after_conflict]
    db.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))

    response, from_cache = await generator.generate_or_get_example(
        card_id=card_id,
        request=ExampleGenerateRequest(),
        db=db,
    )

    assert from_cache is True
    assert response.example == "Cached example"
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_called_once()


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_or_get_example_raises_after_failed_repair(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        side_effect=[
            {
                "parsed": None,
                "raw": _RawMessage(
                    usage_metadata={"input_tokens": 8, "output_tokens": 8, "total_tokens": 16},
                    content="{bad json}",
                ),
                "parsing_error": ValueError("invalid json"),
            },
            {
                "parsed": None,
                "raw": _RawMessage(
                    usage_metadata={"input_tokens": 4, "output_tokens": 4, "total_tokens": 8},
                    content="{still bad json}",
                ),
                "parsing_error": ValueError("still invalid"),
            },
        ]
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    generator = ExampleGenerator()
    card = MagicMock()
    card.payload = {
        "title": "Binary Search Tree",
        "bullets": ["b1", "b2", "b3", "b4", "b5"],
        "example_possible": True,
    }
    card.title = "Binary Search Tree"

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = card

    query_cached = MagicMock()
    query_cached.filter.return_value.first.return_value = None

    db = MagicMock()
    db.query.side_effect = [query_card, query_cached]

    with pytest.raises(ExampleSchemaValidationFailedError):
        await generator.generate_or_get_example(
            card_id=uuid4(),
            request=ExampleGenerateRequest(),
            db=db,
        )

    assert mock_structured.ainvoke.await_count == 2
    db.commit.assert_not_called()
