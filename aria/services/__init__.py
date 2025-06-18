from typing import List, Optional

import bcrypt
from fastapi import HTTPException
from tortoise.exceptions import DoesNotExist

from aria.models import Message, Session
from aria.schemas import (
    MessageCreate,
    MessageResponse,
    PasswordResponse,
    SearchResponse,
    SessionCreate,
    SessionResponse,
    SessionWithMessages,
    ValidationResponse,
)


class SessionService:
    @staticmethod
    async def list_sessions() -> List[SessionResponse]:
        """List all sessions with message counts"""
        sessions = await Session.all().prefetch_related("messages")
        return [
            SessionResponse(
                id=str(session.id),
                name=session.name,
                created=session.created,
                is_protected=session.is_protected,
                message_count=len(session.messages),
            )
            for session in sessions
        ]

    @staticmethod
    async def create_session(session_data: SessionCreate) -> SessionResponse:
        """Create a new session"""
        session = await Session.create(
            name=session_data.name or f"Session {await Session.all().count() + 1}"
        )
        return SessionResponse(
            id=str(session.id),
            name=session.name,
            created=session.created,
            is_protected=session.is_protected,
            message_count=0,
        )

    @staticmethod
    async def get_session_with_messages(session_id: str) -> SessionWithMessages:
        """Get session with all messages"""
        try:
            session = await Session.get(id=session_id).prefetch_related("messages")
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = [
            MessageResponse(
                id=str(msg.id),
                session_id=str(session_id),
                content=msg.content,
                role=msg.role,
                timestamp=msg.timestamp,
                files=msg.files,
            )
            for msg in session.messages
        ]

        return SessionWithMessages(
            id=str(session.id),
            name=session.name,
            created=session.created,
            messages=messages,
        )

    @staticmethod
    async def delete_session(session_id: str):
        """Delete a session and all its messages"""
        try:
            session = await Session.get(id=session_id)
            await session.delete()
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")


class MessageService:
    @staticmethod
    async def list_messages(session_id: str) -> List[MessageResponse]:
        """List all messages in a session"""
        try:
            await Session.get(id=session_id)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = await Message.filter(session_id=session_id).order_by("timestamp")
        return [
            MessageResponse(
                id=str(msg.id),
                session_id=str(session_id),
                content=msg.content,
                role=msg.role,
                timestamp=msg.timestamp,
                files=msg.files,
            )
            for msg in messages
        ]

    @staticmethod
    async def create_message(
        session_id: str, message_data: MessageCreate
    ) -> MessageResponse:
        """Create a new message"""
        try:
            session = await Session.get(id=session_id)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")

        message = await Message.create(
            session=session,
            content=message_data.content,
            role=message_data.role,
            files=message_data.files,
        )

        return MessageResponse(
            id=str(message.id),
            session_id=str(session_id),
            content=message.content,
            role=message.role,
            timestamp=message.timestamp,
            files=message.files,
        )

    @staticmethod
    async def delete_message(session_id: str, message_id: str):
        """Delete a specific message"""
        try:
            message = await Message.get(id=message_id, session_id=session_id)
            await message.delete()
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Message not found")

    @staticmethod
    async def search_messages(query: str) -> List[SearchResponse]:
        """Search messages, excluding protected sessions"""
        # Only search in sessions without passwords
        messages = await Message.filter(
            content__icontains=query,
            session__password_hash__isnull=True,  # Exclude protected sessions
        ).prefetch_related("session")

        return [
            SearchResponse(
                message=MessageResponse(
                    id=str(msg.id),
                    session_id=str(msg.session.id),
                    content=msg.content,
                    role=msg.role,
                    timestamp=msg.timestamp,
                    files=msg.files,
                ),
                session_name=msg.session.name,
                session_id=str(msg.session.id),
            )
            for msg in messages
        ]

    @staticmethod
    async def generate_assistant_response(user_message: str) -> str:
        """Placeholder for OpenAI integration"""
        # TODO: Implement OpenAI integration
        return f"This is a placeholder response to: {user_message[:50]}..."

    @staticmethod
    async def count_user_messages(session_id: str) -> int:
        """Count user messages in a session"""
        return await Message.filter(session_id=session_id, role="user").count()


class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hash.encode("utf-8"))

    @staticmethod
    async def set_session_password(
        session_id: str, current_password: str, new_password: str
    ):
        """Set or change session password"""
        try:
            session = await Session.get(id=session_id)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")

        # If session has a password, verify current password
        if session.password_hash:
            if not current_password:
                raise HTTPException(status_code=400, detail="Current password required")
            if not PasswordService.verify_password(
                current_password, session.password_hash
            ):
                raise HTTPException(status_code=403, detail="Invalid current password")
        else:
            # If no password set, current_password should be empty
            if current_password:
                raise HTTPException(
                    status_code=400,
                    detail="Session has no password set, current password should be empty",
                )

        # Set new password
        session.password_hash = PasswordService.hash_password(new_password)
        await session.save()

    @staticmethod
    async def remove_session_password(
        session_id: str, current_password: Optional[str] = None
    ):
        """Remove session password"""
        try:
            session = await Session.get(id=session_id)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify current password if one exists
        if session.password_hash and current_password:
            if not PasswordService.verify_password(
                current_password, session.password_hash
            ):
                raise HTTPException(status_code=403, detail="Invalid current password")

        # Clear the password hash by updating the field
        await session.update_from_dict({"password_hash": None})
        await session.save()

    @staticmethod
    async def validate_session_password(session_id: str, password: str) -> bool:
        """Validate session password"""
        try:
            session = await Session.get(id=session_id)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.password_hash:
            return True  # No password set, always valid

        return PasswordService.verify_password(password, session.password_hash)
