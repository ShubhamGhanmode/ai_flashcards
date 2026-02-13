"""create decks and cards tables

Revision ID: 20260212_235000
Revises:
Create Date: 2026-02-12 23:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260212_235000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial decks and cards tables."""
    op.create_table(
        "decks",
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("difficulty_level", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=200), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("deck_id"),
    )
    op.create_table(
        "cards",
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.deck_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("card_id"),
    )
    op.create_index("ix_cards_deck_id", "cards", ["deck_id"], unique=False)


def downgrade() -> None:
    """Drop initial decks and cards tables."""
    op.drop_index("ix_cards_deck_id", table_name="cards")
    op.drop_table("cards")
    op.drop_table("decks")
