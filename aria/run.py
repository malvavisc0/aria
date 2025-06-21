#!/usr/bin/env python3
"""
Run script for the Chat API backend
"""

import os
import sys

import uvicorn

# Add the parent directory to the Python path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aria.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "aria.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL,
    )
