import uuid
from typing import List

from tortoise import fields
from tortoise.models import Model


class Session(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(max_length=255, null=True)
    created = fields.DatetimeField(auto_now_add=True)

    # Password protection
    password_hash = fields.CharField(max_length=255, null=True)  # bcrypt hash, nullable

    # Relationship to messages
    messages: fields.ReverseRelation["Message"]

    @property
    def is_protected(self) -> bool:
        return self.password_hash is not None

    def __str__(self):
        return f"Session({self.id}, {self.name})"


class Message(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    session = fields.ForeignKeyField(
        "models.Session", related_name="messages", on_delete=fields.CASCADE,
        index=True  # Add index for faster session-based queries
    )
    content = fields.TextField()
    role = fields.CharField(max_length=20)  # "user" or "assistant"
    timestamp = fields.DatetimeField(auto_now_add=True, index=True)  # Add index for pagination
    files = fields.JSONField(default=list)  # List of file metadata

    def __str__(self):
        return f"Message({self.id}, {self.role}, {self.content[:50]}...)"
