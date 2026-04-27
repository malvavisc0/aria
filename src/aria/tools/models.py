"""Shared SQLAlchemy base for all tool models.

All tool modules that need database persistence should import Base
from this module rather than defining their own DeclarativeBase.
This ensures all tool tables share the same metadata and can coexist
in the same database file.

Note: This is separate from aria.db.models.Base which is used for
the Chainlit UI database - Users, Threads, Steps, etc.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all tool SQLAlchemy models."""

    pass


class ScratchpadItemModel(Base):
    """Standalone scratchpad key-value store.

    Decoupled from reasoning sessions — the scratchpad persists
    independently and survives reasoning session lifecycle events.
    """

    __tablename__ = "scratchpad_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
