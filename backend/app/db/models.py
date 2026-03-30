"""SQLAlchemy database models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Deck(Base):
    """Deck model for storing generated flashcard decks."""

    __tablename__ = "decks"

    deck_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic = Column(String(200), nullable=False)
    difficulty_level = Column(String(20), nullable=False)
    scope = Column(String(200), nullable=True)
    payload = Column(JSONB, nullable=False)  # Full response JSON
    tokens_used = Column(Integer, nullable=True)
    api_cost_cents = Column(Integer, nullable=True)
    api_cost_usd = Column(Float, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    """Card model for individual flashcards."""

    __tablename__ = "cards"

    card_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    deck_id = Column(
        UUID(as_uuid=True),
        ForeignKey("decks.deck_id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)  # Full concept JSON
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    deck = relationship("Deck", back_populates="cards")
    examples = relationship(
        "CardExample",
        back_populates="card",
        cascade="all, delete-orphan",
    )


class CardExample(Base):
    """Cached example generation payloads per card and request fingerprint."""

    __tablename__ = "card_examples"
    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "request_fingerprint",
            name="uq_card_examples_card_req",
        ),
    )

    example_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    card_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cards.card_id", ondelete="CASCADE"),
        nullable=False,
    )
    request_fingerprint = Column(String(64), nullable=False)
    style = Column(String(32), nullable=False)
    length = Column(String(32), nullable=False)
    constraints = Column(JSONB, nullable=True)
    payload = Column(JSONB, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    api_cost_cents = Column(Integer, nullable=True)
    api_cost_usd = Column(Float, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    card = relationship("Card", back_populates="examples")
