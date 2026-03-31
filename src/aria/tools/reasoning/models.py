"""SQLAlchemy models for reasoning persistence."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import shared tools Base and re-export for backward compatibility
from aria.tools.models import (  # noqa: F401 - re-exported for compatibility
    Base,
)


class ReasoningSessionModel(Base):
    """Model for reasoning sessions."""

    __tablename__ = "reasoning_sessions"

    # Primary key - internal UUID
    id: Mapped[str] = mapped_column(String(32), primary_key=True)

    # User-provided session identifier
    session_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )

    # Agent identifier
    agent_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Soft delete flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    steps: Mapped[List["ReasoningStepModel"]] = relationship(
        "ReasoningStepModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReasoningStepModel.step_number",
    )

    reflections: Mapped[List["ReasoningReflectionModel"]] = relationship(
        "ReasoningReflectionModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReasoningReflectionModel.timestamp",
    )

    scratchpad_items: Mapped[List["ReasoningScratchpadModel"]] = relationship(
        "ReasoningScratchpadModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    tool_events: Mapped[List["ReasoningToolEventModel"]] = relationship(
        "ReasoningToolEventModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReasoningToolEventModel.timestamp",
    )

    # Unique constraint on session_id + agent_id
    __table_args__ = (
        UniqueConstraint("session_id", "agent_id", name="uq_session_agent"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReasoningSession(id={self.id}, "
            f"session_id={self.session_id}, agent_id={self.agent_id})>"
        )


class ReasoningStepModel(Base):
    """Model for reasoning steps."""

    __tablename__ = "reasoning_steps"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Foreign key to session
    session_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("reasoning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Step details
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    cognitive_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    reasoning_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Why this step was added (echoed from tool `intent`)
    intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSON stored as text (will be serialized/deserialized)
    evidence: Mapped[str] = mapped_column(Text, nullable=True)
    biases_detected: Mapped[str] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    session: Mapped["ReasoningSessionModel"] = relationship(
        "ReasoningSessionModel", back_populates="steps"
    )

    def __repr__(self) -> str:
        return (
            f"<ReasoningStep(id={self.id}, "
            f"step_number={self.step_number}, mode={self.cognitive_mode})>"
        )


class ReasoningReflectionModel(Base):
    """Model for reasoning reflections."""

    __tablename__ = "reasoning_reflections"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Foreign key to session
    session_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("reasoning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reflection details
    content: Mapped[str] = mapped_column(Text, nullable=False)
    step_id: Mapped[int] = mapped_column(
        Integer, nullable=True
    )  # Optional reference to step

    # Why this reflection was added (echoed from tool `intent`)
    intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    session: Mapped["ReasoningSessionModel"] = relationship(
        "ReasoningSessionModel", back_populates="reflections"
    )

    def __repr__(self) -> str:
        return f"<ReasoningReflection(id={self.id}, step_id={self.step_id})>"


class ReasoningScratchpadModel(Base):
    """Model for scratchpad items."""

    __tablename__ = "reasoning_scratchpad"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Foreign key to session
    session_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("reasoning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scratchpad key-value
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Why this scratchpad key was last modified (echoed from tool `intent`)
    intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    session: Mapped["ReasoningSessionModel"] = relationship(
        "ReasoningSessionModel", back_populates="scratchpad_items"
    )

    # Unique constraint on session_id + key
    __table_args__ = (
        UniqueConstraint("session_id", "key", name="uq_session_key"),
    )

    def __repr__(self) -> str:
        return f"<ReasoningScratchpad(id={self.id}, key={self.key})>"


class ReasoningToolEventModel(Base):
    """Audit log of all reasoning tool calls and their intents."""

    __tablename__ = "reasoning_tool_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Foreign key to session (internal id)
    session_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("reasoning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    intent: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional minimal JSON payload for debugging/audit
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    session: Mapped["ReasoningSessionModel"] = relationship(
        "ReasoningSessionModel", back_populates="tool_events"
    )

    def __repr__(self) -> str:
        return (
            f"<ReasoningToolEvent(id={self.id}, tool={self.tool_name}, "
            f"session_id={self.session_id})>"
        )
