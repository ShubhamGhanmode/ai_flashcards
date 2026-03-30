"""phase4 telemetry backfill and precision cost fields

Revision ID: 20260215_130000
Revises: 20260215_090000
Create Date: 2026-02-15 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260215_130000"
down_revision: str | None = "20260215_090000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Backfill missing telemetry columns and add precise USD telemetry."""
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
    """Drop precision cost telemetry fields introduced by this backfill."""
    deck_columns = _table_columns("decks")
    example_columns = _table_columns("card_examples")

    if "api_cost_usd" in example_columns:
        op.drop_column("card_examples", "api_cost_usd")
    if "api_cost_usd" in deck_columns:
        op.drop_column("decks", "api_cost_usd")
