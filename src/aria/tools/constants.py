"""
Shared constants across all aria2 tools.

This module contains constants that are used by multiple tool modules,
providing a single source of truth for common configuration.
"""

import os
from pathlib import Path

# ============================================================================
# Directory Configuration
# ============================================================================

# Base directory for all file operations
BASE_DIR = Path(os.environ.get("TOOLS_DATA_FOLDER", ".files")).resolve()
BASE_DIR.mkdir(exist_ok=True)

# Derived directories
CODE_DIR = BASE_DIR / "code"
CODE_DIR.mkdir(exist_ok=True)

DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Size and Timeout Limits
# ============================================================================

# Maximum file size for processing (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

# Default timeout for operations (seconds)
DEFAULT_TIMEOUT = 30

# Maximum timeout limit (seconds)
MAX_TIMEOUT = 300

# ============================================================================
# Network Configuration
# ============================================================================

# Maximum retry attempts for network operations
MAX_RETRIES = 3

# Network request timeout (seconds)
NETWORK_TIMEOUT = 10
