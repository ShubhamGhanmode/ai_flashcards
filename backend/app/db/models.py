"""SQLAlchemy database models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
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
