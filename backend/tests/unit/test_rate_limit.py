"""Tests for Redis-backed rate limiting middleware."""

from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.main import app
from app.middleware.rate_limit import RateLimitMiddleware


class InMemoryRedis:
    """Minimal async Redis stub for counter tests."""

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._counts: dict[str, int] = {}
        self._ttls: dict[str, int] = {}
        self._default_ttl = ttl_seconds

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        self._ttls[key] = ttl_seconds
        return True

    async def ttl(self, key: str) -> int:
        return self._ttls.get(key, self._default_ttl)


class ExpireFailsRedis(InMemoryRedis):
    """Redis stub that always fails EXPIRE calls."""

    async def expire(self, _key: str, _ttl_seconds: int) -> bool:
        return False


class FailingRedis:
    """Redis stub that simulates connectivity failures."""

    async def incr(self, _key: str) -> int:
        raise RedisError("redis unavailable")

    async def expire(self, _key: str, _ttl_seconds: int) -> bool:
        raise RedisError("redis unavailable")

    async def ttl(self, _key: str) -> int:
        raise RedisError("redis unavailable")


def _find_rate_limit_middleware() -> RateLimitMiddleware:
    current = app.middleware_stack
    while current is not None and hasattr(current, "app"):
        if isinstance(current, RateLimitMiddleware):
            return current
        current = current.app
    raise AssertionError("RateLimitMiddleware not found")


def test_hourly_limit_returns_429_with_retry_after(client: TestClient) -> None:
    client.get("/health")
    middleware = _find_rate_limit_middleware()
    original_state = (
        middleware.requests_per_hour,
        middleware.decks_per_day,
        middleware._redis_client,
    )

    try:
        middleware.requests_per_hour = 1
        middleware.decks_per_day = 99
        middleware._redis_client = InMemoryRedis(ttl_seconds=57)

        first = client.post(
            "/v1/deck/estimate",
            json={"topic": "Rate limit smoke"},
        )
        second = client.post(
            "/v1/deck/estimate",
            json={"topic": "Rate limit smoke"},
        )

        assert first.status_code == 200
        assert second.status_code == 429
        data = second.json()
        assert data["error"]["code"] == "RATE_LIMITED"
        retry_after = int(second.headers["Retry-After"])
        assert retry_after > 0
    finally:
        middleware.requests_per_hour = original_state[0]
        middleware.decks_per_day = original_state[1]
        middleware._redis_client = original_state[2]


def test_daily_deck_quota_returns_429(client: TestClient) -> None:
    client.get("/health")
    middleware = _find_rate_limit_middleware()
    original_state = (
        middleware.requests_per_hour,
        middleware.decks_per_day,
        middleware._redis_client,
    )

    try:
        middleware.requests_per_hour = 99
        middleware.decks_per_day = 1
        middleware._redis_client = InMemoryRedis(ttl_seconds=120)

        first = client.post("/v1/deck/generate", json={"topic": ""})
        second = client.post("/v1/deck/generate", json={"topic": ""})

        assert first.status_code == 400
        assert second.status_code == 429
        data = second.json()
        assert data["error"]["code"] == "QUOTA_EXCEEDED"
    finally:
        middleware.requests_per_hour = original_state[0]
        middleware.decks_per_day = original_state[1]
        middleware._redis_client = original_state[2]


def test_daily_deck_quota_applies_to_stream_route(client: TestClient) -> None:
    client.get("/health")
    middleware = _find_rate_limit_middleware()
    original_state = (
        middleware.requests_per_hour,
        middleware.decks_per_day,
        middleware._redis_client,
    )

    try:
        middleware.requests_per_hour = 99
        middleware.decks_per_day = 1
        middleware._redis_client = InMemoryRedis(ttl_seconds=120)

        first = client.post("/v1/deck/generate/stream", json={"topic": ""})
        second = client.post("/v1/deck/generate/stream", json={"topic": ""})

        assert first.status_code == 400
        assert second.status_code == 429
        data = second.json()
        assert data["error"]["code"] == "QUOTA_EXCEEDED"
    finally:
        middleware.requests_per_hour = original_state[0]
        middleware.decks_per_day = original_state[1]
        middleware._redis_client = original_state[2]


def test_redis_unavailable_fails_open(client: TestClient) -> None:
    client.get("/health")
    middleware = _find_rate_limit_middleware()
    original_state = (
        middleware.requests_per_hour,
        middleware.decks_per_day,
        middleware._redis_client,
    )

    try:
        middleware.requests_per_hour = 1
        middleware.decks_per_day = 1
        middleware._redis_client = FailingRedis()

        response = client.post(
            "/v1/deck/estimate",
            json={"topic": "Redis fail-open"},
        )

        assert response.status_code == 200
    finally:
        middleware.requests_per_hour = original_state[0]
        middleware.decks_per_day = original_state[1]
        middleware._redis_client = original_state[2]


def test_expire_failure_fails_open(client: TestClient) -> None:
    client.get("/health")
    middleware = _find_rate_limit_middleware()
    original_state = (
        middleware.requests_per_hour,
        middleware.decks_per_day,
        middleware._redis_client,
    )

    try:
        middleware.requests_per_hour = 1
        middleware.decks_per_day = 1
        middleware._redis_client = ExpireFailsRedis(ttl_seconds=-1)

        first = client.post("/v1/deck/estimate", json={"topic": "TTL failure"})
        second = client.post("/v1/deck/estimate", json={"topic": "TTL failure"})

        assert first.status_code == 200
        assert second.status_code == 200
    finally:
        middleware.requests_per_hour = original_state[0]
        middleware.decks_per_day = original_state[1]
        middleware._redis_client = original_state[2]
