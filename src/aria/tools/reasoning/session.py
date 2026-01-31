"""Reasoning session class - no global state."""

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .constants import (
    BIAS_PATTERNS,
    COGNITIVE_MODES,
    COGNITIVE_SCAFFOLDING,
    REASONING_TYPES,
)

if TYPE_CHECKING:
    from .database import ReasoningDatabase


class ReasoningSession:
    """A single reasoning session with structured reasoning artifacts."""

    def __init__(
        self, session_id: Optional[str] = None, agent_id: Optional[str] = None
    ):
        """Initialize a new reasoning session.

        Args:
            session_id: User-provided session identifier
            agent_id: Agent identifier for multi-agent isolation
        """
        self.id = hashlib.md5(str(datetime.now()).encode()).hexdigest()
        self.session_id = session_id
        self.agent_id = agent_id
        self.steps: List[Dict] = []
        self.reflections: List[Dict] = []
        self.scratchpad: Dict[str, Dict] = {}
        self.tool_events: List[Dict[str, Any]] = []
        self.created_at = datetime.now().isoformat()
        self.confidence_trajectory: List[float] = []
        self._db: Optional["ReasoningDatabase"] = None

    def add_step(
        self,
        intent: str,
        content: str,
        cognitive_mode: str = "analysis",
        reasoning_type: str = "deductive",
        evidence: Optional[List[str]] = None,
        confidence: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Add one structured reasoning step.

        Args:
            content (str): The reasoning content
            cognitive_mode (str): One of COGNITIVE_MODES
                (analysis, synthesis, evaluation, etc.)
            reasoning_type (str): One of REASONING_TYPES
                (deductive, inductive, abductive, etc.)
            evidence (str): Optional list of evidence supporting this step
            confidence (str): Confidence level (0.0 to 1.0)

        Returns:
            Dict[str, Any]: JSON-compatible step payload
        """
        if cognitive_mode not in COGNITIVE_MODES:
            cognitive_mode = "analysis"
        if reasoning_type not in REASONING_TYPES:
            reasoning_type = "deductive"

        biases = (
            self._detect_biases(content + " ".join(evidence or []))
            if evidence
            else []
        )

        step = {
            "id": len(self.steps) + 1,
            "cognitive_mode": cognitive_mode,
            "reasoning_type": reasoning_type,
            "content": content,
            "confidence": confidence,
            "intent": intent,
            "evidence": evidence or [],
            "biases_detected": biases,
            "timestamp": datetime.now().isoformat(),
        }

        self.steps.append(step)
        self.confidence_trajectory.append(confidence)

        # Persist to database
        self.persist_step(step)

        # Persist tool event (audit)
        self.persist_tool_event(
            tool_name="add_reasoning_step",
            intent=intent,
            timestamp=step["timestamp"],
            payload={
                "step_id": step["id"],
                "cognitive_mode": cognitive_mode,
                "reasoning_type": reasoning_type,
                "confidence": confidence,
            },
        )

        result: Dict[str, Any] = {
            "step_id": step["id"],
            "cognitive_mode": cognitive_mode,
            "reasoning_type": reasoning_type,
            "content": content,
            "confidence": confidence,
            "intent": intent,
            "evidence": step["evidence"],
            "biases_detected": biases,
            "timestamp": step["timestamp"],
        }

        if confidence < 0.7:
            result["scaffolding_hint"] = COGNITIVE_SCAFFOLDING[cognitive_mode]

        return result

    def add_reflection(
        self, intent: str, reflection: str, on_step: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add meta-cognitive reflection.

        Args:
            reflection (str): The reflection content
            on_step (int): Optional step ID this reflection refers to

        Returns:
            Dict[str, Any]: JSON-compatible reflection payload
        """
        entry: Dict[str, Any] = {
            "id": len(self.reflections) + 1,
            "content": reflection,
            "step_id": on_step,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
        }
        self.reflections.append(entry)

        # Persist to database
        self.persist_reflection(entry)

        # Persist tool event (audit)
        self.persist_tool_event(
            tool_name="add_reflection",
            intent=intent,
            timestamp=entry["timestamp"],
            payload={"reflection_id": entry["id"], "step_id": on_step},
        )

        return {
            "reflection_id": entry["id"],
            "content": reflection,
            "step_id": on_step,
            "intent": intent,
            "timestamp": entry["timestamp"],
        }

    def scratchpad_operation(
        self,
        intent: str,
        key: str,
        operation: str = "get",
        value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simple working memory scratchpad.

        Args:
            key (str): The key to operate on (or "all" for clear operation)
            operation (str): One of "get", "set", "list", "clear"
            value (str): Value to set (required for "set" operation)

        Returns:
            Dict[str, Any]: JSON-compatible scratchpad operation result
        """
        now = datetime.now().isoformat()
        match operation:
            case "set":
                if value is None:
                    return {
                        "status": "error",
                        "error": {
                            "code": "VALUE_REQUIRED",
                            "message": "Value required for set operation",
                        },
                    }
                self.scratchpad[key] = {
                    "value": value,
                    "updated": now,
                    "intent": intent,
                }
                # Persist to database
                self.persist_scratchpad_item(key, self.scratchpad[key])

                self.persist_tool_event(
                    tool_name="use_scratchpad",
                    intent=intent,
                    timestamp=now,
                    payload={"operation": "set", "key": key},
                )

                return {
                    "operation": "set",
                    "key": key,
                    "value": value,
                    "intent": intent,
                    "timestamp": now,
                }
            case "get":
                if key in self.scratchpad:
                    return {
                        "operation": "get",
                        "key": key,
                        "value": self.scratchpad[key]["value"],
                        "timestamp": now,
                    }
                return {
                    "status": "error",
                    "error": {
                        "code": "KEY_NOT_FOUND",
                        "message": f"Key '{key}' not found",
                    },
                }
            case "list":
                if not self.scratchpad:
                    return {
                        "operation": "list",
                        "items": [],
                        "timestamp": now,
                    }
                return {
                    "operation": "list",
                    "items": [
                        {
                            "key": k,
                            "value": v.get("value"),
                            "updated": v.get("updated"),
                            "intent": v.get("intent"),
                        }
                        for k, v in self.scratchpad.items()
                    ],
                    "timestamp": now,
                }
            case "clear":
                if key == "all":
                    self.scratchpad.clear()
                    self.clear_scratchpad_db()
                    self.persist_tool_event(
                        tool_name="use_scratchpad",
                        intent=intent,
                        timestamp=now,
                        payload={"operation": "clear", "key": "all"},
                    )
                    return {
                        "operation": "clear",
                        "key": "all",
                        "timestamp": now,
                    }
                self.scratchpad.pop(key, None)
                self.delete_scratchpad_item_db(key)
                self.persist_tool_event(
                    tool_name="use_scratchpad",
                    intent=intent,
                    timestamp=now,
                    payload={"operation": "clear", "key": key},
                )
                return {
                    "operation": "clear",
                    "key": key,
                    "timestamp": now,
                }
            case _:
                return {
                    "status": "error",
                    "error": {
                        "code": "UNSUPPORTED_OPERATION",
                        "message": (
                            "Supported operations: get, set, list, clear"
                        ),
                    },
                }

    def evaluate(self, intent: str) -> Dict[str, Any]:
        """
        Quick quality assessment of the reasoning chain.

        Returns:
            Dict[str, Any]: JSON-compatible evaluation payload
        """
        n_steps = len(self.steps)
        n_refl = len(self.reflections)
        avg_conf = (
            sum(self.confidence_trajectory) / len(self.confidence_trajectory)
            if self.confidence_trajectory
            else 0
        )

        score = min(10, n_steps + n_refl * 2 + int(avg_conf * 10)) // 3

        recommendations: List[str] = []
        if n_steps < 4:
            recommendations.append("Consider more steps")
        if n_refl == 0:
            recommendations.append("Add at least one reflection")
        if avg_conf < 0.6:
            recommendations.append("Low confidence — gather more evidence?")

        now = datetime.now().isoformat()
        self.persist_tool_event(
            tool_name="evaluate_reasoning",
            intent=intent,
            timestamp=now,
            payload={"quality_score": score},
        )

        return {
            "quality_score": score,
            "steps_count": n_steps,
            "reflections_count": n_refl,
            "average_confidence": avg_conf,
            "recommendations": recommendations,
            "intent": intent,
            "timestamp": now,
        }

    def summary(self, intent: str) -> Dict[str, Any]:
        """
        Current state overview.

        Returns:
            Dict[str, Any]: JSON-compatible summary payload
        """
        avg_conf = (
            sum(self.confidence_trajectory) / len(self.confidence_trajectory)
            if self.confidence_trajectory
            else 0
        )
        now = datetime.now().isoformat()
        self.persist_tool_event(
            tool_name="get_reasoning_summary",
            intent=intent,
            timestamp=now,
            payload=None,
        )
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "steps_count": len(self.steps),
            "reflections_count": len(self.reflections),
            "scratchpad_items_count": len(self.scratchpad),
            "average_confidence": avg_conf,
            "created_at": self.created_at,
            "last_updated": now,
            "intent": intent,
            "timestamp": now,
        }

    def reset(self, intent: str) -> Dict[str, Any]:
        """
        Clear all reasoning data in this session.

        Returns:
            Dict[str, Any]: JSON-compatible reset confirmation
        """
        self.steps.clear()
        self.reflections.clear()
        self.scratchpad.clear()
        self.confidence_trajectory.clear()
        # Persist reset to database
        self.reset_db()
        now = datetime.now().isoformat()
        self.persist_tool_event(
            tool_name="reset_reasoning",
            intent=intent,
            timestamp=now,
            payload=None,
        )
        return {
            "message": "Reasoning session reset successfully",
            "intent": intent,
            "timestamp": now,
        }

    def _detect_biases(self, text: str) -> List[str]:
        """
        Detect potential cognitive biases in text.

        Args:
            text (str): Text to analyze

        Returns:
            List[str]: List of detected bias types
        """
        text = text.lower()
        return [
            bias
            for bias, words in BIAS_PATTERNS.items()
            if any(w in text for w in words)
        ]

    def set_database(self, db: "ReasoningDatabase") -> None:
        """Set database instance for persistence."""
        self._db = db

    def to_dict(self) -> Dict:
        """Serialize session to dictionary for storage."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "steps": self.steps,
            "reflections": self.reflections,
            "scratchpad": self.scratchpad,
            "tool_events": self.tool_events,
            "confidence_trajectory": self.confidence_trajectory,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReasoningSession":
        """Deserialize session from dictionary."""
        session = cls(
            session_id=data.get("session_id"), agent_id=data.get("agent_id")
        )
        session.id = data["id"]
        session.created_at = data["created_at"]
        session.steps = data.get("steps", [])
        session.reflections = data.get("reflections", [])
        session.scratchpad = data.get("scratchpad", {})
        session.tool_events = data.get("tool_events", [])
        session.confidence_trajectory = data.get("confidence_trajectory", [])
        return session

    def persist_metadata(self) -> None:
        """Persist session metadata to database."""
        if self._db and self.session_id and self.agent_id:
            self._db.save_session_metadata(
                self.id, self.session_id, self.agent_id, self.created_at
            )

    def persist_step(self, step: Dict) -> None:
        """Persist a step to database."""
        if self._db:
            self._db.save_step(self.id, step)

    def persist_reflection(self, reflection: Dict) -> None:
        """Persist a reflection to database."""
        if self._db:
            self._db.save_reflection(self.id, reflection)

    def persist_scratchpad_item(self, key: str, value_dict: Dict) -> None:
        """Persist a scratchpad item to database."""
        if self._db:
            self._db.save_scratchpad_item(
                self.id,
                key,
                value_dict["value"],
                value_dict["updated"],
                value_dict.get("intent"),
            )

    def persist_tool_event(
        self,
        tool_name: str,
        intent: str,
        timestamp: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a tool call event to database and local memory."""
        event = {
            "tool_name": tool_name,
            "intent": intent,
            "timestamp": timestamp,
            "payload": payload,
        }
        self.tool_events.append(event)
        if self._db:
            self._db.save_tool_event(
                session_internal_id=self.id,
                tool_name=tool_name,
                intent=intent,
                timestamp=timestamp,
                payload=payload,
            )

    def delete_scratchpad_item_db(self, key: str) -> None:
        """Delete a scratchpad item from database."""
        if self._db:
            self._db.delete_scratchpad_item(self.id, key)

    def clear_scratchpad_db(self) -> None:
        """Clear scratchpad in database."""
        if self._db:
            self._db.clear_scratchpad(self.id)

    def reset_db(self) -> None:
        """Reset session in database."""
        if self._db:
            self._db.reset_session(self.id)
