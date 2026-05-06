"""SQLAlchemy models for planner persistence."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aria.tools.models import Base


class PlanModel(Base):
    """SQLAlchemy model for execution plans."""

    __tablename__ = "plans"

    # Primary key IS the execution_id
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Agent identifier for multi-agent isolation
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    task: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    steps: Mapped[list["PlanStepModel"]] = relationship(
        "PlanStepModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanStepModel.step_number",
    )


class PlanStepModel(Base):
    """SQLAlchemy model for plan steps."""

    __tablename__ = "plan_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Short identifier for API use
    step_id: Mapped[str] = mapped_column(String(36), nullable=False)

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    plan: Mapped["PlanModel"] = relationship("PlanModel", back_populates="steps")

    def __repr__(self) -> str:
        return f"<PlanStep(id={self.id}, step_id={self.step_id}, status={self.status})>"
