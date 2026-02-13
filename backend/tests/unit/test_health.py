"""Tests for health check endpoint."""

from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    """Test that health check returns ok status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert data["version"] == "0.1.0"


def test_health_check_includes_request_id(client: TestClient) -> None:
    """Test that health check response includes request ID."""
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_versioned_health_check_returns_ok(client: TestClient) -> None:
    """Test that versioned health check returns ok status."""
    response = client.get("/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "v1"
