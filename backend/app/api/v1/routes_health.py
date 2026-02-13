"""Versioned health check endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VersionedHealthResponse(BaseModel):
    """Versioned health check response model."""

    status: str
    timestamp: str
    version: str
    api_version: str


@router.get("/health", response_model=VersionedHealthResponse)
async def health_check() -> VersionedHealthResponse:
    """Return API v1 health details."""
    return VersionedHealthResponse(
        status="ok",
        timestamp=datetime.now(UTC).isoformat(),
        version="0.1.0",
        api_version="v1",
    )
