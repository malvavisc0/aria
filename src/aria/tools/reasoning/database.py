"""Database operations for reasoning persistence using SQLAlchemy."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from aria.config.folders import Data

from .models import (
    Base,
    ReasoningReflectionModel,
    ReasoningScratchpadModel,
    ReasoningSessionModel,
    ReasoningStepModel,
    ReasoningToolEventModel,
)

_DEFAULT_DB_PATH = str(Data.path / "reasoning.db")


class ReasoningDatabase:
    """Database manager for reasoning sessions using SQLAlchemy."""

    # Instance initialization flag (set in __new__/__init__)
    _initialized: bool

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls, db_path: str = _DEFAULT_DB_PATH):
        """Singleton pattern for database instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = _DEFAULT_DB_PATH):
        """Initialize database connection."""
        # Ensure the attribute exists before accessing it (pylint-friendly).
        self._initialized = getattr(self, "_initialized", False)
        if self._initialized:
            return

        self.db_path = db_path
        self._ensure_directory()
        self._setup_engine()
        self._create_tables()
        self._initialized = True
        logger.info(f"ReasoningDatabase initialized at {db_path}")

    def _ensure_directory(self) -> None:
        """Create database directory if it doesn't exist."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _setup_engine(self) -> None:
        """Setup SQLAlchemy engine and session factory."""
        # Create engine with SQLite
        database_url = f"sqlite:///{self.db_path}"
        self._engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
        )

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False
        )

        logger.debug(f"Database engine created: {database_url}")

    def _create_tables(self) -> None:
        """Create all tables if they don't exist."""
        assert self._engine is not None
        Base.metadata.create_all(self._engine)
        logger.debug("Database tables created/verified")

    def get_session(self) -> Session:
        """Get a new database session."""
        assert self._session_factory is not None
        return self._session_factory()

    def save_session_metadata(
        self,
        internal_id: str,
        session_id: str,
        agent_id: str,
        created_at: str,
    ) -> None:
        """Save or update session metadata."""
        with self.get_session() as session:
            # Check if session exists
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.id == internal_id
            )
            existing = session.execute(stmt).scalar_one_or_none()

            if existing:
                # Update existing
                existing.updated_at = datetime.utcnow()
                existing.is_active = True
            else:
                # Create new
                new_session = ReasoningSessionModel(
                    id=internal_id,
                    session_id=session_id,
                    agent_id=agent_id,
                    created_at=datetime.fromisoformat(created_at),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                )
                session.add(new_session)

            session.commit()
            logger.debug(
                f"Saved session metadata: {session_id} for agent {agent_id}"
            )

    def load_session(self, session_id: str, agent_id: str) -> Optional[Dict]:
        """Load complete session data from database."""
        with self.get_session() as session:
            # Get session with all relationships
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.session_id == session_id,
                ReasoningSessionModel.agent_id == agent_id,
                ReasoningSessionModel.is_active == True,  # noqa: E712
            )
            session_model = session.execute(stmt).scalar_one_or_none()

            if not session_model:
                return None

            internal_id = session_model.id

            # Convert steps to dict
            steps = []
            for step in session_model.steps:
                steps.append(
                    {
                        "id": step.step_number,
                        "cognitive_mode": step.cognitive_mode,
                        "reasoning_type": step.reasoning_type,
                        "content": step.content,
                        "confidence": step.confidence,
                        "intent": getattr(step, "intent", None),
                        "evidence": (
                            json.loads(step.evidence) if step.evidence else []
                        ),
                        "biases_detected": (
                            json.loads(step.biases_detected)
                            if step.biases_detected
                            else []
                        ),
                        "timestamp": step.timestamp.isoformat(),
                    }
                )

            # Convert reflections to dict
            reflections = []
            for refl in session_model.reflections:
                reflections.append(
                    {
                        "content": refl.content,
                        "step_id": refl.step_id,
                        "intent": getattr(refl, "intent", None),
                        "timestamp": refl.timestamp.isoformat(),
                    }
                )

            # Convert scratchpad to dict
            scratchpad = {}
            for item in session_model.scratchpad_items:
                scratchpad[item.key] = {
                    "value": item.value,
                    "updated": item.updated_at.isoformat(),
                    "intent": getattr(item, "intent", None),
                }

            # Convert tool events to dict
            tool_events = []
            for ev in getattr(session_model, "tool_events", []) or []:
                tool_events.append(
                    {
                        "tool_name": ev.tool_name,
                        "intent": ev.intent,
                        "payload": (
                            json.loads(ev.payload_json)
                            if ev.payload_json
                            else None
                        ),
                        "timestamp": ev.timestamp.isoformat(),
                    }
                )

            # Build session data
            session_data = {
                "id": internal_id,
                "session_id": session_model.session_id,
                "agent_id": session_model.agent_id,
                "created_at": session_model.created_at.isoformat(),
                "steps": steps,
                "reflections": reflections,
                "scratchpad": scratchpad,
                "tool_events": tool_events,
                "confidence_trajectory": [
                    step["confidence"] for step in steps
                ],
            }

            logger.debug(f"Loaded session {session_id} for agent {agent_id}")
            return session_data

    def save_step(self, session_internal_id: str, step: Dict) -> None:
        """Save a reasoning step."""
        with self.get_session() as session:
            step_model = ReasoningStepModel(
                session_id=session_internal_id,
                step_number=step["id"],
                cognitive_mode=step["cognitive_mode"],
                reasoning_type=step["reasoning_type"],
                content=step["content"],
                confidence=step["confidence"],
                intent=step.get("intent"),
                evidence=json.dumps(step["evidence"]),
                biases_detected=json.dumps(step["biases_detected"]),
                timestamp=datetime.fromisoformat(step["timestamp"]),
            )
            session.add(step_model)

            # Update session timestamp
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.id == session_internal_id
            )
            session_model = session.execute(stmt).scalar_one()
            session_model.updated_at = datetime.utcnow()

            session.commit()
            logger.debug(
                f"Saved step {step['id']} for session {session_internal_id}"
            )

    def save_reflection(
        self, session_internal_id: str, reflection: Dict
    ) -> None:
        """Save a reflection."""
        with self.get_session() as session:
            refl_model = ReasoningReflectionModel(
                session_id=session_internal_id,
                content=reflection["content"],
                step_id=reflection.get("step_id"),
                intent=reflection.get("intent"),
                timestamp=datetime.fromisoformat(reflection["timestamp"]),
            )
            session.add(refl_model)

            # Update session timestamp
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.id == session_internal_id
            )
            session_model = session.execute(stmt).scalar_one()
            session_model.updated_at = datetime.utcnow()

            session.commit()
            logger.debug(f"Saved reflection for session {session_internal_id}")

    def save_scratchpad_item(
        self,
        session_internal_id: str,
        key: str,
        value: str,
        updated_at: str,
        intent: Optional[str] = None,
    ) -> None:
        """Save or update a scratchpad item."""
        with self.get_session() as session:
            # Check if item exists
            stmt = select(ReasoningScratchpadModel).where(
                ReasoningScratchpadModel.session_id == session_internal_id,
                ReasoningScratchpadModel.key == key,
            )
            existing = session.execute(stmt).scalar_one_or_none()

            if existing:
                existing.value = value
                existing.updated_at = datetime.fromisoformat(updated_at)
                if intent is not None:
                    existing.intent = intent
            else:
                item = ReasoningScratchpadModel(
                    session_id=session_internal_id,
                    key=key,
                    value=value,
                    updated_at=datetime.fromisoformat(updated_at),
                    intent=intent,
                )
                session.add(item)

            session.commit()
            logger.debug(
                f"Saved scratchpad item {key} for session "
                f"{session_internal_id}"
            )

    def save_tool_event(
        self,
        session_internal_id: str,
        tool_name: str,
        intent: str,
        timestamp: str,
        payload: Optional[Dict] = None,
    ) -> None:
        """Persist an audit event for a tool call."""
        with self.get_session() as session:
            ev = ReasoningToolEventModel(
                session_id=session_internal_id,
                tool_name=tool_name,
                intent=intent,
                payload_json=(
                    json.dumps(payload) if payload is not None else None
                ),
                timestamp=datetime.fromisoformat(timestamp),
            )
            session.add(ev)

            # Update session timestamp
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.id == session_internal_id
            )
            session_model = session.execute(stmt).scalar_one()
            session_model.updated_at = datetime.utcnow()

            session.commit()
            logger.debug(
                f"Saved tool event {tool_name} for session {session_internal_id}",
            )

    def delete_scratchpad_item(
        self, session_internal_id: str, key: str
    ) -> None:
        """Delete a scratchpad item."""
        with self.get_session() as session:
            stmt = select(ReasoningScratchpadModel).where(
                ReasoningScratchpadModel.session_id == session_internal_id,
                ReasoningScratchpadModel.key == key,
            )
            item = session.execute(stmt).scalar_one_or_none()

            if item:
                session.delete(item)
                session.commit()
                logger.debug(
                    f"Deleted scratchpad item {key} for session "
                    f"{session_internal_id}"
                )

    def clear_scratchpad(self, session_internal_id: str) -> None:
        """Clear all scratchpad items for a session."""
        with self.get_session() as session:
            stmt = select(ReasoningScratchpadModel).where(
                ReasoningScratchpadModel.session_id == session_internal_id
            )
            items = session.execute(stmt).scalars().all()

            for item in items:
                session.delete(item)

            session.commit()
            logger.debug(
                f"Cleared scratchpad for session {session_internal_id}"
            )

    def delete_session(self, session_id: str, agent_id: str) -> bool:
        """Mark session as inactive (soft delete)."""
        with self.get_session() as session:
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.session_id == session_id,
                ReasoningSessionModel.agent_id == agent_id,
            )
            session_model = session.execute(stmt).scalar_one_or_none()

            if session_model:
                session_model.is_active = False
                session.commit()
                logger.debug(
                    f"Deleted session {session_id} for agent {agent_id}"
                )
                return True

            return False

    def reset_session(self, session_internal_id: str) -> None:
        """Clear all steps, reflections, and scratchpad for a session."""
        with self.get_session() as session:
            # Delete all related data
            stmt = select(ReasoningStepModel).where(
                ReasoningStepModel.session_id == session_internal_id
            )
            steps = session.execute(stmt).scalars().all()
            for step in steps:
                session.delete(step)

            stmt = select(ReasoningReflectionModel).where(
                ReasoningReflectionModel.session_id == session_internal_id
            )
            reflections = session.execute(stmt).scalars().all()
            for refl in reflections:
                session.delete(refl)

            stmt = select(ReasoningScratchpadModel).where(
                ReasoningScratchpadModel.session_id == session_internal_id
            )
            items = session.execute(stmt).scalars().all()
            for item in items:
                session.delete(item)

            # Update session timestamp
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.id == session_internal_id
            )
            session_model = session.execute(stmt).scalar_one()
            session_model.updated_at = datetime.utcnow()

            session.commit()
            logger.debug(f"Reset session {session_internal_id}")

    def list_sessions(self, agent_id: Optional[str] = None) -> List[Dict]:
        """List all active sessions, optionally filtered by agent."""
        with self.get_session() as session:
            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.is_active == True  # noqa: E712
            )

            if agent_id:
                stmt = stmt.where(ReasoningSessionModel.agent_id == agent_id)

            stmt = stmt.order_by(ReasoningSessionModel.updated_at.desc())

            sessions = session.execute(stmt).scalars().all()

            return [
                {
                    "session_id": s.session_id,
                    "agent_id": s.agent_id,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ]

    def cleanup_old_sessions(
        self, days: int = 30, agent_id: Optional[str] = None
    ) -> int:
        """Permanently delete inactive sessions older than specified days."""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            stmt = select(ReasoningSessionModel).where(
                ReasoningSessionModel.is_active == False,  # noqa: E712
                ReasoningSessionModel.updated_at < cutoff_date,
            )

            if agent_id:
                stmt = stmt.where(ReasoningSessionModel.agent_id == agent_id)

            old_sessions = session.execute(stmt).scalars().all()
            count = len(old_sessions)

            for old_session in old_sessions:
                session.delete(old_session)

            session.commit()
            logger.info(f"Cleaned up {count} old sessions")
            return count

    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            logger.debug("Database connections closed")


# Global database instance
_db_instance = None


def get_database() -> ReasoningDatabase:
    """Get global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ReasoningDatabase()
    return _db_instance
