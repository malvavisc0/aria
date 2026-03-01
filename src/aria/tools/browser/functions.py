"""Browser automation tools using agent-browser CLI.

Tools for:
1. Opening URLs and getting page content (accessibility tree)
2. Clicking elements (accept cookies, pagination, etc.)
3. Taking screenshots

The browser daemon is started automatically when the Aria server starts.
The agent-browser binary must be installed first:
    aria agentbrowser download

Example:
    ```python
    from aria.tools.browser import (
        browser_open, browser_click, browser_screenshot
    )

    # Open a URL and get page content
    result = browser_open("Reading documentation", "https://example.com")

    # Click an element by its ref
    result = browser_click("Accepting cookies", "@e2")

    # Take a screenshot
    result = browser_screenshot("Capturing page state", "page.png")
    ```
"""

import json

from aria.tools.browser.constants import SCREENSHOTS_DIR
from aria.tools.browser.manager import get_browser_manager


def _get_manager():
    """Get the browser manager, raising if unavailable."""
    manager = get_browser_manager()
    if manager is None:
        raise RuntimeError(
            "Browser is not available. Either agent-browser is not installed "
            "(run 'aria agentbrowser download') or the browser daemon "
            "failed to start."
        )
    if not manager.is_running:
        raise RuntimeError(
            "Browser daemon is not running. It should have been started "
            "during app startup. Check the server logs for errors."
        )
    return manager


def browser_open(intent: str, url: str) -> str:
    """Open a URL in the headless browser and get page content.

    This bypasses anti-bot protection by using a real Chromium browser.
    Use this for browsing websites, not for downloading files.

    The browser is already running — this just navigates to the URL.

    Args:
        intent: Why you are opening this URL (e.g., "Reading documentation")
        url: The URL to navigate to

    Returns:
        JSON with page content as accessibility tree, title, and URL.
        Elements have @refs like @e1, @e2 that can be used with browser_click.

    Example:
        ```python
        result = browser_open("Reading article", "https://example.com")
        # Returns JSON with accessibility tree and element refs
        ```
    """
    manager = _get_manager()

    # Step 1: Navigate to URL
    nav_result = manager.run_command("open", url)
    if "error" in nav_result:
        return json.dumps(nav_result, indent=2)

    # Step 2: Wait for page to finish loading
    manager.run_command("wait", "--load", "networkidle")

    # Step 3: Get interactive accessibility tree snapshot
    snapshot = manager.run_command("snapshot", "-i", "-c")

    return json.dumps(snapshot, indent=2)


def browser_click(intent: str, ref: str) -> str:
    """Click an element by its @ref from a previous snapshot.

    Use this to interact with elements like:
    - Accepting cookie consent banners
    - Clicking 'Load more' buttons
    - Navigating pagination
    - Following links

    After clicking, returns an updated snapshot of the page.

    Args:
        intent: Why you are clicking this element (e.g., "Accepting cookies")
        ref: Element reference from snapshot, e.g. '@e2'

    Returns:
        JSON with updated page snapshot after the click.

    Example:
        ```python
        # After browser_open returns snapshot with @e2 for "Accept" button
        result = browser_click("Accepting cookies", "@e2")
        # Returns updated snapshot
        ```
    """
    manager = _get_manager()

    # Click the element
    click_result = manager.run_command("click", ref)
    if "error" in click_result:
        return json.dumps(click_result, indent=2)

    # Wait for any navigation/updates to settle
    manager.run_command("wait", "1000")

    # Return updated snapshot
    snapshot = manager.run_command("snapshot", "-i", "-c")
    return json.dumps(snapshot, indent=2)


def browser_screenshot(intent: str, filename: str) -> str:
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
        result = browser_screenshot("Capturing page state", "page.png")
        # Returns {"success": true, "file_path": "/path/to/downloads/page.png"}
        ```
    """
    manager = _get_manager()

    filepath = SCREENSHOTS_DIR / filename
    result = manager.run_command("screenshot", str(filepath), json_output=False)

    if "error" in result:
        return json.dumps(result, indent=2)

    return json.dumps(
        {
            "success": True,
            "file_path": str(filepath),
            "note": "Use vision tools to analyze the screenshot if needed.",
        },
        indent=2,
    )
