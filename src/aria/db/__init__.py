"""Database layer for Aria application.

Provides:
- SQLite-compatible Chainlit data layer
- Local filesystem storage client
- User authentication utilities
- SQLAlchemy models

Example:
    >>> from aria.db import SQLiteSQLAlchemyDataLayer, LocalStorageClient
    >>> from aria.db import hash_password, verify_password

    # Set up data layer
    data_layer = SQLiteSQLAlchemyDataLayer("sqlite:///./data/aria.db")

    # Set up local storage
    storage = LocalStorageClient(".files/storage")

    # Hash a password
    hashed = hash_password("secret")
    >>> verify_password("secret", hashed)
    True
"""

from aria.db.auth import hash_password, verify_password
from aria.db.layer import SQLiteSQLAlchemyDataLayer
from aria.db.local_storage_client import LocalStorageClient
from aria.db.models import Base, Element, Feedback, Step, Thread, User

__all__ = [
    # Authentication
    "hash_password",
    "verify_password",
    # Data layer
    "SQLiteSQLAlchemyDataLayer",
    # Storage
    "LocalStorageClient",
    # Models
    "Base",
    "User",
    "Thread",
    "Step",
    "Element",
    "Feedback",
]
