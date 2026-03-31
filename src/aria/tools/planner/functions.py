"""Planner toolset for agent execution planning.

Provides structured execution plans with step management capabilities.
Each plan is isolated by execution_id, allowing multiple concurrent
plan executions without interference.

All plans are persisted to the database - no in-memory caching.
"""

import functools
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, Optional

from aria.tools import get_function_name, tool_response

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


def _update_timestamp(obj: Plan | PlanStep) -> None:
    """Update the updated_at timestamp of a plan or step."""
    obj.updated_at = datetime.now(timezone.utc).isoformat()


def _no_active_plan_error(
    reason: str,
    operation: str,
    execution_id: Optional[str] = None,
    **params: object,
) -> str:
    """Return a standardized no-active-plan error payload."""
    error_msg = (
        f"No active plan for execution_id '{execution_id}'. "
        "Use create_execution_plan first."
        if execution_id
        else "No active plan. Use create_execution_plan first."
    )
    return tool_response(
        tool=operation,
        intent="",
        data={"error": error_msg},
    )


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
    in_progress = sum(
        1 for s in plan.steps if s.status == StepStatus.IN_PROGRESS
    )
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
            "Use create_execution_plan first."
        )
    # Reconstruct Plan from database data
    return _dict_to_plan(plan_data)


def _requires_plan(func: Callable) -> Callable:
    """Decorator that checks if a plan exists in the database.

    Returns an error JSON if no plan exists for the execution_id.
    The execution_id is expected as the second argument (after 'reason').
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> str:
        # execution_id is expected as the second positional arg or in kwargs
        execution_id = args[1] if len(args) > 1 else kwargs.get("execution_id")
        if not execution_id or not registry.plan_exists(execution_id):
            reason = args[0] if args else kwargs.get("reason", "unknown")
            return _no_active_plan_error(reason, func.__name__, execution_id)
        return func(*args, **kwargs)

    return wrapper


def create_execution_plan(
    reason: str, task: str, steps: list[str], agent_id: str = "default"
) -> str:
    """Create a new execution plan with the given task and steps.

    Args:
        reason: Natural-language explanation of why the agent needs planning.
        task: The overall task description.
        steps: List of step descriptions in execution order.
        agent_id: Agent identifier for multi-agent isolation.

    Returns:
        A JSON string containing the created plan or error.
    """
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

        return tool_response(
            tool=get_function_name(),
            intent=reason or "",
            data={
                "result": _serialize_plan(plan),
                "error": "",
                "metadata": {
                    "timestamp": timestamp,
                    "params": {
                        "task": task,
                        "steps": steps,
                        "agent_id": agent_id,
                    },
                    "execution_id": execution_id,
                    "success": True,
                },
            },
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason or "",
            data={
                "result": "",
                "error": str(exc),
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"task": task, "steps": steps},
                    "success": False,
                },
            },
        )


@_requires_plan
def get_execution_plan(reason: str, execution_id: str) -> str:
    """Get the current plan status.

    Args:
        reason: Natural-language explanation of why the agent needs the plan.
        execution_id: The execution ID of the plan to retrieve.

    Returns:
        A JSON string containing the current plan or error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_plan = _get_current_plan(execution_id)

        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data=_serialize_plan(current_plan),
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason,
            exc=Exception(str(exc)),
        )


@_requires_plan
def update_plan_step(
    reason: str,
    execution_id: str,
    step_id: str,
    status: str,
    result: Optional[str] = None,
) -> str:
    """Update a step's status and optionally its result.

    Args:
        reason: Natural-language explanation of why the agent needs to update.
        execution_id: The execution ID of the plan to update.
        step_id: The ID of the step to update.
        status: New status - one of: pending, in_progress, completed, failed.
        result: Optional result message to store with the step.

    Returns:
        A JSON string containing the updated step or error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Validate status
        try:
            new_status = StepStatus(status.lower())
        except ValueError:
            valid_statuses = [s.value for s in StepStatus]
            error = (
                f"Invalid status '{status}'. Valid values: {valid_statuses}"
            )
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": error,
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id, "status": status},
                        "success": False,
                    },
                },
            )

        # Update in database
        db = registry.get_db()
        success = db.update_step(
            execution_id, step_id, new_status.value, result
        )

        if not success:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id, "status": status},
                        "success": False,
                    },
                },
            )

        # Reload to get updated step data
        current_plan = _get_current_plan(execution_id)
        step = next((s for s in current_plan.steps if s.id == step_id), None)

        if step is None:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id, "status": status},
                        "success": False,
                    },
                },
            )

        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": _serialize_step(step),
                "error": "",
                "metadata": {
                    "timestamp": timestamp,
                    "params": {
                        "step_id": step_id,
                        "status": status,
                        "result": result,
                    },
                    "success": True,
                },
            },
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": "",
                "error": str(exc),
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_id": step_id, "status": status},
                    "success": False,
                },
            },
        )


@_requires_plan
def add_plan_step(
    reason: str, execution_id: str, after_step_id: Optional[str], new_step: str
) -> str:
    """Add a new step after a specified step or at the end.

    Args:
        reason: Natural-language explanation of why the agent needs to add a
            step.
        execution_id: The execution ID of the plan to add a step to.
        after_step_id: ID of the step to insert after. None for end of plan.
        new_step: Description of the new step.

    Returns:
        A JSON string containing the inserted step or error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Create new step
        step_id = str(uuid.uuid4())

        db = registry.get_db()
        step_data = db.add_step(execution_id, step_id, new_step, after_step_id)

        if step_data is None:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{after_step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {
                            "after_step_id": after_step_id,
                            "new_step": new_step,
                        },
                        "success": False,
                    },
                },
            )

        # Convert status string to StepStatus enum
        step_data["status"] = StepStatus(step_data["status"])
        step = PlanStep(**step_data)

        # Reload plan to get updated step count
        current_plan = _get_current_plan(execution_id)

        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": {
                    **_serialize_step(step),
                    "inserted_after": after_step_id,
                    "total_steps": len(current_plan.steps),
                },
                "error": "",
                "metadata": {
                    "timestamp": timestamp,
                    "params": {
                        "after_step_id": after_step_id,
                        "new_step": new_step,
                    },
                    "success": True,
                },
            },
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": "",
                "error": str(exc),
                "metadata": {
                    "timestamp": timestamp,
                    "params": {
                        "after_step_id": after_step_id,
                        "new_step": new_step,
                    },
                    "success": False,
                },
            },
        )


@_requires_plan
def remove_plan_step(reason: str, execution_id: str, step_id: str) -> str:
    """Remove a step from the plan.

    Args:
        reason: Natural-language explanation of why the agent needs to remove
            a step.
        execution_id: The execution ID of the plan to remove a step from.
        step_id: ID of the step to remove.

    Returns:
        A JSON string confirming removal or error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        db = registry.get_db()
        removed_data = db.remove_step(execution_id, step_id)

        if removed_data is None:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id},
                        "success": False,
                    },
                },
            )

        # Reload to get remaining step count
        current_plan = _get_current_plan(execution_id)

        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": {
                    "removed_step_id": removed_data["id"],
                    "description": removed_data["description"],
                    "remaining_steps": len(current_plan.steps),
                },
                "error": "",
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_id": step_id},
                    "success": True,
                },
            },
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": "",
                "error": str(exc),
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_id": step_id},
                    "success": False,
                },
            },
        )


@_requires_plan
def replace_plan_step(
    reason: str, execution_id: str, step_id: str, new_step: str
) -> str:
    """Replace a step's description.

    Args:
        reason: Natural-language explanation of why the agent needs to replace
            a step.
        execution_id: The execution ID of the plan to replace a step in.
        step_id: ID of the step to replace.
        new_step: New description for the step.

    Returns:
        A JSON string containing the updated step or error.
    """
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
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id, "new_step": new_step},
                        "success": False,
                    },
                },
            )

        # Update in database
        db = registry.get_db()
        success = db.update_step(execution_id, step_id, description=new_step)

        if not success:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id, "new_step": new_step},
                        "success": False,
                    },
                },
            )

        # Reload to get updated step
        current_plan = _get_current_plan(execution_id)
        step = next((s for s in current_plan.steps if s.id == step_id), None)

        if step is None:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": f"Step '{step_id}' not found in plan.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_id": step_id, "new_step": new_step},
                        "success": False,
                    },
                },
            )

        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": {
                    **_serialize_step(step),
                    "old_description": old_description,
                    "new_description": step.description,
                },
                "error": "",
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_id": step_id, "new_step": new_step},
                    "success": True,
                },
            },
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": "",
                "error": str(exc),
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_id": step_id, "new_step": new_step},
                    "success": False,
                },
            },
        )


@_requires_plan
def reorder_plan_steps(
    reason: str, execution_id: str, step_ids: list[str]
) -> str:
    """Reorder steps in the plan.

    Args:
        reason: Natural-language explanation of why the agent needs to reorder.
        execution_id: The execution ID of the plan to reorder.
        step_ids: New order of step IDs as a list.

    Returns:
        A JSON string containing the reordered steps or error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_plan = _get_current_plan(execution_id)

        current_step_count = len(current_plan.steps)

        if len(step_ids) != current_step_count:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": (
                        "step_ids must contain each current step exactly "
                        "once. "
                        f"Expected {current_step_count} IDs, got "
                        f"{len(step_ids)}."
                    ),
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_ids": step_ids},
                        "success": False,
                    },
                },
            )

        if len(set(step_ids)) != len(step_ids):
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": "step_ids contains duplicate step IDs.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_ids": step_ids},
                        "success": False,
                    },
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
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": "; ".join(error_parts),
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_ids": step_ids},
                        "success": False,
                    },
                },
            )

        # Reorder in database
        db = registry.get_db()
        reordered_data = db.reorder_steps(execution_id, step_ids)

        if reordered_data is None:
            return tool_response(
                tool=get_function_name(),
                intent=reason,
                data={
                    "result": "",
                    "error": "Failed to reorder steps.",
                    "metadata": {
                        "timestamp": timestamp,
                        "params": {"step_ids": step_ids},
                        "success": False,
                    },
                },
            )

        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": {
                    "reordered_steps": reordered_data,
                    "total_steps": len(reordered_data),
                },
                "error": "",
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_ids": step_ids},
                    "success": True,
                },
            },
        )
    except Exception as exc:
        return tool_response(
            tool=get_function_name(),
            intent=reason,
            data={
                "result": "",
                "error": str(exc),
                "metadata": {
                    "timestamp": timestamp,
                    "params": {"step_ids": step_ids},
                    "success": False,
                },
            },
        )
