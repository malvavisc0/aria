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

from typing import Annotated

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Type aliases for common column patterns
str_pk = Annotated[str, mapped_column(String(36), primary_key=True)]
str_36 = Annotated[str, mapped_column(String(36))]
str_fk_user = Annotated[
    str, mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
]
str_fk_thread = Annotated[
    str,
    mapped_column(String(36), ForeignKey("threads.id", ondelete="CASCADE")),
]


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class User(Base):
    """User model for authentication and thread ownership."""

    __tablename__ = "users"

    id: Mapped[str_pk]
    identifier: Mapped[str] = mapped_column(Text, unique=True)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    metadata_: Mapped[str] = mapped_column("metadata", Text)
    createdAt: Mapped[str | None] = mapped_column(Text)
    # Hashed password (PBKDF2-SHA256 format: salt$hash)
    password: Mapped[str | None] = mapped_column(Text)

    # Relationships
    threads: Mapped[list["Thread"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Thread(Base):
    """Thread model representing a conversation thread."""

    __tablename__ = "threads"

    id: Mapped[str_pk]
    createdAt: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    userId: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    userIdentifier: Mapped[str | None] = mapped_column(Text)
    # `TEXT[]` in the source schema. Chainlit currently passes Python `list[str]`
    # for SQLite, which cannot be bound by sqlite3/aiosqlite.
    # Our custom data layer will `json.dumps(tags)` on write and `json.loads` on read.
    tags: Mapped[str | None] = mapped_column(Text)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    metadata_: Mapped[str | None] = mapped_column("metadata", Text)

    # Relationships
    user: Mapped["User | None"] = relationship(back_populates="threads")
    steps: Mapped[list["Step"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    elements: Mapped[list["Element"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
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
    """Step model representing individual steps in a conversation thread."""

    __tablename__ = "steps"

    id: Mapped[str_pk]
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    threadId: Mapped[str_fk_thread]
    parentId: Mapped[str | None] = mapped_column(String(36))
    streaming: Mapped[bool] = mapped_column(Boolean)
    waitForAnswer: Mapped[bool | None] = mapped_column(Boolean)
    isError: Mapped[bool | None] = mapped_column(Boolean)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    metadata_: Mapped[str | None] = mapped_column("metadata", Text)
    # `TEXT[]` in the source schema; stored as JSON string for SQLite.
    tags: Mapped[str | None] = mapped_column(Text)
    input: Mapped[str | None] = mapped_column(Text)
    output: Mapped[str | None] = mapped_column(Text)
    createdAt: Mapped[str | None] = mapped_column(Text)
    command: Mapped[str | None] = mapped_column(Text)
    start: Mapped[str | None] = mapped_column(Text)
    end: Mapped[str | None] = mapped_column(Text)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    generation: Mapped[str | None] = mapped_column(Text)
    showInput: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    indent: Mapped[int | None] = mapped_column(Integer)
    defaultOpen: Mapped[bool | None] = mapped_column(Boolean)

    # Relationships
    thread: Mapped["Thread"] = relationship(back_populates="steps")

    # Indexes for performance
    __table_args__ = (
        Index("ix_steps_threadId", "threadId"),
        Index("ix_steps_createdAt", "createdAt"),
    )


class Element(Base):
    """Element model representing attachments or media in a thread."""

    __tablename__ = "elements"

    id: Mapped[str_pk]
    threadId: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("threads.id", ondelete="CASCADE")
    )
    type: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    chainlitKey: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    display: Mapped[str | None] = mapped_column(Text)
    objectKey: Mapped[str | None] = mapped_column(Text)
    size: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(Text)
    forId: Mapped[str | None] = mapped_column(String(36))
    mime: Mapped[str | None] = mapped_column(Text)
    # Stored as JSON string (Chainlit serializes via `json.dumps`).
    props: Mapped[str | None] = mapped_column(Text)

    # Relationships
    thread: Mapped["Thread | None"] = relationship(back_populates="elements")

    # Indexes for performance
    __table_args__ = (
        Index("ix_elements_threadId", "threadId"),
        Index("ix_elements_forId", "forId"),
    )


class Feedback(Base):
    """Feedback model for user feedback on steps."""

    __tablename__ = "feedbacks"

    id: Mapped[str_pk]
    forId: Mapped[str] = mapped_column(String(36))
    threadId: Mapped[str_fk_thread]
    value: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)

    # Relationships
    thread: Mapped["Thread"] = relationship(back_populates="feedbacks")

    # Indexes for performance
    __table_args__ = (
        Index("ix_feedbacks_threadId", "threadId"),
        Index("ix_feedbacks_forId", "forId"),
    )
