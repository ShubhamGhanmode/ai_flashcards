"""Tests for Phase 4 telemetry persistence."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import CardExample, Deck
from app.db.session import get_db
from app.main import app
from app.schemas.deck import (
    Concept,
    DeckResponse,
)
from app.schemas.deck import (
    GenerationMetadata as DeckGenerationMetadata,
)
from app.schemas.deck import (
    TokenUsage as DeckTokenUsage,
)
from app.schemas.example import ExampleGenerateRequest, LLMExampleOutput
from app.services.cost_calculator import CostCalculator
from app.services.example_generator import ExampleGenerator


class _RawMessage:
    """Minimal stub for LangChain raw message objects."""

    def __init__(self, usage_metadata: dict[str, int], content: str) -> None:
        self.usage_metadata = usage_metadata
        self.content = content


def _make_deck_response(deck_id: UUID | None = None) -> DeckResponse:
    if deck_id is None:
        deck_id = uuid4()
    concept = Concept(
        title="Concept",
        bullets=["b1", "b2", "b3", "b4", "b5"],
        example_possible=True,
        example_hint="hint",
    )
    return DeckResponse(
        deck_id=deck_id,
        topic="Binary Search Trees",
        difficulty_level="beginner",
        concepts=[concept, concept, concept],
        generation_metadata=DeckGenerationMetadata(
            model="gpt-5-nano",
            prompt_version="v1",
            tokens=DeckTokenUsage(prompt=120, completion=80, total=200),
            timestamp="2026-01-01T00:00:00Z",
        ),
    )


def test_deck_generation_persists_cost_and_latency(client: TestClient) -> None:
    mock_db = MagicMock()

    def custom_db():
        yield mock_db

    app.dependency_overrides[get_db] = custom_db
    try:
        with patch("app.api.v1.routes_deck.get_llm_client") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.generate_deck = AsyncMock(return_value=_make_deck_response())
            mock_get_llm.return_value = mock_llm

            response = client.post(
                "/v1/deck/generate",
                json={"topic": "Binary Search Trees"},
            )

        assert response.status_code == 201
        persisted_deck = next(
            call.args[0]
            for call in mock_db.add.call_args_list
            if isinstance(call.args[0], Deck)
        )
        assert persisted_deck.tokens_used == 200
        assert persisted_deck.generation_time_ms is not None
        assert persisted_deck.generation_time_ms >= 0
        expected_cents = CostCalculator.cost_to_cents(
            CostCalculator.estimate_cost_usd("gpt-5-nano", 120, 80)
        )
        assert persisted_deck.api_cost_cents == expected_cents
        assert persisted_deck.api_cost_usd == pytest.approx(
            CostCalculator.estimate_cost_usd("gpt-5-nano", 120, 80)
        )
    finally:
        app.dependency_overrides.clear()


@patch("app.services.example_generator.ChatOpenAI")
@pytest.mark.asyncio
async def test_example_generation_persists_cost_and_latency(
    mock_chat_openai: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value={
            "parsed": LLMExampleOutput(
                example="Example text",
                steps=["s1"],
                pitfalls=["p1"],
            ),
            "raw": _RawMessage(
                usage_metadata={"input_tokens": 11, "output_tokens": 19, "total_tokens": 30},
                content='{"example":"Example text"}',
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

    query_card = MagicMock()
    query_card.filter.return_value.first.return_value = card

    query_cached = MagicMock()
    query_cached.filter.return_value.first.return_value = None

    db = MagicMock()
    db.query.side_effect = [query_card, query_cached]

    _, from_cache = await generator.generate_or_get_example(
        card_id=card_id,
        request=ExampleGenerateRequest(),
        db=db,
    )

    assert from_cache is False
    added_row = db.add.call_args.args[0]
    assert isinstance(added_row, CardExample)
    assert added_row.tokens_used == 30
    assert added_row.generation_time_ms is not None
    assert added_row.generation_time_ms >= 0
    expected_cents = CostCalculator.cost_to_cents(
        CostCalculator.estimate_cost_usd("gpt-5-nano", 11, 19)
    )
    assert added_row.api_cost_cents == expected_cents
    assert added_row.api_cost_usd == pytest.approx(
        CostCalculator.estimate_cost_usd("gpt-5-nano", 11, 19)
    )
