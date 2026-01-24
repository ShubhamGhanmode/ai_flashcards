# Phase 1: Repo Setup and Foundations

## Goal
Establish the monorepo structure, base services, and health-checkable skeletons for backend and frontend. By the end of this phase, you'll have a working Docker Compose setup with a FastAPI backend and Next.js frontend, both with proper quality tooling.

**Status**: Phase 1 complete (repo audit on 2026-01-24).

---

## Prerequisites

Before starting, ensure you have these installed on your machine:

| Tool | Version | How to Check | Installation |
|------|---------|--------------|--------------|
| **Git** | 2.40+ | `git --version` | [git-scm.com](https://git-scm.com/) |
| **Docker Desktop** | 4.25+ | `docker --version` | [docker.com/desktop](https://www.docker.com/products/docker-desktop/) |
| **Python** | 3.11+ | `python --version` | [python.org](https://www.python.org/downloads/) or use `pyenv` |
| **Node.js** | 20 LTS | `node --version` | [nodejs.org](https://nodejs.org/) or use `nvm` |
| **VS Code** (recommended) | Latest | - | [code.visualstudio.com](https://code.visualstudio.com/) |

### Also Required
- **OpenAI API Key**: Get one from [platform.openai.com](https://platform.openai.com/api-keys)
- **Phase 0 artifacts reviewed**: Ensure you've read through `PLAN.md` and all `docs/` files

---

## Version Specifications

Use these exact versions for consistency:

| Tool/Dependency | Version | Notes |
|-----------------|---------|-------|
| Python | 3.11+ | Use `pyenv` or Docker base image |
| Node.js | 20 LTS | Use `nvm` or Docker base image |
| FastAPI | 0.110+ | Latest stable |
| Next.js | 16+ | App Router |
| React | 19+ | Required by Next.js 16+ |
| PostgreSQL | 16 | Docker image |
| Redis | 7 | Docker image |
| Docker Compose | v2 | Use `docker compose` (not `docker-compose`) |

---

## Deliverables Checklist

By the end of Phase 1, you should have:

- [ ] `backend/` and `frontend/` project scaffolds
- [ ] Dockerfiles and `docker-compose.yml`
- [ ] `.env.example` with required variables
- [ ] FastAPI `/health` endpoint returning `{"status": "ok"}`
- [ ] Next.js homepage with topic input form
- [ ] Linting, formatting, and pre-commit hooks configured
- [ ] Testing framework scaffolds (pytest, Jest)
- [ ] Everything running via `docker compose up`

---

## Detailed Steps

### Step 1: Create Repository Structure

**1.1 Create the project directories:**

```bash
# Navigate to your projects folder
cd d:/Projects/ai_flashcards

# Create main directories
mkdir -p backend/app/api
mkdir -p backend/app/services
mkdir -p backend/app/db
mkdir -p backend/app/prompts
mkdir -p backend/app/schemas
mkdir -p backend/app/middleware
mkdir -p backend/app/utils
mkdir -p backend/tests/unit
mkdir -p backend/tests/integration
mkdir -p frontend
```

**1.2 Create the `.gitignore` file:**

Create a file at the project root called `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
ENV/
.eggs/
*.egg-info/
.mypy_cache/
.ruff_cache/
.pytest_cache/

# Node
node_modules/
.next/
out/
.turbo/
*.tsbuildinfo

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# Docker
*.log

# OS
.DS_Store
Thumbs.db

# Build outputs
dist/
build/
*.egg
```

**1.3 Create `.editorconfig` for consistent formatting:**

Create `.editorconfig` at the project root:

```ini
# EditorConfig helps maintain consistent coding styles
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

---

### Step 2: Backend Skeleton (FastAPI)

**2.1 Create `backend/pyproject.toml`:**

This file defines your Python project and all its dependencies.

```toml
[project]
name = "flashcard-backend"
version = "0.1.0"
description = "Flashcard Learning Assistant API"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "openai>=1.12.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg[binary]>=3.1.0",
    "redis>=5.0.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**2.2 Create the main FastAPI application `backend/app/main.py`:**

```python
"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_health import router as health_router
from app.middleware.request_id import RequestIDMiddleware

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
async def lifespan(_: FastAPI):
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

    return app


# Create app instance
app = create_app()
```

**2.3 Create `backend/app/__init__.py`:**

```python
"""Flashcard Backend Application."""
```

**2.4 Create `backend/app/api/__init__.py`:**

```python
"""API routes package."""
```

**2.5 Create the health check route `backend/app/api/routes_health.py`:**

```python
"""Health check endpoint for monitoring and load balancer checks."""

from datetime import datetime, timezone

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
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
    )
```

**2.6 Create the request ID middleware `backend/app/middleware/__init__.py`:**

```python
"""Middleware package."""
```

**2.7 Create `backend/app/middleware/request_id.py`:**

```python
"""Request ID middleware for request tracing."""

import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a unique request ID to each request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        # Add to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request completion
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response
```

**2.8 Create `backend/app/services/__init__.py`:**

```python
"""Services package."""
```

**2.9 Create `backend/app/db/__init__.py`:**

```python
"""Database package."""
```

**2.10 Create `backend/app/prompts/__init__.py`:**

```python
"""Prompts package."""
```

**2.11 Create `backend/app/schemas/__init__.py`:**

```python
"""Pydantic schemas package."""
```

**2.12 Create `backend/app/utils/__init__.py`:**

```python
"""Utilities package."""
```

---

### Step 3: Backend Testing Setup

**3.1 Create `backend/tests/__init__.py`:**

```python
"""Test package."""
```

**3.2 Create `backend/tests/conftest.py`:**

```python
"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)
```

**3.3 Create `backend/tests/unit/__init__.py`:**

```python
"""Unit tests package."""
```

**3.4 Create `backend/tests/unit/test_health.py`:**

```python
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
```

**3.5 Create `backend/tests/integration/__init__.py`:**

```python
"""Integration tests package."""
```

---

### Step 4: Database Migration Setup

**4.1 Initialize Alembic:**

First, navigate to the backend directory and run:

```bash
cd backend

# Create a virtual environment (for local development)
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# Or on Mac/Linux
# source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Initialize Alembic
alembic init app/db/migrations
```

**4.2 Update `backend/app/db/migrations/env.py`:**

Replace the contents with:

```python
"""Alembic migration environment configuration."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/flashcards"
)
config.set_main_option("sqlalchemy.url", database_url)

# Add your model's MetaData object here for 'autogenerate' support
# from app.db.models import Base
# target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**4.3 Update `backend/app/db/migrations/alembic.ini`:**

Move `alembic.ini` to `backend/alembic.ini` and update the script location:

```ini
[alembic]
script_location = app/db/migrations

# ... rest of the file stays the same
```

---

### Step 5: Frontend Skeleton (Next.js)

**5.1 Initialize Next.js application:**

```bash
# Navigate to frontend directory
cd ../frontend

# Create Next.js app with TypeScript, Tailwind, ESLint, and App Router
npx -y create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-turbopack --use-npm
```

When prompted, accept the default options.

**5.2 Update `frontend/src/app/page.tsx`:**

Use the current landing page implementation in the repo (amber/dark theme with a glass form card). If recreating from scratch, make sure it includes:

- Topic input field (max 200 chars)
- Difficulty selector (buttons or dropdown)
- Error state and loading state
- Primary "Generate Flashcards" CTA
- A few feature/value props

Design tokens and animations are defined in `frontend/src/app/globals.css`.

**5.3 Update `frontend/src/app/layout.tsx`:**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Flashcard Learning Assistant",
  description: "Generate AI-powered flashcard decks for any topic",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

---

### Step 6: Frontend Quality Tools

**6.1 Install additional dev dependencies:**

```bash
# In the frontend directory
npm install -D prettier eslint-config-prettier @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom @types/jest
```

**6.2 (Optional) Create `frontend/.prettierrc`:**

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": false,
  "printWidth": 100,
  "tabWidth": 2
}
```

**6.3 Update `frontend/eslint.config.mjs` (flat config):**

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
```

**6.4 Create `frontend/jest.config.js`:**

```javascript
const nextJest = require("next/jest");

const createJestConfig = nextJest({
  dir: "./",
});

const customJestConfig = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
};

module.exports = createJestConfig(customJestConfig);
```

**6.5 Create `frontend/jest.setup.js`:**

```javascript
import "@testing-library/jest-dom";
```

**6.6 Create `frontend/__tests__/page.test.tsx`:**

```tsx
import { render, screen } from "@testing-library/react";
import Home from "@/app/page";

describe("Home Page", () => {
  it("renders the main heading", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /flashcard learning assistant/i })
    ).toBeInTheDocument();
  });

  it("renders the topic input", () => {
    render(<Home />);
    expect(screen.getByLabelText(/what do you want to learn/i)).toBeInTheDocument();
  });

  it("renders the difficulty select", () => {
    render(<Home />);
    expect(screen.getByLabelText(/difficulty level/i)).toBeInTheDocument();
  });

  it("renders the submit button", () => {
    render(<Home />);
    expect(screen.getByRole("button", { name: /generate flashcards/i })).toBeInTheDocument();
  });
});
```

**6.7 Add test script to `frontend/package.json`:**

Add this to the `"scripts"` section:

```json
"test": "jest",
"test:watch": "jest --watch"
```

---

### Step 7: Pre-commit Hooks

**7.1 Create `.pre-commit-config.yaml` at the project root:**

```yaml
# Pre-commit hooks configuration
# Run `pre-commit install` to activate

repos:
  # Python linting and formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        files: ^backend/
      - id: ruff-format
        files: ^backend/

  # Python type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        files: ^backend/
        additional_dependencies:
          - types-redis

  # JavaScript/TypeScript formatting
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        types_or: [javascript, typescript, jsx, tsx, json, css, markdown]
        exclude: ^(frontend/\.next/|node_modules/)

  # General file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=1000]
```

**7.2 Install and activate pre-commit:**

```bash
# Navigate to project root
cd d:/Projects/ai_flashcards

# Install pre-commit (if not already installed)
pip install pre-commit

# Install the hooks
pre-commit install

# Run on all files to verify setup
pre-commit run --all-files
```

---

### Step 8: Docker and Compose

**8.1 Create `backend/Dockerfile`:**

```dockerfile
# Backend Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e .

# Stage 2: Runtime
FROM python:3.11-slim as runtime

WORKDIR /app

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY app ./app
COPY alembic.ini .

# Set ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**8.2 Create `frontend/Dockerfile`:**

```dockerfile
# Frontend Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Dependencies
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built assets
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Set environment variable for port
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Run the application
CMD ["node", "server.js"]
```

**8.3 Update `frontend/next.config.ts` for standalone output:**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Add your other Next.js config options here
};

export default nextConfig;
```

**8.4 Create `docker-compose.yml` at the project root:**

```yaml
# Docker Compose configuration for development
# Run with: docker compose up --build

version: "3.8"

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: flashcards-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: flashcards
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: flashcards-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: flashcards-backend
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/flashcards
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"]
      interval: 30s
      timeout: 10s
      start_period: 10s
      retries: 3
    restart: unless-stopped

  # Next.js Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: flashcards-frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**8.5 Create `docker-compose.dev.yml` for development with hot reload:**

```yaml
# Docker Compose configuration for development with hot reload
# Run with: docker compose -f docker-compose.dev.yml up

version: "3.8"

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: flashcards-postgres-dev
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: flashcards
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: flashcards-redis-dev
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend (development mode with hot reload)
  backend:
    image: python:3.11-slim
    container_name: flashcards-backend-dev
    working_dir: /app
    command: >
      bash -c "pip install -e '.[dev]' &&
               uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/flashcards
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Next.js Frontend (development mode with hot reload)
  frontend:
    image: node:20-alpine
    container_name: flashcards-frontend-dev
    working_dir: /app
    command: sh -c "npm install && npm run dev"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

volumes:
  postgres_data_dev:
```

---

### Step 9: Environment Configuration

**9.1 Create `.env.example` at the project root:**

```env
# ===========================================
# Flashcard Learning Assistant Configuration
# ===========================================
# Copy this file to .env and fill in your values
# NEVER commit the .env file to version control

# -------------------------------------------
# OpenAI API Configuration
# -------------------------------------------
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-api-key-here

# -------------------------------------------
# Database Configuration
# -------------------------------------------
# PostgreSQL connection URL
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/flashcards

# -------------------------------------------
# Redis Configuration
# -------------------------------------------
# Redis connection URL for caching and job queues
REDIS_URL=redis://localhost:6379/0

# -------------------------------------------
# Object Storage Configuration (S3-compatible)
# -------------------------------------------
# For PDF file storage (configure later in Phase 5)
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=flashcards-uploads
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=

# -------------------------------------------
# Frontend Configuration
# -------------------------------------------
# API URL that the frontend will use to connect to backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# -------------------------------------------
# Security Configuration
# -------------------------------------------
# Comma-separated list of allowed CORS origins
CORS_ORIGINS=http://localhost:3000

# Secret key for signing tokens (generate a secure random string)
SECRET_KEY=change-me-in-production-use-a-long-random-string

# -------------------------------------------
# Development Settings
# -------------------------------------------
# Set to "development" or "production"
ENVIRONMENT=development

# Enable debug mode (set to false in production)
DEBUG=true
```

**9.2 Create your actual `.env` file:**

```bash
# Copy the example
cp .env.example .env

# Edit and add your OpenAI API key
# On Windows, use notepad or your preferred editor
```

---

### Step 10: Smoke Test

Now let's verify everything works!

**10.1 Start the services:**

```bash
# Navigate to project root
cd d:/Projects/ai_flashcards

# Build and start all services
docker compose up --build
```

**10.2 Verify the backend health check:**

Open a new terminal and run:

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"ok","timestamp":"2026-01-23T22:30:00.000000+00:00","version":"0.1.0"}
```

Or open http://localhost:8000/health in your browser.

**10.3 Verify the API documentation:**

Open http://localhost:8000/docs in your browser. You should see the Swagger UI with the `/health` endpoint documented.

**10.4 Verify the frontend:**

Open http://localhost:3000 in your browser. You should see:
- A dark, amber-accented background with a glass form card
- The "Master any topic with flashcards" heading
- A topic input field
- Difficulty buttons (Beginner / Intermediate / Advanced)
- A "Generate Flashcards" button

**10.5 Run the backend tests:**

```bash
# In a new terminal, navigate to backend
cd backend

# Activate virtual environment
.venv\Scripts\activate

# Run tests
pytest -v
```

Expected output:
```
========================= test session starts =========================
collected 2 items

tests/unit/test_health.py::test_health_check_returns_ok PASSED
tests/unit/test_health.py::test_health_check_includes_request_id PASSED

========================= 2 passed in 0.50s ==========================
```

**10.6 Run the frontend tests:**

```bash
# Navigate to frontend
cd ../frontend

# Run tests
npm test
```

**10.7 Run pre-commit hooks:**

```bash
# Navigate to project root
cd ..

# Run on all files
pre-commit run --all-files
```

---

## Exit Criteria ✅

Before moving to Phase 2, verify these are all true:

- [ ] `docker compose up --build` runs without errors
- [ ] Backend `/health` returns `{"status": "ok", ...}`
- [ ] Backend Swagger docs load at http://localhost:8000/docs
- [ ] Frontend loads at http://localhost:3000
- [ ] Topic input and difficulty dropdown are visible
- [ ] `pytest` passes all tests in backend
- [ ] `npm test` passes all tests in frontend
- [ ] `pre-commit run --all-files` passes

---

## Troubleshooting

### Docker build fails with "permission denied"
- On Windows, make sure Docker Desktop is running
- Try restarting Docker Desktop

### Port already in use
- Check what's using the port: `netstat -ano | findstr :8000`
- Stop the conflicting service or change the port in docker-compose.yml

### Frontend can't connect to backend
- Ensure CORS is configured correctly in `backend/app/main.py`
- Check that `NEXT_PUBLIC_API_URL` is set correctly

### Pre-commit hooks fail on Windows
- Make sure you're using Git Bash or PowerShell
- Run `pre-commit clean` and try again

---

## Next Steps

Once all exit criteria are met, proceed to **Phase 2: Schema-first Deck Generation**.
