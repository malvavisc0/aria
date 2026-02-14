"""CLI utilities for the Aria application.

This module provides shared utilities for CLI commands including:
- Database session management with automatic commit/rollback
- Console output helpers for consistent styling
- Error handling patterns for CLI commands

Example:
    ```python
    from aria.cli import get_db_session

    with get_db_session() as session:
        # Perform database operations
        session.execute(text("SELECT 1"))
    ```
"""

import contextlib

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from aria.config.database import SQLite
from aria.db.models import Base


@contextlib.contextmanager
def get_db_session():
    """Context manager for database sessions with automatic transaction handling.

    Creates a new SQLAlchemy session, handles commit/rollback automatically,
    and ensures proper cleanup on exit.

    Yields:
        Session: An active SQLAlchemy session for database operations.

    Raises:
        typer.Exit: Exits with code 1 if any exception occurs during operations.

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
        raise typer.Exit(1)
    finally:
        session.close()
