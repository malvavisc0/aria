"""Browser automation tools using Lightpanda with Playwright CDP.

Tools for:
1. Opening URLs and getting page content
2. Clicking elements (accept cookies, pagination, etc.)
3. Taking screenshots

The browser is started automatically when the Aria server starts.
Lightpanda must be installed first:
    aria lightpanda download

Example:
    ```python
    from aria.tools.browser import (
        browser_open, browser_click, browser_screenshot
    )

    # Open a URL and get page content
    result = browser_open("Reading documentation", "https://example.com")

    # Click an element by CSS selector
    result = browser_click("Accepting cookies", "button.accept")

    # Take a screenshot
    result = browser_screenshot("Capturing page state", "page.png")
    ```
"""

from aria.tools.browser.constants import SCREENSHOTS_DIR
from aria.tools.browser.manager import get_browser_manager


def _get_manager():
    """Get the browser manager, raising if unavailable."""
    manager = get_browser_manager()
    if manager is None:
        raise RuntimeError(
            "Browser is not available. Either Lightpanda is not installed "
            "(run 'aria lightpanda download') or the browser "
            "failed to start."
        )
    if not manager.is_running:
        raise RuntimeError(
            "Browser is not running. It should have been started "
            "during app startup. Check the server logs for errors."
        )
    return manager


async def browser_open(intent: str, url: str) -> str:
    """Open a URL in the headless browser and get page content.

    This bypasses anti-bot protection by using a real browser via
    Lightpanda's CDP implementation. Use this for browsing websites,
    not for downloading files.

    The browser is already running — this just navigates to the URL.

    Args:
        intent: Why you are opening this URL (e.g., "Reading documentation")
        url: The URL to navigate to

    Returns:
        JSON with page content, title, and URL.

    Example:
        ```python
        result = await browser_open("Reading article", "https://example.com")
        # Returns JSON with page content
        ```
    """
    manager = _get_manager()
    return await manager.navigate(url)


async def browser_click(intent: str, selector: str) -> str:
    """Click an element by CSS selector.

    Use this to interact with elements like:
    - Accepting cookie consent banners
    - Clicking 'Load more' buttons
    - Navigating pagination
    - Following links

    After clicking, returns updated page content.

    Args:
        intent: Why you are clicking this element (e.g., "Accepting cookies")
        selector: CSS selector for the element, e.g. 'button.accept',
            'a[href="/next"]', '#submit-button'

    Returns:
        JSON with updated page content after the click.

    Example:
        ```python
        # Click a button with class "accept"
        result = await browser_click("Accepting cookies", "button.accept")

        # Click a link by its href
        result = await browser_click("Going to next page", "a.next-page")

        # Click by ID
        result = await browser_click("Submitting form", "#submit-button")
        ```
    """
    manager = _get_manager()
    return await manager.click(selector)


async def browser_screenshot(intent: str, filename: str) -> str:
    """Take a screenshot of the current browser page.

    The browser must have navigated to a page first with browser_open.

    Args:
        intent: Why you are taking the screenshot
            (e.g., "Capturing error state")
        filename: Output filename, e.g. 'page.png'

    Returns:
        JSON with the file path where the screenshot was saved.

    Example:
        ```python
        # After browser_open
        result = await browser_screenshot("Capturing page state", "page.png")
        # Returns {"success": true, "file_path": "/path/to/downloads/page.png"}
        ```
    """
    manager = _get_manager()

    filepath = SCREENSHOTS_DIR / filename
    return await manager.screenshot(str(filepath))
