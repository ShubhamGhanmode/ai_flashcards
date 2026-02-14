"""add card_examples table

Revision ID: 20260213_120000
Revises: 20260212_235000
Create Date: 2026-02-13 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260213_120000"
down_revision: str | None = "20260212_235000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create card_examples cache table."""
    op.create_table(
        "card_examples",
        sa.Column("example_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("style", sa.String(length=32), nullable=False),
        sa.Column("length", sa.String(length=32), nullable=False),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.card_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("example_id"),
        sa.UniqueConstraint(
            "card_id",
            "request_fingerprint",
            name="uq_card_examples_card_req",
        ),
    )
    op.create_index(
        "ix_card_examples_card_id",
        "card_examples",
        ["card_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop card_examples cache table."""
    op.drop_index("ix_card_examples_card_id", table_name="card_examples")
    op.drop_table("card_examples")
