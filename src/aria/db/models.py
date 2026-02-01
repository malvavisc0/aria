"""SQLAlchemy models matching [`data.layer.sql`](data.layer.sql:1).

These models are intended for **SQLite**.

Notes
-----
- The upstream schema uses Postgres types (`UUID`, `JSONB`, `TEXT[]`).
  For SQLite we store UUIDs as `String(36)`.
- Chainlit's [`SQLAlchemyDataLayer`](.venv/lib/python3.12/site-packages/chainlit/data/sql_alchemy.py:1)
  serializes JSON fields with `json.dumps(...)` and sends them as **strings**
  (not Python dicts). For SQLite compatibility, JSON-like columns are modeled
  as `Text`.
- Column name `metadata` is reserved by SQLAlchemy's Declarative API, so we map
  it to a safe Python attribute `metadata_` while keeping the DB column name
  exactly `metadata`.
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    identifier = Column(Text, nullable=False, unique=True)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    metadata_ = Column("metadata", Text, nullable=False)
    createdAt = Column(Text)
    # Hashed password (PBKDF2-SHA256 format: salt$hash)
    password = Column(Text, nullable=True)

    # Relationships
    threads = relationship(
        "Thread", back_populates="user", cascade="all, delete-orphan"
    )


class Thread(Base):
    __tablename__ = "threads"

    id = Column(String(36), primary_key=True)
    createdAt = Column(Text)
    name = Column(Text)
    userId = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    userIdentifier = Column(Text)
    # `TEXT[]` in the source schema. Chainlit currently passes Python `list[str]`
    # for SQLite, which cannot be bound by sqlite3/aiosqlite.
    # Our custom data layer will `json.dumps(tags)` on write and `json.loads` on read.
    tags = Column(Text)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    metadata_ = Column("metadata", Text)

    # Relationships
    user = relationship("User", back_populates="threads")
    steps = relationship(
        "Step",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    elements = relationship(
        "Element",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedbacks = relationship(
        "Feedback",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_threads_userId", "userId"),
        Index("ix_threads_createdAt", "createdAt"),
    )


class Step(Base):
    __tablename__ = "steps"

    id = Column(String(36), primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    threadId = Column(
        String(36),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    parentId = Column(String(36))
    streaming = Column(Boolean, nullable=False)
    waitForAnswer = Column(Boolean)
    isError = Column(Boolean)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    metadata_ = Column("metadata", Text)
    # `TEXT[]` in the source schema; stored as JSON string for SQLite.
    tags = Column(Text)
    input = Column(Text)
    output = Column(Text)
    createdAt = Column(Text)
    command = Column(Text)
    start = Column(Text)
    end = Column(Text)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    generation = Column(Text)
    showInput = Column(Text)
    language = Column(Text)
    indent = Column(Integer)
    defaultOpen = Column(Boolean)

    # Relationships
    thread = relationship("Thread", back_populates="steps")

    # Indexes for performance
    __table_args__ = (
        Index("ix_steps_threadId", "threadId"),
        Index("ix_steps_createdAt", "createdAt"),
    )


class Element(Base):
    __tablename__ = "elements"

    id = Column(String(36), primary_key=True)
    threadId = Column(
        String(36),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=True,
    )
    type = Column(Text)
    url = Column(Text)
    chainlitKey = Column(Text)
    name = Column(Text, nullable=False)
    display = Column(Text)
    objectKey = Column(Text)
    size = Column(Text)
    page = Column(Integer)
    language = Column(Text)
    forId = Column(String(36))
    mime = Column(Text)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    props = Column(Text)

    # Relationships
    thread = relationship("Thread", back_populates="elements")

    # Indexes for performance
    __table_args__ = (
        Index("ix_elements_threadId", "threadId"),
        Index("ix_elements_forId", "forId"),
    )


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(String(36), primary_key=True)
    forId = Column(String(36), nullable=False)
    threadId = Column(
        String(36),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    value = Column(Integer, nullable=False)
    comment = Column(Text)

    # Relationships
    thread = relationship("Thread", back_populates="feedbacks")

    # Indexes for performance
    __table_args__ = (
        Index("ix_feedbacks_threadId", "threadId"),
        Index("ix_feedbacks_forId", "forId"),
    )
