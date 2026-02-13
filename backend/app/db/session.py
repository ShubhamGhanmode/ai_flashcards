"""Database session management."""

import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Get the database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/flashcards",
    )


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
