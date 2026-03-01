"""Constants for browser automation tools.

This module contains constants specific to browser automation using
the agent-browser CLI. For shared constants, imports from
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

# ============================================================================
# Directory Configuration
# ============================================================================

# Screenshots directory (reuse downloads)
SCREENSHOTS_DIR = DOWNLOADS_DIR
