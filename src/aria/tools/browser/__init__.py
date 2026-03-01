"""Browser automation tools using agent-browser CLI.

This module provides tools for web browsing and interaction using
the agent-browser CLI from Vercel Labs. The browser daemon is managed
at the application level and started during app startup.

Tools:
    browser_open: Navigate to a URL and get page content
    browser_click: Click elements by their @ref from snapshots
    browser_screenshot: Take screenshots of the current page

Example:
    ```python
    from aria.tools.browser import browser_open, browser_click

    # Open a URL
    result = browser_open("Reading docs", "https://example.com")

    # Click an element (ref from snapshot)
    result = browser_click("Accepting cookies", "@e2")
    ```
"""

from aria.tools.browser.functions import (
    browser_click,
    browser_open,
    browser_screenshot,
)

__all__ = [
    "browser_open",
    "browser_click",
    "browser_screenshot",
]
