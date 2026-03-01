"""Browser automation tools using Lightpanda with Playwright CDP.

This module provides tools for web browsing and interaction using
Lightpanda, a lightweight headless browser with CDP support.
The browser is managed at the application level and started during
app startup.

Tools:
    browser_open: Navigate to a URL and get page content
    browser_click: Click elements by CSS selector
    browser_screenshot: Take screenshots of the current page

Example:
    ```python
    from aria.tools.browser import browser_open, browser_click

    # Open a URL
    result = browser_open("Reading docs", "https://example.com")

    # Click an element by CSS selector
    result = browser_click("Accepting cookies", "button.accept")
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
