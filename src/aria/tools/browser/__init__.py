"""Browser automation tools using Lightpanda with Playwright CDP.

This module provides tools for web browsing and interaction using
Lightpanda, a lightweight headless browser with CDP support.
The browser is managed at the application level and started during
app startup.

Tools:
    open_url: Navigate to a URL and persist page content
    browser_click: Click elements by CSS selector

Example:
    ```python
    from aria.tools.browser import open_url, browser_click

    # Open a URL
    result = open_url("Reading docs", "https://example.com")

    # Click an element by CSS selector
    result = browser_click("Accepting cookies", "button.accept")
    ```
"""

from aria.tools.browser.functions import browser_click, browser_close, open_url

__all__ = [
    "open_url",
    "browser_click",
    "browser_close",
]
