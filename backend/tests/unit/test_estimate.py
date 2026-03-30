"""Tests for POST /v1/deck/estimate."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.v1.routes_deck import _estimate_duration_seconds


class TestEstimateDeck:
    """Tests for deck estimate endpoint behavior."""

    @patch("app.api.v1.routes_deck.get_llm_client")
    def test_estimate_success_without_openai_key(
        self,
        mock_get_llm_client: MagicMock,
        client: TestClient,
        monkeypatch,
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        response = client.post(
            "/v1/deck/estimate",
            json={
                "topic": "Binary Search Trees",
                "difficulty_level": "beginner",
                "max_concepts": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["schema_version"] == "1.0"
        assert data["estimated_tokens"]["total"] > 0
        assert data["estimated_cost_usd"] >= 0
        assert data["estimated_seconds"] > 0
        mock_get_llm_client.assert_not_called()

    def test_estimate_invalid_input_returns_400(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/v1/deck/estimate",
            json={
                "topic": "",
                "difficulty_level": "beginner",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "validation_errors" in data["error"]["details"]


def test_estimate_duration_seconds_floor_and_rounding() -> None:
    assert _estimate_duration_seconds(0) == 0.5
    assert _estimate_duration_seconds(109) == 0.5
    assert _estimate_duration_seconds(333) == 1.5
