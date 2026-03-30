"""Process-local circuit breaker for provider-facing LLM calls."""

import os
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from math import ceil
from threading import Lock

import httpx


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker thresholds and window sizes."""

    failure_threshold: int = 5
    failure_window_seconds: int = 60
    open_duration_seconds: int = 30


class CircuitBreakerOpenError(Exception):
    """Raised when a request is blocked by an open circuit breaker."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Circuit breaker is open")
        self.retry_after_seconds = retry_after_seconds


class CircuitBreaker:
    """Thread-safe, process-local circuit breaker."""

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self.config = config
        self._state = "closed"
        self._failures: deque[float] = deque()
        self._opened_at: float | None = None
        self._half_open_probe_in_flight = False
        self._lock = Lock()

    def _trim_failures(self, now: float) -> None:
        cutoff = now - self.config.failure_window_seconds
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()

    def retry_after_seconds(self) -> int:
        """Return seconds until next retry is allowed."""
        with self._lock:
            return self._retry_after_locked()

    def _retry_after_locked(self) -> int:
        now = time.monotonic()
        if self._state == "open" and self._opened_at is not None:
            remaining = self.config.open_duration_seconds - (now - self._opened_at)
            return max(1, ceil(remaining))
        if self._state == "half_open" and self._half_open_probe_in_flight:
            return 1
        return 0

    def allow_request(self) -> bool:
        """Return whether a request may proceed."""
        with self._lock:
            now = time.monotonic()

            if self._state == "open":
                if self._opened_at is None:
                    self._opened_at = now
                elapsed = now - self._opened_at
                if elapsed < self.config.open_duration_seconds:
                    return False
                self._state = "half_open"
                self._half_open_probe_in_flight = False

            if self._state == "half_open":
                if self._half_open_probe_in_flight:
                    return False
                self._half_open_probe_in_flight = True
                return True

            return True

    def record_success(self) -> None:
        """Record a successful provider call."""
        with self._lock:
            self._state = "closed"
            self._opened_at = None
            self._half_open_probe_in_flight = False
            self._failures.clear()

    def record_failure(self) -> None:
        """Record a failed provider call and transition states if needed."""
        with self._lock:
            now = time.monotonic()

            if self._state == "half_open":
                self._state = "open"
                self._opened_at = now
                self._half_open_probe_in_flight = False
                return

            self._trim_failures(now)
            self._failures.append(now)
            if len(self._failures) >= self.config.failure_threshold:
                self._state = "open"
                self._opened_at = now
                self._half_open_probe_in_flight = False


def _status_code_from_exception(error: Exception) -> int | None:
    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    return None


def is_provider_transient_error(error: Exception) -> bool:
    """Return True when an exception should count toward breaker failures."""
    if isinstance(error, (TimeoutError, httpx.TimeoutException, httpx.TransportError)):
        return True

    status_code = _status_code_from_exception(error)
    if status_code == 429 or (status_code is not None and status_code >= 500):
        return True

    name = error.__class__.__name__.lower()
    return any(
        marker in name
        for marker in (
            "ratelimit",
            "timeout",
            "apiconnection",
            "serviceunavailable",
            "internalserver",
            "temporarilyunavailable",
        )
    )


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def load_circuit_breaker_config() -> CircuitBreakerConfig:
    """Build breaker config from environment variables."""
    return CircuitBreakerConfig(
        failure_threshold=_int_env("CIRCUIT_BREAKER_FAILURE_THRESHOLD", 5),
        failure_window_seconds=_int_env("CIRCUIT_BREAKER_FAILURE_WINDOW_SECONDS", 60),
        open_duration_seconds=_int_env("CIRCUIT_BREAKER_OPEN_DURATION_SECONDS", 30),
    )


@lru_cache(maxsize=1)
def get_circuit_breaker() -> CircuitBreaker:
    """Return the process-local circuit breaker singleton."""
    return CircuitBreaker(load_circuit_breaker_config())


def reset_circuit_breaker() -> None:
    """Reset the cached circuit breaker singleton."""
    get_circuit_breaker.cache_clear()
