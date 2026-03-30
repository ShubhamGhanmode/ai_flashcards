"""Tests for circuit breaker state transitions."""

import app.services.circuit_breaker as circuit_breaker_module
from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    get_circuit_breaker,
    reset_circuit_breaker,
)


def test_circuit_breaker_opens_after_failure_threshold(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(circuit_breaker_module.time, "monotonic", lambda: now[0])
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=2,
            failure_window_seconds=60,
            open_duration_seconds=30,
        )
    )

    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is False


def test_half_open_allows_single_probe_then_closes_on_success(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(circuit_breaker_module.time, "monotonic", lambda: now[0])
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=1,
            failure_window_seconds=60,
            open_duration_seconds=30,
        )
    )

    breaker.record_failure()
    assert breaker.allow_request() is False

    now[0] = 131.0
    assert breaker.allow_request() is True
    assert breaker.allow_request() is False

    breaker.record_success()
    assert breaker.allow_request() is True


def test_half_open_probe_failure_reopens_circuit(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(circuit_breaker_module.time, "monotonic", lambda: now[0])
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=1,
            failure_window_seconds=60,
            open_duration_seconds=30,
        )
    )

    breaker.record_failure()
    now[0] = 131.0
    assert breaker.allow_request() is True
    breaker.record_failure()

    assert breaker.allow_request() is False
    assert breaker.retry_after_seconds() > 0


def test_reset_circuit_breaker_clears_singleton() -> None:
    reset_circuit_breaker()
    first = get_circuit_breaker()
    reset_circuit_breaker()
    second = get_circuit_breaker()

    assert first is not second
