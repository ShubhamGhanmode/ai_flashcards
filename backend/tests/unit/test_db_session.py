"""Tests for database URL resolution helpers."""

import app.db.session as session_module


def test_get_database_url_prefers_split_db_settings(
    monkeypatch,
) -> None:
    """DB_* settings should take precedence over DATABASE_URL when present."""
    monkeypatch.setattr(session_module, "_load_env_files", lambda: None)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:wrong@localhost:5432/flashcards",
    )
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "flashcards")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "my pass@123")

    database_url = session_module.get_database_url()

    assert database_url == (
        "postgresql+psycopg://postgres:my+pass%40123@localhost:5432/flashcards"
    )


def test_get_database_url_normalizes_legacy_driver_url(
    monkeypatch,
) -> None:
    """Legacy Postgres URLs should normalize to psycopg v3 driver syntax."""
    monkeypatch.setattr(session_module, "_load_env_files", lambda: None)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/flashcards",
    )
    for key in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    database_url = session_module.get_database_url()

    assert database_url == "postgresql+psycopg://postgres:postgres@localhost:5432/flashcards"
