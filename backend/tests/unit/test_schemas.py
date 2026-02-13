"""Tests for Pydantic deck schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.deck import (
    Concept,
    DeckGenerateRequest,
    DeckResponse,
    GenerationMetadata,
    LLMConcept,
    LLMDeckOutput,
    Source,
    TokenUsage,
)

# =============================================================================
# DeckGenerateRequest Tests
# =============================================================================


class TestDeckGenerateRequest:
    """Tests for DeckGenerateRequest validation."""

    def test_valid_request_minimal(self) -> None:
        req = DeckGenerateRequest(topic="Binary Search Trees")
        assert req.topic == "Binary Search Trees"
        assert req.difficulty_level == "beginner"
        assert req.max_concepts == 5
        assert req.scope is None

    def test_valid_request_full(self) -> None:
        req = DeckGenerateRequest(
            topic="Binary Search Trees",
            difficulty_level="advanced",
            max_concepts=7,
            scope="Balanced BSTs",
        )
        assert req.difficulty_level == "advanced"
        assert req.max_concepts == 7
        assert req.scope == "Balanced BSTs"

    def test_topic_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="")

    def test_topic_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="x" * 201)

    def test_invalid_difficulty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="Test", difficulty_level="expert")  # type: ignore[arg-type]

    def test_max_concepts_below_minimum(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="Test", max_concepts=2)

    def test_max_concepts_above_maximum(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="Test", max_concepts=8)

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="Test", unknown_field="value")  # type: ignore[call-arg]

    def test_topic_whitespace_normalized(self) -> None:
        req = DeckGenerateRequest(topic="  Binary   Search   Trees  ")
        assert req.topic == "Binary Search Trees"

    def test_scope_whitespace_normalized(self) -> None:
        req = DeckGenerateRequest(
            topic="Trees",
            scope="  Balanced    BSTs  ",
        )
        assert req.scope == "Balanced BSTs"

    def test_topic_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DeckGenerateRequest(topic="   \t   ")


# =============================================================================
# Concept / LLMConcept Tests
# =============================================================================


def _make_bullets(n: int = 5) -> list[str]:
    return [f"Bullet point {i+1}" for i in range(n)]


class TestConcept:
    """Tests for Concept model."""

    def test_valid_concept(self) -> None:
        c = Concept(
            title="Test Concept",
            bullets=_make_bullets(5),
            example_possible=True,
            example_hint="Try this example",
        )
        assert c.title == "Test Concept"
        assert len(c.bullets) == 5
        assert c.example_possible is True
        assert c.card_id is not None

    def test_bullets_fewer_than_5_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Concept(
                title="Test",
                bullets=_make_bullets(4),
                example_possible=False,
            )

    def test_bullets_more_than_5_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Concept(
                title="Test",
                bullets=_make_bullets(6),
                example_possible=False,
            )

    def test_empty_bullet_rejected(self) -> None:
        bullets = _make_bullets(4) + [""]
        with pytest.raises(ValidationError):
            Concept(
                title="Test",
                bullets=bullets,
                example_possible=False,
            )

    def test_title_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Concept(
                title="",
                bullets=_make_bullets(5),
                example_possible=False,
            )


class TestSource:
    """Tests for Source model validation."""

    def test_valid_source_url(self) -> None:
        source = Source(
            source_id="src1",
            resource_id="res1",
            title="Reference",
            url="https://example.com/path",
        )
        assert source.url is not None
        assert str(source.url).startswith("https://example.com")

    def test_invalid_source_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Source(
                source_id="src1",
                resource_id="res1",
                title="Reference",
                url="not-a-uri",
            )


class TestLLMConcept:
    """Tests for LLMConcept model (no card_id)."""

    def test_valid_llm_concept(self) -> None:
        c = LLMConcept(
            title="Test",
            bullets=_make_bullets(5),
            example_possible=True,
            example_hint="Hint",
        )
        assert c.title == "Test"
        assert not hasattr(c, "card_id")


class TestLLMDeckOutput:
    """Tests for LLMDeckOutput validation."""

    def _make_concepts(self, n: int) -> list[LLMConcept]:
        return [
            LLMConcept(
                title=f"Concept {i+1}",
                bullets=_make_bullets(5),
                example_possible=True,
            )
            for i in range(n)
        ]

    def test_valid_output_3_concepts(self) -> None:
        output = LLMDeckOutput(concepts=self._make_concepts(3))
        assert len(output.concepts) == 3

    def test_valid_output_7_concepts(self) -> None:
        output = LLMDeckOutput(concepts=self._make_concepts(7))
        assert len(output.concepts) == 7

    def test_fewer_than_3_concepts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LLMDeckOutput(concepts=self._make_concepts(2))

    def test_more_than_7_concepts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LLMDeckOutput(concepts=self._make_concepts(8))


# =============================================================================
# DeckResponse Tests
# =============================================================================


class TestDeckResponse:
    """Tests for DeckResponse model."""

    def _make_deck_response(self, n_concepts: int = 5) -> DeckResponse:
        concepts = [
            Concept(
                title=f"Concept {i+1}",
                bullets=_make_bullets(5),
                example_possible=True,
            )
            for i in range(n_concepts)
        ]
        return DeckResponse(
            deck_id=uuid4(),
            topic="Binary Search Trees",
            difficulty_level="beginner",
            concepts=concepts,
            generation_metadata=GenerationMetadata(
                model="gpt-4o-mini",
                prompt_version="v1",
                tokens=TokenUsage(prompt=100, completion=200, total=300),
                timestamp="2026-01-01T00:00:00Z",
            ),
        )

    def test_valid_response(self) -> None:
        resp = self._make_deck_response(5)
        assert resp.schema_version == "1.0"
        assert resp.topic == "Binary Search Trees"
        assert len(resp.concepts) == 5

    def test_schema_version_always_1_0(self) -> None:
        resp = self._make_deck_response()
        assert resp.schema_version == "1.0"

    def test_too_few_concepts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._make_deck_response(2)

    def test_too_many_concepts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._make_deck_response(8)

    def test_json_roundtrip(self) -> None:
        resp = self._make_deck_response(5)
        json_str = resp.model_dump_json()
        restored = DeckResponse.model_validate_json(json_str)
        assert restored.deck_id == resp.deck_id
        assert len(restored.concepts) == 5
