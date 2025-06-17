import os
import time
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise

from aria.api.endpoints import router as api_router

from .config import settings
from .models import Message, Session
from .schemas import (
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
from .services import MessageService, PasswordService, SessionService

app = FastAPI(
    title="Chat API",
    description="FastAPI backend for chat sessions and messages",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Include API router
app.include_router(api_router)

# Serve frontend static files at /
frontend_dir = os.path.join(os.path.dirname(__file__), "webui")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# Database setup
register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["aria.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

# Create upload directory on startup
settings.create_upload_dir()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
