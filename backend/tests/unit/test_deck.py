"""Tests for deck generation routes."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.schemas.deck import (
    Concept,
    DeckResponse,
    GenerationMetadata,
    TokenUsage,
)
from app.services.llm_client import SchemaValidationFailedError


def _make_deck_response(deck_id=None, n_concepts=5) -> DeckResponse:
    """Helper to build a DeckResponse for mocking."""
    if deck_id is None:
        deck_id = uuid4()
    concepts = [
        Concept(
            title=f"Concept {i+1}",
            bullets=[f"Bullet {j+1} for concept {i+1}" for j in range(5)],
            example_possible=True,
            example_hint=f"Example hint {i+1}",
        )
        for i in range(n_concepts)
    ]
    return DeckResponse(
        deck_id=deck_id,
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


def _mock_db_session():
    """Create a mock DB session for dependency override."""
    mock_db = MagicMock()
    yield mock_db


@pytest.fixture(autouse=True)
def override_db():
    """Override the DB dependency for all tests in this module."""
    app.dependency_overrides[get_db] = _mock_db_session
    yield
    app.dependency_overrides.clear()


class TestGenerateDeck:
    """Tests for POST /v1/deck/generate."""

    @patch("app.api.v1.routes_deck.get_llm_client")
    def test_generate_deck_success(
        self,
        mock_get_llm: MagicMock,
        client: TestClient,
    ) -> None:
        # Mock LLM client
        mock_response = _make_deck_response()
        mock_llm = MagicMock()
        mock_llm.generate_deck = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/v1/deck/generate",
            json={
                "topic": "Binary Search Trees",
                "difficulty_level": "beginner",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Binary Search Trees"
        assert data["schema_version"] == "1.0"
        assert len(data["concepts"]) == 5
        assert "generation_metadata" in data
        assert "scope" not in data
        assert "sources" not in data

    def test_generate_deck_empty_topic_rejected(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/deck/generate",
            json={"topic": "", "difficulty_level": "beginner"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "validation_errors" in data["error"]["details"]

    def test_generate_deck_invalid_difficulty_rejected(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/deck/generate",
            json={"topic": "Test", "difficulty_level": "expert"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_generate_deck_max_concepts_out_of_range(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/deck/generate",
            json={
                "topic": "Test",
                "difficulty_level": "beginner",
                "max_concepts": 10,
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"

    @patch("app.api.v1.routes_deck.get_llm_client")
    def test_generate_deck_llm_error_returns_502(
        self,
        mock_get_llm: MagicMock,
        client: TestClient,
    ) -> None:
        mock_llm = MagicMock()
        mock_llm.generate_deck = AsyncMock(
            side_effect=RuntimeError("LLM unavailable")
        )
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/v1/deck/generate",
            json={
                "topic": "Binary Search Trees",
                "difficulty_level": "beginner",
            },
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "LLM_PROVIDER_ERROR"
        assert data["error"]["retryable"] is True
        assert data["error"]["recovery_action"] == "Retry in a few seconds."

    @patch("app.api.v1.routes_deck.get_llm_client")
    def test_generate_deck_schema_validation_failed_returns_details(
        self,
        mock_get_llm: MagicMock,
        client: TestClient,
    ) -> None:
        mock_llm = MagicMock()
        mock_llm.generate_deck = AsyncMock(
            side_effect=SchemaValidationFailedError(
                "Deck output failed schema validation.",
                details={
                    "validation_errors": [
                        {
                            "field": "response",
                            "message": "Invalid deck payload",
                            "type": "schema_validation_failed",
                        }
                    ]
                },
            )
        )
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/v1/deck/generate",
            json={
                "topic": "Binary Search Trees",
                "difficulty_level": "beginner",
            },
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "SCHEMA_VALIDATION_FAILED"
        assert "validation_errors" in data["error"]["details"]
        assert (
            data["error"]["recovery_action"]
            == "Try a narrower topic and regenerate the deck."
        )

    @patch("app.api.v1.routes_deck.get_llm_client")
    def test_generate_deck_sanitizes_topic_and_scope_before_llm_call(
        self,
        mock_get_llm: MagicMock,
        client: TestClient,
    ) -> None:
        mock_response = _make_deck_response()
        mock_llm = MagicMock()
        mock_llm.generate_deck = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/v1/deck/generate",
            json={
                "topic": "  Binary   Search Trees  ",
                "difficulty_level": "beginner",
                "scope": "  Balanced   BSTs  ",
            },
        )

        assert response.status_code == 201
        mock_llm.generate_deck.assert_awaited_once()
        call_request = mock_llm.generate_deck.await_args.args[0]
        assert call_request.topic == "Binary Search Trees"
        assert call_request.scope == "Balanced BSTs"

    def test_generate_deck_whitespace_only_topic_rejected(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/deck/generate",
            json={"topic": "   \t  ", "difficulty_level": "beginner"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "validation_errors" in data["error"]["details"]

    def test_generate_deck_includes_request_id(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/deck/generate",
            json={"topic": "", "difficulty_level": "beginner"},
        )
        assert "X-Request-ID" in response.headers


class TestGetDeck:
    """Tests for GET /v1/deck/{deck_id}."""

    def test_get_deck_not_found(
        self,
        client: TestClient,
    ) -> None:
        # The mock DB from override returns MagicMock for query chains,
        # which isn't None, so we need to customize it.
        # We'll use a custom override for this test.
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def custom_db():
            yield mock_db

        app.dependency_overrides[get_db] = custom_db

        deck_id = uuid4()
        response = client.get(f"/v1/deck/{deck_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["details"]["deck_id"] == str(deck_id)
        assert data["error"]["recovery_action"] == "Verify the deck ID and try again."

    def test_get_deck_success(
        self,
        client: TestClient,
    ) -> None:
        mock_response = _make_deck_response()
        payload = mock_response.model_dump(mode="json")

        mock_deck = MagicMock()
        mock_deck.payload = payload

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deck
        )

        def custom_db():
            yield mock_db

        app.dependency_overrides[get_db] = custom_db

        deck_id = mock_response.deck_id
        response = client.get(f"/v1/deck/{deck_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "Binary Search Trees"
        assert data["schema_version"] == "1.0"

    def test_get_deck_invalid_uuid(self, client: TestClient) -> None:
        response = client.get("/v1/deck/not-a-uuid")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"
