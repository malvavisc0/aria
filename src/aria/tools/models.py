"""Shared SQLAlchemy base for all tool models.

All tool modules that need database persistence should import Base
from this module rather than defining their own DeclarativeBase.
This ensures all tool tables share the same metadata and can coexist
in the same database file.

Note: This is separate from aria.db.models.Base which is used for
the Chainlit UI database - Users, Threads, Steps, etc.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all tool SQLAlchemy models."""

    pass
