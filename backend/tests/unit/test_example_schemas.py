"""Tests for Pydantic example schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.example import (
    ExampleGenerateRequest,
    ExampleResponse,
    GenerationMetadata,
    LLMExampleOutput,
    TokenUsage,
)


class TestExampleGenerateRequest:
    """Tests for example generation request validation."""

    def test_valid_request_defaults(self) -> None:
        request = ExampleGenerateRequest()
        assert request.style == "default"
        assert request.length == "medium"
        assert request.constraints is None

    def test_constraints_max_items(self) -> None:
        with pytest.raises(ValidationError):
            ExampleGenerateRequest(constraints=[f"c{i}" for i in range(11)])


class TestExampleResponse:
    """Tests for example response validation."""

    def test_valid_response(self) -> None:
        response = ExampleResponse(
            card_id=uuid4(),
            example="Example text",
            steps=["Step one", "Step two"],
            pitfalls=["Pitfall one"],
            source_refs=["src_1"],
            generation_metadata=GenerationMetadata(
                model="gpt-4o-mini",
                prompt_version="v1",
                tokens=TokenUsage(prompt=1, completion=2, total=3),
                timestamp="2026-01-01T00:00:00Z",
                rag_used=False,
            ),
        )
        assert response.schema_version == "1.0"
        assert response.example == "Example text"

    def test_example_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExampleResponse(
                card_id=uuid4(),
                example="x" * 2001,
                generation_metadata=GenerationMetadata(
                    model="gpt-4o-mini",
                    prompt_version="v1",
                    tokens=TokenUsage(prompt=1, completion=2, total=3),
                    timestamp="2026-01-01T00:00:00Z",
                    rag_used=False,
                ),
            )


class TestLLMExampleOutput:
    """Tests for structured example output model."""

    def test_valid_llm_output(self) -> None:
        output = LLMExampleOutput(
            example="Example",
            steps=["s1"],
            pitfalls=["p1"],
            source_refs=["src_1"],
        )
        assert output.example == "Example"
