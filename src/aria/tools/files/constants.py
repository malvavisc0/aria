"""
Constants for file operations security and configuration.

These constants define security limits, allowed file types, and system
configuration parameters for file handling operations.

For shared constants like BASE_DIR and MAX_FILE_SIZE,
import from aria2.tools.constants.
"""

# Maximum chunk size for operations (in lines)
MAX_CHUNK_SIZE = 10000

# Maximum line length allowed (in characters)
MAX_LINE_LENGTH = 10000

# Allowed file extensions for security
ALLOWED_EXTENSIONS = {
    ".txt",
    ".py",
    ".js",
    ".json",
    ".md",
    ".csv",
    ".log",
    ".yaml",
    ".yml",
    ".xml",
    ".ts",
}

# Blocked patterns that should not appear in file names
BLOCKED_PATTERNS = {"..", "~", "$", "`", ";", "|", "&", "<", ">"}
