"""Redis-backed request rate limits and deck quotas."""

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.middleware.request_id import request_id_var

logger = structlog.get_logger()

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
EXCLUDED_PATHS = {"/health", "/v1/health", "/docs", "/redoc", "/openapi.json"}
DECK_GENERATE_PATHS = {"/v1/deck/generate", "/v1/deck/generate/stream"}


def _parse_positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply hourly request rate limit and daily deck quota."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.requests_per_hour = _parse_positive_int(
            os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR"),
            30,
        )
        self.decks_per_day = _parse_positive_int(
            os.getenv("RATE_LIMIT_DECKS_PER_DAY"),
            10,
        )
        self._redis_client: redis.Redis | None = None

    def _redis(self) -> redis.Redis:
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis_client

    @staticmethod
    def _current_hour_window(now: datetime) -> tuple[str, int]:
        bucket = now.strftime("%Y%m%d%H")
        window_end = (now + timedelta(hours=1)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        ttl = max(1, int((window_end - now).total_seconds()))
        return bucket, ttl

    @staticmethod
    def _current_day_window(now: datetime) -> tuple[str, int]:
        bucket = now.strftime("%Y%m%d")
        window_end = (now + timedelta(days=1)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        ttl = max(1, int((window_end - now).total_seconds()))
        return bucket, ttl

    @staticmethod
    def _client_identifier(request: Request) -> str:
        state_user_id = getattr(request.state, "user_id", None)
        if isinstance(state_user_id, str) and state_user_id.strip():
            return f"user:{state_user_id.strip()}"

        header_user_id = request.headers.get("X-User-ID")
        if header_user_id and header_user_id.strip():
            return f"user:{header_user_id.strip()}"

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip:
                return f"ip:{client_ip}"

        fallback_ip = request.client.host if request.client else "unknown"
        return f"ip:{fallback_ip}"

    @staticmethod
    async def _increment_counter(
        redis_client: redis.Redis,
        key: str,
        ttl_seconds: int,
    ) -> tuple[int, int]:
        count = int(await redis_client.incr(key))
        if count == 1:
            expire_applied = await redis_client.expire(key, ttl_seconds)
            if not expire_applied:
                raise RedisError(f"failed to apply TTL to key: {key}")

        ttl_remaining = int(await redis_client.ttl(key))
        if ttl_remaining <= 0:
            expire_applied = await redis_client.expire(key, ttl_seconds)
            if not expire_applied:
                raise RedisError(f"failed to repair TTL for key: {key}")
            ttl_remaining = int(await redis_client.ttl(key))
            if ttl_remaining <= 0:
                raise RedisError(f"invalid TTL for key after repair: {key}")
        return count, ttl_remaining

    @staticmethod
    def _error_response(
        *,
        code: str,
        message: str,
        retryable: bool,
        retry_after_seconds: int | None = None,
    ) -> JSONResponse:
        payload: dict[str, Any] = {
            "code": code,
            "message": message,
            "request_id": request_id_var.get(),
            "retryable": retryable,
        }
        if retry_after_seconds is not None:
            payload["details"] = {"retry_after_seconds": retry_after_seconds}

        response = JSONResponse(
            status_code=429,
            content={"error": payload},
        )
        if retry_after_seconds is not None:
            response.headers["Retry-After"] = str(retry_after_seconds)
        return response

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in EXCLUDED_PATHS or request.method not in MUTATING_METHODS:
            return await call_next(request)

        client = self._client_identifier(request)
        now = datetime.now(UTC)
        redis_client = self._redis()

        try:
            hour_bucket, hour_ttl = self._current_hour_window(now)
            hourly_key = f"rl:hour:{client}:{hour_bucket}"
            hourly_count, hourly_retry = await self._increment_counter(
                redis_client,
                hourly_key,
                hour_ttl,
            )
            if hourly_count > self.requests_per_hour:
                return self._error_response(
                    code="RATE_LIMITED",
                    message="Hourly request limit exceeded. Try again later.",
                    retryable=True,
                    retry_after_seconds=hourly_retry,
                )

            if request.url.path in DECK_GENERATE_PATHS and request.method == "POST":
                day_bucket, day_ttl = self._current_day_window(now)
                deck_quota_key = f"quota:deck:{client}:{day_bucket}"
                deck_count, _ = await self._increment_counter(
                    redis_client,
                    deck_quota_key,
                    day_ttl,
                )
                if deck_count > self.decks_per_day:
                    return self._error_response(
                        code="QUOTA_EXCEEDED",
                        message="Daily deck quota reached. Try again tomorrow.",
                        retryable=False,
                    )
        except RedisError as exc:
            logger.warning(
                "rate_limit_fail_open",
                path=request.url.path,
                request_id=request_id_var.get(),
                error=str(exc),
            )

        return await call_next(request)
