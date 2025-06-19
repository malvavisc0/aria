import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise

from aria.api.endpoints import router as api_router

from .config import settings


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure parent directory for database file exists
    db_path = settings.DATABASE_URL
    if db_path.startswith("sqlite://"):
        db_path = db_path.replace("sqlite://", "")
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

    # Initialize empty SQLite database file if it does not exist
    if not os.path.exists(db_path):
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.close()

    settings.create_upload_dir()
    yield


# Single FastAPI instance with lifespan
app = FastAPI(
    title="Aria API",
    description="FastAPI backend for chat sessions and messages",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
