"""Planner toolset for agent execution planning.

Provides structured execution plans with step management capabilities.
Each plan is isolated by execution_id, allowing multiple concurrent
plan executions without interference.

All plans are persisted to the database - no in-memory caching.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from aria.tools import tool_response
from aria.tools.decorators import log_tool_call

from . import registry


class StepStatus(str, Enum):
    """Status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanStep:
    """A single step in an execution plan."""

    id: str
    description: str
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Plan:
    """An execution plan containing ordered steps."""

    task: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: list[PlanStep] = field(default_factory=list)
    agent_id: str = "default"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def _dict_to_plan(data: Dict) -> Plan:
    """Convert database dict to Plan dataclass."""
    plan_steps = [
        PlanStep(
            id=step["id"],
            description=step["description"],
            status=StepStatus(step["status"]),
            result=step.get("result"),
            created_at=step["created_at"],
            updated_at=step["updated_at"],
        )
        for step in data["steps"]
    ]
    return Plan(
        id=data["plan_id"],
        agent_id=data.get("agent_id", "default"),
        task=data["task"],
        steps=plan_steps,
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _step_to_dict(step: PlanStep) -> Dict:
    """Serialize a single plan step for database storage."""
    return {
        "id": step.id,
        "description": step.description,
        "status": step.status.value,
        "result": step.result,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
    }


def _serialize_step(step: PlanStep) -> dict[str, object]:
    """Serialize a plan step for tool responses."""
    return {
        "id": step.id,
        "description": step.description,
        "status": step.status.value,
        "result": step.result,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
    }


def _serialize_plan(plan: Plan) -> dict[str, object]:
    """Serialize a plan for tool responses."""
    completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED)
    failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)
    in_progress = sum(1 for s in plan.steps if s.status == StepStatus.IN_PROGRESS)
    pending = sum(1 for s in plan.steps if s.status == StepStatus.PENDING)

    return {
        "plan_id": plan.id,
        "task": plan.task,
        "steps": [_serialize_step(step) for step in plan.steps],
        "total_steps": len(plan.steps),
        "progress": {
            "total": len(plan.steps),
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
        },
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def _get_current_plan(execution_id: str) -> Plan:
    """Return the active plan for the given execution_id from database."""
    db = registry.get_db()
    plan_data = db.load_plan(execution_id)
    if plan_data is None:
        raise RuntimeError(
            f"No active plan for execution_id '{execution_id}'. "
            "Use plan(action='create') first."
        )
    return _dict_to_plan(plan_data)


def _ok(
    tool: str,
    reason: str,
    result: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a success response."""
    return tool_response(
        tool=tool,
        reason=reason or "",
        data={
            "result": result,
            "error": "",
            "metadata": metadata or {},
        },
    )


def _err(
    tool: str,
    reason: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Build an error response."""
    return tool_response(
        tool=tool,
        reason=reason or "",
        data={
            "result": "",
            "error": message,
            "metadata": metadata or {},
        },
    )


def _action_create(
    reason: str,
    task: str,
    steps: List[str],
    agent_id: str,
) -> str:
    """Create a new execution plan with the given task and steps."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Create plan steps
        plan_steps = [
            PlanStep(
                id=str(uuid.uuid4())[:8],
                description=step_desc,
                status=StepStatus.PENDING,
            )
            for step_desc in steps
        ]

        plan = Plan(task=task, steps=plan_steps, agent_id=agent_id)
        execution_id = plan.id
        created_at = plan.created_at

        # Save to database
        db = registry.get_db()
        db.save_plan(
            plan_id=execution_id,
            agent_id=agent_id,
            task=task,
            steps=[_step_to_dict(s) for s in plan.steps],
            created_at=created_at,
        )

        return _ok(
            tool="plan",
            reason=reason,
            result=_serialize_plan(plan),
            metadata={
                "timestamp": timestamp,
                "action": "create",
                "params": {
                    "task": task,
                    "steps": steps,
                    "agent_id": agent_id,
                },
                "execution_id": execution_id,
                "success": True,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "create",
                "params": {"task": task, "steps": steps},
                "success": False,
            },
        )


def _action_get(reason: str, execution_id: str) -> str:
    """Get the current plan status."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_plan = _get_current_plan(execution_id)
        return _ok(
            tool="plan",
            reason=reason,
            result=_serialize_plan(current_plan),
            metadata={
                "timestamp": timestamp,
                "action": "get",
                "execution_id": execution_id,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "get",
                "execution_id": execution_id,
            },
        )


def _action_update(
    reason: str,
    execution_id: str,
    step_id: str,
    status: Optional[str],
    result: Optional[str],
) -> str:
    """Update a step's status and optionally its result."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Validate status
        if status is None:
            return _err(
                tool="plan",
                reason=reason,
                message="status is required for update action",
                metadata={
                    "timestamp": timestamp,
                    "action": "update",
                    "params": {"step_id": step_id},
                    "success": False,
                },
            )

        try:
            new_status = StepStatus(status.lower())
        except ValueError:
            valid_statuses = [s.value for s in StepStatus]
            return _err(
                tool="plan",
                reason=reason,
                message=(
                    f"Invalid status '{status}'. " f"Valid values: {valid_statuses}"
                ),
                metadata={
                    "timestamp": timestamp,
                    "action": "update",
                    "params": {"step_id": step_id, "status": status},
                    "success": False,
                },
            )

        # Update in database
        db = registry.get_db()
        success = db.update_step(execution_id, step_id, new_status.value, result)

        if not success:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "update",
                    "params": {"step_id": step_id, "status": status},
                    "success": False,
                },
            )

        # Reload to get updated step data
        current_plan = _get_current_plan(execution_id)
        step = next((s for s in current_plan.steps if s.id == step_id), None)

        if step is None:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "update",
                    "params": {"step_id": step_id, "status": status},
                    "success": False,
                },
            )

        return _ok(
            tool="plan",
            reason=reason,
            result=_serialize_step(step),
            metadata={
                "timestamp": timestamp,
                "action": "update",
                "params": {
                    "step_id": step_id,
                    "status": status,
                    "result": result,
                },
                "execution_id": execution_id,
                "success": True,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "update",
                "params": {"step_id": step_id, "status": status},
                "success": False,
            },
        )


def _action_add(
    reason: str,
    execution_id: str,
    after_step_id: Optional[str],
    description: str,
) -> str:
    """Add a new step after a specified step or at the end."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Create new step
        step_id = str(uuid.uuid4())

        db = registry.get_db()
        step_data = db.add_step(execution_id, step_id, description, after_step_id)

        if step_data is None:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{after_step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "add",
                    "params": {
                        "after_step_id": after_step_id,
                        "description": description,
                    },
                    "success": False,
                },
            )

        # Convert status string to StepStatus enum
        step_data["status"] = StepStatus(step_data["status"])
        step = PlanStep(**step_data)

        # Reload plan to get updated step count
        current_plan = _get_current_plan(execution_id)

        return _ok(
            tool="plan",
            reason=reason,
            result={
                **_serialize_step(step),
                "inserted_after": after_step_id,
                "total_steps": len(current_plan.steps),
            },
            metadata={
                "timestamp": timestamp,
                "action": "add",
                "params": {
                    "after_step_id": after_step_id,
                    "description": description,
                },
                "execution_id": execution_id,
                "success": True,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "add",
                "params": {
                    "after_step_id": after_step_id,
                    "description": description,
                },
                "success": False,
            },
        )


def _action_remove(
    reason: str,
    execution_id: str,
    step_id: str,
) -> str:
    """Remove a step from the plan."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        db = registry.get_db()
        removed_data = db.remove_step(execution_id, step_id)

        if removed_data is None:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "remove",
                    "params": {"step_id": step_id},
                    "success": False,
                },
            )

        # Reload to get remaining step count
        current_plan = _get_current_plan(execution_id)

        return _ok(
            tool="plan",
            reason=reason,
            result={
                "removed_step_id": removed_data["id"],
                "description": removed_data["description"],
                "remaining_steps": len(current_plan.steps),
            },
            metadata={
                "timestamp": timestamp,
                "action": "remove",
                "params": {"step_id": step_id},
                "execution_id": execution_id,
                "success": True,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "remove",
                "params": {"step_id": step_id},
                "success": False,
            },
        )


def _action_replace(
    reason: str,
    execution_id: str,
    step_id: str,
    description: str,
) -> str:
    """Replace a step's description."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Load current plan to get old description
        current_plan = _get_current_plan(execution_id)
        old_description = None
        for s in current_plan.steps:
            if s.id == step_id:
                old_description = s.description
                break

        if old_description is None:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "replace",
                    "params": {"step_id": step_id, "description": description},
                    "success": False,
                },
            )

        # Update in database
        db = registry.get_db()
        success = db.update_step(execution_id, step_id, description=description)

        if not success:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "replace",
                    "params": {"step_id": step_id, "description": description},
                    "success": False,
                },
            )

        # Reload to get updated step
        current_plan = _get_current_plan(execution_id)
        step = next((s for s in current_plan.steps if s.id == step_id), None)

        if step is None:
            return _err(
                tool="plan",
                reason=reason,
                message=f"Step '{step_id}' not found in plan.",
                metadata={
                    "timestamp": timestamp,
                    "action": "replace",
                    "params": {"step_id": step_id, "description": description},
                    "success": False,
                },
            )

        return _ok(
            tool="plan",
            reason=reason,
            result={
                **_serialize_step(step),
                "old_description": old_description,
                "new_description": step.description,
            },
            metadata={
                "timestamp": timestamp,
                "action": "replace",
                "params": {"step_id": step_id, "description": description},
                "execution_id": execution_id,
                "success": True,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "replace",
                "params": {"step_id": step_id, "description": description},
                "success": False,
            },
        )


def _action_reorder(
    reason: str,
    execution_id: str,
    step_ids: List[str],
) -> str:
    """Reorder steps in the plan."""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_plan = _get_current_plan(execution_id)

        current_step_count = len(current_plan.steps)

        if len(step_ids) != current_step_count:
            return _err(
                tool="plan",
                reason=reason,
                message=(
                    "step_ids must contain each current step exactly "
                    "once. "
                    f"Expected {current_step_count} IDs, got "
                    f"{len(step_ids)}."
                ),
                metadata={
                    "timestamp": timestamp,
                    "action": "reorder",
                    "params": {"step_ids": step_ids},
                    "success": False,
                },
            )

        if len(set(step_ids)) != len(step_ids):
            return _err(
                tool="plan",
                reason=reason,
                message="step_ids contains duplicate step IDs.",
                metadata={
                    "timestamp": timestamp,
                    "action": "reorder",
                    "params": {"step_ids": step_ids},
                    "success": False,
                },
            )

        # Validate all step IDs are present
        current_ids = {s.id for s in current_plan.steps}
        requested_ids = set(step_ids)

        if current_ids != requested_ids:
            missing = current_ids - requested_ids
            extra = requested_ids - current_ids
            error_parts = []
            if missing:
                error_parts.append(f"Missing steps: {missing}")
            if extra:
                error_parts.append(f"Unknown steps: {extra}")
            return _err(
                tool="plan",
                reason=reason,
                message="; ".join(error_parts),
                metadata={
                    "timestamp": timestamp,
                    "action": "reorder",
                    "params": {"step_ids": step_ids},
                    "success": False,
                },
            )

        # Reorder in database
        db = registry.get_db()
        reordered_data = db.reorder_steps(execution_id, step_ids)

        if reordered_data is None:
            return _err(
                tool="plan",
                reason=reason,
                message="Failed to reorder steps.",
                metadata={
                    "timestamp": timestamp,
                    "action": "reorder",
                    "params": {"step_ids": step_ids},
                    "success": False,
                },
            )

        return _ok(
            tool="plan",
            reason=reason,
            result={
                "reordered_steps": reordered_data,
                "total_steps": len(reordered_data),
            },
            metadata={
                "timestamp": timestamp,
                "action": "reorder",
                "params": {"step_ids": step_ids},
                "execution_id": execution_id,
                "success": True,
            },
        )
    except Exception as exc:
        return _err(
            tool="plan",
            reason=reason,
            message=str(exc),
            metadata={
                "timestamp": timestamp,
                "action": "reorder",
                "params": {"step_ids": step_ids},
                "success": False,
            },
        )


@log_tool_call
def plan(
    reason: str,
    action: str,
    task: Optional[str] = None,
    steps: Optional[List[str]] = None,
    step_id: Optional[str] = None,
    status: Optional[str] = None,
    result: Optional[str] = None,
    description: Optional[str] = None,
    after_step_id: Optional[str] = None,
    step_ids: Optional[List[str]] = None,
    execution_id: Optional[str] = None,
    agent_id: str = "default",
) -> str:
    """Create and manage ordered execution plans (SQLite-backed).

    Actions: create, get, update, add, remove, replace, reorder.

    Args:
        reason: Why (logging).
        action: create|get|update|add|remove|replace|reorder.
        task: Task description (required for create).
        steps: Ordered step descriptions (required for create).
        step_id: Step ID for update/remove/replace.
        status: pending|in_progress|completed|failed (for update).
        result: Result message for update.
        description: Step description for add/replace.
        after_step_id: Insert after this step ID (for add).
        step_ids: New step order (for reorder).
        execution_id: Plan ID from create; required for all others.
        agent_id: Agent isolation key (default: "default").

    Returns:
        JSON with plan data, step info, progress.
    """
    action = action.lower().strip()

    if action == "create":
        if task is None:
            return _err(
                tool="plan",
                reason=reason,
                message="task is required for create action",
                metadata={"action": "create", "success": False},
            )
        if steps is None or len(steps) == 0:
            return _err(
                tool="plan",
                reason=reason,
                message="steps is required for create action",
                metadata={"action": "create", "success": False},
            )
        return _action_create(reason, task, steps, agent_id)

    elif action == "get":
        if execution_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="execution_id is required for get action",
                metadata={"action": "get", "success": False},
            )
        return _action_get(reason, execution_id)

    elif action == "update":
        if execution_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="execution_id is required for update action",
                metadata={"action": "update", "success": False},
            )
        if step_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="step_id is required for update action",
                metadata={"action": "update", "success": False},
            )
        return _action_update(reason, execution_id, step_id, status, result)

    elif action == "add":
        if execution_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="execution_id is required for add action",
                metadata={"action": "add", "success": False},
            )
        if description is None:
            return _err(
                tool="plan",
                reason=reason,
                message="description is required for add action",
                metadata={"action": "add", "success": False},
            )
        return _action_add(reason, execution_id, after_step_id, description)

    elif action == "remove":
        if execution_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="execution_id is required for remove action",
                metadata={"action": "remove", "success": False},
            )
        if step_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="step_id is required for remove action",
                metadata={"action": "remove", "success": False},
            )
        return _action_remove(reason, execution_id, step_id)

    elif action == "replace":
        if execution_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="execution_id is required for replace action",
                metadata={"action": "replace", "success": False},
            )
        if step_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="step_id is required for replace action",
                metadata={"action": "replace", "success": False},
            )
        if description is None:
            return _err(
                tool="plan",
                reason=reason,
                message="description is required for replace action",
                metadata={"action": "replace", "success": False},
            )
        return _action_replace(reason, execution_id, step_id, description)

    elif action == "reorder":
        if execution_id is None:
            return _err(
                tool="plan",
                reason=reason,
                message="execution_id is required for reorder action",
                metadata={"action": "reorder", "success": False},
            )
        if step_ids is None:
            return _err(
                tool="plan",
                reason=reason,
                message="step_ids is required for reorder action",
                metadata={"action": "reorder", "success": False},
            )
        return _action_reorder(reason, execution_id, step_ids)

    else:
        return _err(
            tool="plan",
            reason=reason,
            message=(
                f"Unknown action '{action}'. Valid actions: "
                "create, get, update, add, remove, replace, reorder"
            ),
            metadata={
                "action": action,
                "success": False,
                "how_to_fix": (
                    "Use one of the valid actions: "
                    "create, get, update, add, remove, replace, reorder"
                ),
            },
        )
