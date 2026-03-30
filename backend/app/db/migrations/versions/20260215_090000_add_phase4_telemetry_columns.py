"""add phase4 telemetry columns

Revision ID: 20260215_090000
Revises: 20260213_120000
Create Date: 2026-02-15 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260215_090000"
down_revision: str | None = "20260213_120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Add cost/latency telemetry fields for deck and example rows."""
    deck_columns = _table_columns("decks")
    if "tokens_used" not in deck_columns:
        op.add_column("decks", sa.Column("tokens_used", sa.Integer(), nullable=True))
    if "api_cost_cents" not in deck_columns:
        op.add_column("decks", sa.Column("api_cost_cents", sa.Integer(), nullable=True))
    if "api_cost_usd" not in deck_columns:
        op.add_column("decks", sa.Column("api_cost_usd", sa.Float(), nullable=True))
    if "generation_time_ms" not in deck_columns:
        op.add_column(
            "decks",
            sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        )

    example_columns = _table_columns("card_examples")
    if "tokens_used" not in example_columns:
        op.add_column(
            "card_examples",
            sa.Column("tokens_used", sa.Integer(), nullable=True),
        )
    if "api_cost_cents" not in example_columns:
        op.add_column(
            "card_examples",
            sa.Column("api_cost_cents", sa.Integer(), nullable=True),
        )
    if "api_cost_usd" not in example_columns:
        op.add_column(
            "card_examples",
            sa.Column("api_cost_usd", sa.Float(), nullable=True),
        )
    if "generation_time_ms" not in example_columns:
        op.add_column(
            "card_examples",
            sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    """Remove cost/latency telemetry fields."""
    example_columns = _table_columns("card_examples")
    deck_columns = _table_columns("decks")

    if "generation_time_ms" in example_columns:
        op.drop_column("card_examples", "generation_time_ms")
    if "api_cost_usd" in example_columns:
        op.drop_column("card_examples", "api_cost_usd")
    if "api_cost_cents" in example_columns:
        op.drop_column("card_examples", "api_cost_cents")
    if "tokens_used" in example_columns:
        op.drop_column("card_examples", "tokens_used")

    if "generation_time_ms" in deck_columns:
        op.drop_column("decks", "generation_time_ms")
    if "api_cost_usd" in deck_columns:
        op.drop_column("decks", "api_cost_usd")
    if "api_cost_cents" in deck_columns:
        op.drop_column("decks", "api_cost_cents")
    if "tokens_used" in deck_columns:
        op.drop_column("decks", "tokens_used")
