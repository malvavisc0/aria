import os
import time
from datetime import datetime, timezone
from os import environ
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import StreamingResponse

from aria.ai import ollama_core_agent
from aria.ai.agents import get_prompt_improver_agent
from aria.ai.outputs import ImprovedPromptResponse
from aria.schemas import (
    HealthResponse,
    MessageCreate,
    PaginatedMessagesResponse,
    PasswordResponse,
    SearchResponse,
    SessionCreate,
    SessionMetadataResponse,
    SessionPasswordRemove,
    SessionPasswordSet,
    SessionPasswordValidate,
    SessionResponse,
    ValidationResponse,
)
from aria.services import MessageService, PasswordService, SessionService

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


@router.get("/api/sessions/metadata", response_model=List[SessionMetadataResponse])
async def list_session_metadata():
    """List all chat sessions with metadata but without messages"""
    return await SessionService.list_session_metadata()


@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(session_data: SessionCreate):
    """Create a new session"""
    session = await SessionService.create_session(session_data)
    session.user_message_count = 0  # New session has no messages
    return session


@router.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """Delete a session and all its messages"""
    await SessionService.delete_session(session_id)


@router.get(
    "/api/sessions/{session_id}/messages/paginated",
    response_model=PaginatedMessagesResponse,
)
async def paginated_messages(
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
):
    """Get paginated messages for a session"""
    return await MessageService.paginated_messages(session_id, limit, cursor)


@router.post(
    "/api/sessions/{session_id}/messages",
)
async def send_message(
    session_id: str,
    message_data: MessageCreate,
) -> StreamingResponse:
    """Send a new message and get assistant response"""
    user_message_data = MessageCreate(
        content=message_data.content, role=message_data.role
    )

    # Save user message
    await MessageService.create_message(session_id, user_message_data)

    # Stream assistant response and collect full content
    assistant_content = ""

    async def stream_response():
        nonlocal assistant_content
        agent = ollama_core_agent(
            user_id=message_data.role, session_id=session_id, enable_memory=True
        )
        # Stream chunks and collect content
        async for chunk in agent.arun(input=message_data.content, stream=True):
            if chunk.content:
                chunk_str = str(chunk.content)
                assistant_content += chunk_str
                yield chunk_str

        # After streaming is complete, save assistant message to database
        if assistant_content:
            assistant_message_data = MessageCreate(
                content=assistant_content, role="assistant"
            )
            await MessageService.create_message(session_id, assistant_message_data)

    return StreamingResponse(stream_response(), media_type="text/event-stream")


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


@router.post("/api/improve-prompt", response_model=ImprovedPromptResponse)
async def improve_prompt(prompt_data: Dict[str, Any] = Body(...)):
    """
    Improve a prompt without changing its original meaning.

    This endpoint takes a user's prompt and returns an improved version that maintains
    the original intent but enhances clarity, structure, and effectiveness.

    Parameters:
    - prompt_data: A dictionary containing:
      - text: (required) The original prompt text to improve
      - target_model: (optional) The model the prompt is intended for
      - primary_focus: (optional) The main aspect to focus on (Clarity, Efficiency, Security, etc.)
      - preserve_intent: (optional) Whether to strictly preserve the original intent

    Returns:
    - A JSON response with both the original and improved prompts, along with an explanation
      of the changes made and technique(s) used
    """
    if "text" not in prompt_data:
        raise HTTPException(status_code=400, detail="Prompt text is required")

    original_prompt = prompt_data["text"]

    # Extract simple optional parameters with defaults
    target_model = prompt_data.get(
        "target_model", environ.get("OLLAMA_MODEL_ID", "cogito:8b")
    )
    primary_focus = prompt_data.get("primary_focus", "Clarity")
    preserve_intent = prompt_data.get("preserve_intent", True)

    # Construct a structured query using XML format
    message = f"""
<optimization_request>
  <original_prompt>
{original_prompt}
  </original_prompt>
  
  <target_model>{target_model}</target_model>
  <primary_focus>{primary_focus}</primary_focus>
  <preserve_intent>{"true" if preserve_intent else "false"}</preserve_intent>
</optimization_request>
"""

    # Get the prompt improver agent
    agent = get_prompt_improver_agent()

    # Run the agent to improve the prompt
    response = await agent.arun(input=message)

    # Return the improved prompt and explanation
    return response.content
