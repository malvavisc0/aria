"""
Constants for file operations security and configuration.

These constants define security limits, allowed file types, and system
configuration parameters for file handling operations.

For shared constants like BASE_DIR and MAX_FILE_SIZE,
import from aria.tools.constants.
"""

# Maximum chunk size for operations (in lines)
MAX_CHUNK_SIZE = 10000

# Maximum line length allowed (in characters)
MAX_LINE_LENGTH = 10000

# Allowed file extensions for security
ALLOWED_EXTENSIONS = {
    # Text/Code
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
    ".ini",
    ".toml",
    # Shell scripts
    ".sh",
    ".bash",
    ".zsh",
    # Code files
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    # Web files
    ".html",
    ".css",
    ".scss",
    ".jsx",
    ".tsx",
    # Config files
    ".env",
    ".gitignore",
    ".dockerignore",
    ".sql",
    # Build/Project files
    "Dockerfile",
    "Makefile",
    "CMakeLists.txt",
}

# Blocked patterns that should not appear in file names
BLOCKED_PATTERNS = {"..", "~", "$", "`", ";", "|", "&", "<", ">"}
