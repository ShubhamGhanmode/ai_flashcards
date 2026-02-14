"""Database session management."""

import os
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _load_env_files() -> None:
    """Load .env files for local development when not provided by shell."""
    backend_dir = Path(__file__).resolve().parents[2]
    repo_dir = backend_dir.parent
    env_candidates = [
        repo_dir / ".env",
        backend_dir / ".env",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(env_file, override=False)


def _build_database_url_from_parts() -> str | None:
    """Build DB URL from component environment variables if provided."""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not any(
        value is not None
        for value in (db_host, db_port, db_name, db_user, db_password)
    ):
        return None

    host = db_host or "localhost"
    port = db_port or "5432"
    name = db_name or "flashcards"
    user = db_user or "postgres"
    password = db_password or ""

    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"

    return f"postgresql+psycopg://{auth}@{host}:{port}/{name}"


def normalize_database_url(database_url: str) -> str:
    """Normalize Postgres URLs to the installed psycopg (v3) driver."""
    if database_url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + database_url.removeprefix(
            "postgresql+psycopg2://"
        )
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


def get_database_url() -> str:
    """Get the database URL from environment."""
    _load_env_files()

    db_url_from_parts = _build_database_url_from_parts()
    if db_url_from_parts:
        return normalize_database_url(db_url_from_parts)

    raw_database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/flashcards",
    )
    return normalize_database_url(raw_database_url)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache the SQLAlchemy engine (lazy initialization)."""
    return create_engine(get_database_url(), echo=False)


def get_session_local() -> sessionmaker[Session]:
    """Create a sessionmaker bound to the engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
