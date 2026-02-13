"""API v1 routes package."""

from fastapi import APIRouter

from app.api.v1 import routes_deck, routes_health

router = APIRouter(prefix="/v1")

# Include all v1 routes
router.include_router(routes_health.router, tags=["Health"])
router.include_router(routes_deck.router, prefix="/deck", tags=["Deck"])
