"""Tests for LLMClient schema repair flow."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.deck import DeckGenerateRequest, LLMConcept, LLMDeckOutput
from app.services.llm_client import LLMClient, SchemaValidationFailedError


class _RawMessage:
    """Minimal stub for LangChain raw message objects."""

    def __init__(self, usage_metadata: dict[str, int], content: str) -> None:
        self.usage_metadata = usage_metadata
        self.content = content


@pytest.fixture
def env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide API key expected by LLMClient constructor."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def _valid_llm_output() -> LLMDeckOutput:
    concept = LLMConcept(
        title="Binary Search Tree",
        bullets=["b1", "b2", "b3", "b4", "b5"],
        example_possible=True,
        example_hint="Try insert/search trace",
    )
    return LLMDeckOutput(concepts=[concept, concept, concept])


@patch("app.services.llm_client.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_deck_uses_single_repair_pass(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        side_effect=[
            {
                "parsed": None,
                "raw": _RawMessage(
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    content="{bad json}",
                ),
                "parsing_error": ValueError("invalid json"),
            },
            {
                "parsed": _valid_llm_output(),
                "raw": _RawMessage(
                    usage_metadata={"input_tokens": 5, "output_tokens": 7, "total_tokens": 12},
                    content="{\"concepts\": []}",
                ),
                "parsing_error": None,
            },
        ]
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    client = LLMClient()
    response = await client.generate_deck(
        DeckGenerateRequest(topic="BST", difficulty_level="beginner", max_concepts=3),
        uuid4(),
    )

    assert mock_structured.ainvoke.await_count == 2
    assert response.generation_metadata.tokens.total == 42
    assert len(response.concepts) == 3


@patch("app.services.llm_client.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_deck_raises_after_failed_repair(
    mock_chat_openai: MagicMock,
    env_api_key: None,
) -> None:
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        side_effect=[
            {
                "parsed": None,
                "raw": _RawMessage(
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    content="{bad json}",
                ),
                "parsing_error": ValueError("invalid json"),
            },
            {
                "parsed": None,
                "raw": _RawMessage(
                    usage_metadata={"input_tokens": 5, "output_tokens": 7, "total_tokens": 12},
                    content="{still bad json}",
                ),
                "parsing_error": ValueError("still invalid"),
            },
        ]
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_chat_openai.return_value = mock_llm

    client = LLMClient()

    with pytest.raises(SchemaValidationFailedError) as exc:
        await client.generate_deck(
            DeckGenerateRequest(topic="BST", difficulty_level="beginner", max_concepts=3),
            uuid4(),
        )

    assert "validation_errors" in exc.value.details
    assert mock_structured.ainvoke.await_count == 2
