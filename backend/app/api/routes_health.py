"""Health check endpoint for monitoring and load balancer checks."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current health status of the API.
    Used by load balancers and monitoring systems.
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC).isoformat(),
        version="0.1.0",
    )
