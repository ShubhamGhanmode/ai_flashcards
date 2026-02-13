"""Main FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_health import router as health_router
from app.api.v1 import router as v1_router
from app.middleware.request_id import RequestIDMiddleware, request_id_var

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),  # Use JSONRenderer() in production
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    logger.info("application_startup", version="0.1.0")
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Flashcard Learning Assistant API",
        description="Generate flashcard decks from topics with optional RAG",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware - configure origins from environment in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Frontend origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(RequestIDMiddleware)

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(v1_router)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        validation_errors = []
        for err in exc.errors():
            location = ".".join(str(part) for part in err.get("loc", []))
            validation_errors.append(
                {
                    "field": location or "request",
                    "message": err.get("msg", "Invalid value"),
                    "type": err.get("type", "validation_error"),
                }
            )

        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Request validation failed.",
                    "request_id": request_id_var.get(),
                    "retryable": False,
                    "details": {"validation_errors": validation_errors},
                    "recovery_action": "Fix invalid fields and try again.",
                }
            },
        )

    return app


# Create app instance
app = create_app()
