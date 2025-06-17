import time
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from aria.config import settings
from aria.models import Message, Session
from aria.schemas import (
    HealthResponse,
    MessageCreate,
    MessageResponse,
    PasswordResponse,
    SearchResponse,
    SessionCreate,
    SessionPasswordRemove,
    SessionPasswordSet,
    SessionPasswordValidate,
    SessionResponse,
    SessionWithMessages,
    ValidationResponse,
)
from aria.services import MessageService, PasswordService, SessionService

router = APIRouter()

startup_time = time.time()


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = int(time.time() - startup_time)
    return HealthResponse(
        status="ok",
        model="ready",
        uptime=uptime,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all chat sessions"""
    return await SessionService.list_sessions()


@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(session_data: SessionCreate):
    """Create a new session"""
    return await SessionService.create_session(session_data)


@router.get("/api/sessions/{session_id}", response_model=SessionWithMessages)
async def get_session(session_id: str):
    """Get session details and all messages"""
    return await SessionService.get_session_with_messages(session_id)


@router.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """Delete a session and all its messages"""
    await SessionService.delete_session(session_id)


@router.get("/api/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def list_messages(session_id: str):
    """List all messages in a session"""
    return await MessageService.list_messages(session_id)


@router.post(
    "/api/sessions/{session_id}/messages",
    response_model=List[MessageResponse],
    status_code=201,
)
async def send_message(
    session_id: str,
    content: str = Form(...),
    role: str = Form("user"),
    files: List[UploadFile] = File(default=[]),
):
    """Send a new message (text and/or files) and get assistant response"""
    # This is the endpoint we're NOT implementing - just placeholder
    raise HTTPException(status_code=501, detail="Message sending not implemented yet")


@router.delete("/api/sessions/{session_id}/messages/{message_id}", status_code=204)
async def delete_message(session_id: str, message_id: str):
    """Delete a specific message"""
    await MessageService.delete_message(session_id, message_id)


@router.put("/api/sessions/{session_id}/password", response_model=PasswordResponse)
async def set_session_password(session_id: str, password_data: SessionPasswordSet):
    """Set or change session password"""
    await PasswordService.set_session_password(
        session_id, password_data.current_password, password_data.new_password
    )
    return PasswordResponse(success=True, message="Password updated successfully")


@router.delete("/api/sessions/{session_id}/password", response_model=PasswordResponse)
async def remove_session_password(session_id: str, password_data: SessionPasswordRemove):
    """Remove session password"""
    await PasswordService.remove_session_password(
        session_id, password_data.current_password
    )
    return PasswordResponse(success=True, message="Password removed successfully")


@router.post("/api/sessions/{session_id}/validate", response_model=ValidationResponse)
async def validate_session_password(
    session_id: str, password_data: SessionPasswordValidate
):
    """Validate session password"""
    is_valid = await PasswordService.validate_session_password(
        session_id, password_data.password
    )
    if is_valid:
        return ValidationResponse(valid=True)
    else:
        return ValidationResponse(valid=False, error="Invalid password")


@router.get("/api/sessions/search", response_model=List[SearchResponse])
async def search_messages(q: str):
    """Search messages, excluding protected sessions"""
    return await MessageService.search_messages(q)
