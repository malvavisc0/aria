"""
Configuration settings for the Chat API backend
"""

import os
from typing import Optional


class Settings:
    # Database settings
    DATABASE_URL: str = "sqlite:///opt/storage/chat.db"

    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # CORS settings
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "/opt/storage/uploads"
    ALLOWED_FILE_TYPES: list = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "text/plain",
        "text/csv",
        "application/pdf",
        "application/json",
    ]

    # OpenAI settings (for future implementation)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-3.5-turbo"

    # Logging
    LOG_LEVEL: str = "info"

    @classmethod
    def create_upload_dir(cls):
        """Create upload directory if it doesn't exist"""
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)


# Global settings instance
settings = Settings()
