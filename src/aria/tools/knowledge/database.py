"""Database operations for knowledge store persistence."""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import select

from aria.tools.database import get_tools_database

from .models import KnowledgeEntryModel


class KnowledgeDatabase:
    """Database manager for knowledge store persistence."""

    _initialized: bool
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, "_initialized", False)
        if self._initialized:
            return

        self._tools_db = get_tools_database()
        self._tools_db.create_tables()
        self._initialized = True
        logger.info("KnowledgeDatabase initialized")

    def get_session(self):
        return self._tools_db.get_session()

    def store(
        self,
        entry_id: str,
        agent_id: str,
        key: str,
        value: str,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Store a new knowledge entry."""
        with self.get_session() as session:
            entry = KnowledgeEntryModel(
                id=entry_id,
                agent_id=agent_id,
                key=key,
                value=value,
                tags=json.dumps(tags) if tags else None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True,
            )
            session.add(entry)
            session.commit()
            logger.debug(f"Stored knowledge entry {entry_id} with key '{key}'")

    def recall(self, agent_id: str, key: str) -> Optional[Dict]:
        """Recall a knowledge entry by key."""
        with self.get_session() as session:
            stmt = (
                select(KnowledgeEntryModel)
                .where(
                    KnowledgeEntryModel.agent_id == agent_id,
                    KnowledgeEntryModel.key == key,
                    KnowledgeEntryModel.is_active.is_(True),
                )
                .order_by(KnowledgeEntryModel.updated_at.desc())
            )
            entry = session.execute(stmt).scalar_one_or_none()

            if entry is None:
                return None

            return {
                "id": entry.id,
                "key": entry.key,
                "value": entry.value,
                "tags": json.loads(entry.tags) if entry.tags else [],
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }

    def search(
        self,
        agent_id: str,
        query: str,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search knowledge entries by key or value substring."""
        with self.get_session() as session:
            pattern = f"%{query}%"
            stmt = (
                select(KnowledgeEntryModel)
                .where(
                    KnowledgeEntryModel.agent_id == agent_id,
                    KnowledgeEntryModel.is_active.is_(True),
                )
                .where(
                    KnowledgeEntryModel.key.ilike(pattern)
                    | KnowledgeEntryModel.value.ilike(pattern)
                )
                .order_by(KnowledgeEntryModel.updated_at.desc())
                .limit(max_results)
            )
            entries = session.execute(stmt).scalars().all()

            return [
                {
                    "id": e.id,
                    "key": e.key,
                    "value": e.value,
                    "tags": json.loads(e.tags) if e.tags else [],
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                }
                for e in entries
            ]

    def list_entries(
        self,
        agent_id: str,
        tag: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict]:
        """List all knowledge entries for an agent."""
        with self.get_session() as session:
            stmt = select(KnowledgeEntryModel).where(
                KnowledgeEntryModel.agent_id == agent_id,
                KnowledgeEntryModel.is_active.is_(True),
            )

            if tag:
                stmt = stmt.where(KnowledgeEntryModel.tags.contains(tag))

            stmt = stmt.order_by(KnowledgeEntryModel.updated_at.desc()).limit(
                max_results
            )
            entries = session.execute(stmt).scalars().all()

            return [
                {
                    "id": e.id,
                    "key": e.key,
                    "value": e.value,
                    "tags": json.loads(e.tags) if e.tags else [],
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                }
                for e in entries
            ]

    def update(self, entry_id: str, agent_id: str, value: str) -> bool:
        """Update a knowledge entry's value."""
        with self.get_session() as session:
            stmt = select(KnowledgeEntryModel).where(
                KnowledgeEntryModel.id == entry_id,
                KnowledgeEntryModel.agent_id == agent_id,
                KnowledgeEntryModel.is_active.is_(True),
            )
            entry = session.execute(stmt).scalar_one_or_none()

            if entry is None:
                return False

            entry.value = value
            entry.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.debug(f"Updated knowledge entry {entry_id}")
            return True

    def delete(self, entry_id: str, agent_id: str) -> bool:
        """Soft-delete a knowledge entry."""
        with self.get_session() as session:
            stmt = select(KnowledgeEntryModel).where(
                KnowledgeEntryModel.id == entry_id,
                KnowledgeEntryModel.agent_id == agent_id,
                KnowledgeEntryModel.is_active.is_(True),
            )
            entry = session.execute(stmt).scalar_one_or_none()

            if entry is None:
                return False

            entry.is_active = False
            entry.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.debug(f"Deleted knowledge entry {entry_id}")
            return True


def get_database() -> KnowledgeDatabase:
    """Get the knowledge database singleton."""
    return KnowledgeDatabase()
