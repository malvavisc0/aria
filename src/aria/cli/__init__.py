"""CLI utilities for the Aria application.

This module provides shared utilities for CLI commands including:
- Database session management with automatic commit/rollback

Example:
    ```python
    from aria.cli import get_db_session

    with get_db_session() as session:
        # Perform database operations
        session.execute(text("SELECT 1"))
    ```
"""

import contextlib

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from aria.config.database import SQLite
from aria.db.models import Base


@contextlib.contextmanager
def get_db_session():
    """Context manager for database sessions with automatic transaction handling.

    Creates a new SQLAlchemy session, commits on success, rolls back on error,
    and always closes the session on exit.

    Yields:
        Session: An active SQLAlchemy session for database operations.

    Raises:
        Exception: Re-raises any exception that occurs during the session,
            after rolling back the transaction.

    Example:
        ```python
        with get_db_session() as session:
            users = session.execute(select(User)).scalars().all()
        ```
    """
    engine = create_engine(SQLite.db_url)
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
