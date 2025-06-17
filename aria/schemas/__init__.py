import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    name: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    name: Optional[str]
    created: datetime
    is_protected: bool
    message_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    session_id: str
    content: str
    role: str
    timestamp: datetime
    files: List[dict] = []

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    files: List[dict] = []


class SessionWithMessages(BaseModel):
    id: str
    name: Optional[str]
    created: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    model: str
    uptime: int
    timestamp: str


class SearchResponse(BaseModel):
    message: MessageResponse
    session_name: Optional[str]
    session_id: str

    class Config:
        from_attributes = True


# Password-related schemas
class SessionPasswordSet(BaseModel):
    current_password: str  # Current password (empty string if no password set)
    new_password: str  # New password to set


class SessionPasswordRemove(BaseModel):
    current_password: Optional[str] = None


class SessionPasswordValidate(BaseModel):
    password: str


class PasswordResponse(BaseModel):
    success: bool
    message: str


class ValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
