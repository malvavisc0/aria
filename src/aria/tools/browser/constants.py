"""Constants for browser automation tools.

This module contains constants specific to browser automation using
Lightpanda with Playwright CDP. For shared constants, imports from
aria.tools.constants.
"""

from aria.tools.constants import BASE_DIR

# Timeout for individual browser commands (seconds)
# Longer than network timeout since page loads can be slow
BROWSER_COMMAND_TIMEOUT = 60

# Default wait strategy after navigation
DEFAULT_WAIT_STRATEGY = "networkidle"

# Default CDP port for Lightpanda serve
LIGHTPANDA_DEFAULT_PORT = 9222

# Screenshots directory
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Persisted browser page-content captures
BROWSER_CONTENT_DIR = BASE_DIR / "browser"
BROWSER_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
