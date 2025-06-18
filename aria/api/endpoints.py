import time
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from aria.ai import ollama_core_agent
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
import httpx
import os

router = APIRouter()

startup_time = time.time()


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    ollama_url = os.getenv("OLLAMA_URL")
    if not ollama_url:
        raise HTTPException(status_code=500, detail="OLLAMA_URL is not set")
    
    response = httpx.get(url=ollama_url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ollama is not available")
    
    uptime = int(time.time() - startup_time)
    return HealthResponse(
        status="ok",
        model="ready",
        uptime=uptime,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    


@router.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all chat sessions"""
    sessions = await SessionService.list_sessions()
    for session in sessions:
        session.user_message_count = await MessageService.count_user_messages(session.id)
    return sessions


@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(session_data: SessionCreate):
    """Create a new session"""
    session = await SessionService.create_session(session_data)
    session.user_message_count = 0  # New session has no messages
    return session


@router.get("/api/sessions/{session_id}", response_model=SessionWithMessages)
async def get_session(session_id: str):
    """Get session details and all messages"""
    session = await SessionService.get_session_with_messages(session_id)
    session.user_message_count = await MessageService.count_user_messages(session_id)
    return session


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
)
async def send_message(
    session_id: str,
    message: str = Form(...),
    role: str = Form("user"),
    files: List[UploadFile] = File(default=[]),
) -> StreamingResponse:
    """Send a new message (text and/or files) and get assistant response"""
    user_message_data = MessageCreate(
        content=message, role=role, files=[]  # TODO: Handle file uploads properly
    )

    # Save user message
    await MessageService.create_message(session_id, user_message_data)

    # Stream assistant response and collect full content
    assistant_content = ""

    async def stream_response():
        nonlocal assistant_content
        agent = ollama_core_agent(user_id=role, session_id=session_id, enable_memory=True)
        response = await agent.arun(
            message=message, stream=True, user_id=role, session_id=session_id
        )

        # Stream chunks and collect content
        async for chunk in response:
            if chunk.content:
                chunk_str = str(chunk.content)
                assistant_content += chunk_str
                yield chunk_str

        # After streaming is complete, save assistant message to database
        if assistant_content:
            assistant_message_data = MessageCreate(
                content=assistant_content, role="assistant", files=[]
            )
            await MessageService.create_message(session_id, assistant_message_data)

    return StreamingResponse(stream_response(), media_type='text/event-stream')


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
    return ValidationResponse(valid=False, error="Invalid password")


@router.get("/api/sessions/search", response_model=List[SearchResponse])
async def search_messages(q: str):
    """Search messages, excluding protected sessions"""
    return await MessageService.search_messages(q)
