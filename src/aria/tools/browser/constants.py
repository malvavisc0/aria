"""Constants for browser automation tools.

This module contains constants specific to browser automation using
Lightpanda with Playwright CDP. For shared constants, imports from
aria.tools.constants.
"""

from aria.tools.constants import DOWNLOADS_DIR

# ============================================================================
# Timeout Configuration
# ============================================================================

# Timeout for individual browser commands (seconds)
# Longer than network timeout since page loads can be slow
BROWSER_COMMAND_TIMEOUT = 60

# ============================================================================
# Default Settings
# ============================================================================

# Default wait strategy after navigation
DEFAULT_WAIT_STRATEGY = "networkidle"

# Default CDP port for Lightpanda serve
LIGHTPANDA_DEFAULT_PORT = 9222

# ============================================================================
# Directory Configuration
# ============================================================================

# Screenshots directory (reuse downloads)
SCREENSHOTS_DIR = DOWNLOADS_DIR
