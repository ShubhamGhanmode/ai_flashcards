"""Tests for card example routes."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.schemas.example import ExampleResponse, GenerationMetadata, TokenUsage
from app.services.example_generator import (
    CardNotFoundError,
    ExampleNotAllowedError,
    ExampleSchemaValidationFailedError,
)


def _make_example_response(card_id: UUID) -> ExampleResponse:
    return ExampleResponse(
        card_id=card_id,
        example="Use a real-world filing system analogy for lookup speed.",
        steps=["Check root", "Move left or right", "Repeat until found"],
        pitfalls=["Do not assume tree is balanced"],
        generation_metadata=GenerationMetadata(
            model="gpt-4o-mini",
            prompt_version="v1",
            tokens=TokenUsage(prompt=12, completion=24, total=36),
            timestamp="2026-01-01T00:00:00Z",
            rag_used=False,
        ),
    )


def _mock_db_session():
    """Create a mock DB session for dependency override."""
    mock_db = MagicMock()
    yield mock_db


@pytest.fixture(autouse=True)
def override_db():
    """Override DB dependency for all tests in this module."""
    app.dependency_overrides[get_db] = _mock_db_session
    yield
    app.dependency_overrides.clear()


class TestGenerateCardExample:
    """Tests for POST /v1/card/{card_id}/example."""

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_created_returns_201(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(
            return_value=(_make_example_response(card_id), False)
        )
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example")

        assert response.status_code == 201
        data = response.json()
        assert data["card_id"] == str(card_id)
        assert data["schema_version"] == "1.0"
        assert "X-Request-ID" in response.headers

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_cache_hit_returns_200(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(
            return_value=(_make_example_response(card_id), True)
        )
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["card_id"] == str(card_id)
        assert "X-Request-ID" in response.headers

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_card_not_found_returns_404(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(side_effect=CardNotFoundError(card_id))
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example", json={})

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["details"]["card_id"] == str(card_id)

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_not_allowed_returns_400(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(
            side_effect=ExampleNotAllowedError(card_id)
        )
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example", json={})

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "validation_errors" in data["error"]["details"]

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_schema_failure_returns_502(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(
            side_effect=ExampleSchemaValidationFailedError(
                "Example output failed schema validation.",
                details={
                    "validation_errors": [
                        {
                            "field": "response",
                            "message": "Invalid example payload",
                            "type": "schema_validation_failed",
                        }
                    ]
                },
            )
        )
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example", json={})

        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "SCHEMA_VALIDATION_FAILED"
        assert "validation_errors" in data["error"]["details"]

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_llm_error_returns_502(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(side_effect=RuntimeError("LLM failure"))
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example", json={})

        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "LLM_PROVIDER_ERROR"
        assert data["error"]["retryable"] is True

    @patch("app.api.v1.routes_card.get_example_generator")
    def test_generate_example_timeout_returns_504(
        self,
        mock_get_generator: MagicMock,
        client: TestClient,
    ) -> None:
        card_id = uuid4()
        service = MagicMock()
        service.generate_or_get_example = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )
        mock_get_generator.return_value = service

        response = client.post(f"/v1/card/{card_id}/example", json={})

        assert response.status_code == 504
        data = response.json()
        assert data["error"]["code"] == "LLM_TIMEOUT"
        assert data["error"]["retryable"] is True

    def test_generate_example_invalid_uuid_returns_400(
        self,
        client: TestClient,
    ) -> None:
        response = client.post("/v1/card/not-a-uuid/example", json={})
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_generate_example_includes_request_id_header(
        self,
        client: TestClient,
    ) -> None:
        response = client.post("/v1/card/not-a-uuid/example", json={})
        assert "X-Request-ID" in response.headers
