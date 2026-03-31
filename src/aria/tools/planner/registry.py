"""Planner registry backed by database."""

from typing import Optional

from loguru import logger

from .database import PlannerDatabase

_db = None


def _get_db() -> PlannerDatabase:
    global _db
    if _db is None:
        _db = PlannerDatabase()
    return _db


def get_active_plan_id(agent_id: str) -> Optional[str]:
    """Get the most recent active plan ID for an agent."""
    db = _get_db()
    plan_data = db.get_active_plan(agent_id)
    if not plan_data:
        return None
    logger.debug(
        "Resolved active plan '{}' for agent '{}'",
        plan_data["plan_id"],
        agent_id,
    )
    return plan_data["plan_id"]


def plan_exists(plan_id: str) -> bool:
    """Check if a plan exists and is active."""
    db = _get_db()
    return db.load_plan(plan_id) is not None


def get_db() -> PlannerDatabase:
    """Get the database instance."""
    return _get_db()
