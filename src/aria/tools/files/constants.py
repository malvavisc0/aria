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

# Blocked file extensions (binary/executable/media that shouldn't be read as text)
BLOCKED_EXTENSIONS = {
    # Executables and libraries
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".msi",
    ".com",
    # Compiled objects
    ".class",
    ".pyc",
    ".pyo",
    ".o",
    ".obj",
    # OS packages/images
    ".deb",
    ".rpm",
    ".dmg",
    ".iso",
    ".img",
    # Archives
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".zst",
    # Media (images)
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".tiff",
    ".psd",
    # Media (audio/video)
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wav",
    ".flac",
    ".mkv",
    ".wmv",
    ".ogg",
    # Office/binary documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    # Fonts
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
}

# Blocked patterns that should not appear in file names
BLOCKED_PATTERNS = {"..", "~", "$", "`", ";", "|", "&", "<", ">"}
