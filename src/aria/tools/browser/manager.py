"""Lightpanda browser lifecycle management via Playwright CDP.

The LightpandaManager follows the same pattern as LlamaCppServerManager:
- Started during on_app_startup() if the binary is available
- Stopped during on_app_shutdown()
- Agents use browser tools without worrying about lifecycle

Example:
    ```python
    from aria.tools.browser.manager import (
        LightpandaManager,
        set_browser_manager,
    )

    # During app startup
    manager = LightpandaManager(binary_path, port=9222)
    if await manager.start():
        set_browser_manager(manager)

    # During app shutdown
    await manager.stop()
    set_browser_manager(None)
    ```
"""

import asyncio
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import Browser, Page, Playwright, async_playwright

from aria.tools import safe_json
from aria.tools.browser.constants import (
    BROWSER_COMMAND_TIMEOUT,
    BROWSER_CONTENT_DIR,
    LIGHTPANDA_DEFAULT_PORT,
)

# Module-level singleton — set during app startup
_manager: Optional["LightpandaManager"] = None


def _build_content_filepath(url: str, action: str) -> Path:
    """Build a stable, timestamped path for persisted page content."""
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{action}_{digest}.txt"
    return BROWSER_CONTENT_DIR / filename


def get_browser_manager() -> Optional["LightpandaManager"]:
    """Get the global LightpandaManager instance.

    Returns None if Lightpanda is not installed or not started.
    """
    return _manager


def set_browser_manager(manager: Optional["LightpandaManager"]) -> None:
    """Set the global LightpandaManager instance.

    Called from on_app_startup() and on_app_shutdown().
    """
    global _manager
    _manager = manager


class LightpandaManager:
    """Manages Lightpanda browser lifecycle via CDP + Playwright.

    Started during on_app_startup(), stopped during on_app_shutdown().
    Agents use browser tools without worrying about lifecycle.

    The manager starts Lightpanda in serve mode, which creates a CDP
    endpoint that Playwright connects to for browser automation.

    Attributes:
        _binary: Path to the Lightpanda binary.
        _port: CDP port for Lightpanda serve.
        _process: Subprocess running Lightpanda serve.
        _playwright: Playwright instance.
        _browser: Connected Browser instance.
        _page: Current Page instance.
    """

    def __init__(self, binary_path: Path, port: int = LIGHTPANDA_DEFAULT_PORT):
        """Initialize the Lightpanda manager.

        Args:
            binary_path: Path to the Lightpanda binary.
            port: CDP port for Lightpanda serve (default: 9222).
        """
        self._binary = binary_path
        self._port = port
        self._process: Optional[subprocess.Popen] = None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def start(self) -> bool:
        """Start Lightpanda serve and connect Playwright via CDP.

        This starts the Lightpanda process in serve mode, waits for
        the CDP endpoint to be ready, then connects Playwright.

        Returns:
            True if started successfully, False otherwise.
        """
        try:
            # Start Lightpanda serve process
            cmd = [
                str(self._binary),
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(self._port),
            ]
            logger.debug(f"Starting Lightpanda: {' '.join(cmd)}")

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for CDP endpoint to be ready
            if not await self._wait_for_cdp():
                logger.error("Lightpanda CDP endpoint did not become ready")
                self._cleanup_process()
                return False

            # Connect Playwright via CDP
            self._playwright = await async_playwright().start()
            cdp_url = f"http://127.0.0.1:{self._port}"
            self._browser = await self._playwright.chromium.connect_over_cdp(
                cdp_url
            )

            # Create initial page
            self._page = await self._browser.new_page()

            logger.info(f"Lightpanda browser started on port {self._port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start Lightpanda: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Close Playwright, terminate Lightpanda process.

        Called from on_app_shutdown().
        """
        # Close browser connection
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self._browser = None

        # Stop Playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping Playwright: {e}")
            finally:
                self._playwright = None

        # Terminate Lightpanda process
        self._cleanup_process()

        self._page = None
        logger.info("Lightpanda browser stopped")

    def _cleanup_process(self) -> None:
        """Terminate the Lightpanda subprocess."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            except Exception as e:
                logger.warning(f"Error terminating Lightpanda: {e}")
            finally:
                self._process = None

    async def _wait_for_cdp(self, timeout: float = 10.0) -> bool:
        """Wait for the CDP endpoint to be ready.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            True if CDP is ready, False if timeout.
        """
        import socket

        loop = asyncio.get_running_loop()
        start_time = loop.time()
        while loop.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", self._port))
                sock.close()
                if result == 0:
                    # Port is open, give it a moment to fully initialize
                    await asyncio.sleep(0.5)
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.1)

        return False

    @property
    def is_running(self) -> bool:
        """Check if the browser is running."""
        return (
            self._process is not None
            and self._browser is not None
            and self._page is not None
        )

    def _is_page_valid(self) -> bool:
        """Check if the page is still valid and not closed."""
        try:
            return self._page is not None and not self._page.is_closed()
        except Exception:
            return False

    async def _ensure_page(self) -> bool:
        """Ensure we have a valid page, restart browser if needed.

        Returns:
            True if page is available, False otherwise.
        """
        if self._is_page_valid():
            return True

        # Try to restart the browser
        logger.warning("Browser page invalid, attempting to restart...")
        await self.stop()

        # Try to start again
        if await self.start():
            logger.info("Browser restarted successfully")
            return True

        logger.error("Failed to restart browser")
        return False

    @property
    def page(self) -> Page:
        """Get the current Playwright page.

        Raises:
            RuntimeError: If browser is not running.
        """
        if not self.is_running:
            raise RuntimeError("Lightpanda browser is not running")
        return self._page  # type: ignore

    def _require_running_page(self) -> Page:
        """Ensure browser is running and page is available.

        Returns:
            The current page.

        Raises:
            RuntimeError: If browser is not running or page is not open.
        """
        if not self.is_running:
            raise RuntimeError("Browser is not running")
        if not self._page:
            raise RuntimeError("Page is not open")
        return self._page

    def _success(self, data: dict) -> str:
        """Create a success JSON response."""
        return safe_json(data)

    def _error(self, message: str, recovery: bool = False) -> str:
        """Create an error JSON response."""
        result = {"error": message}
        if recovery:
            result["recovery"] = "Browser crashed. Restarted. Retry."
        return safe_json(result)

    async def navigate(self, url: str) -> str:
        """Navigate to URL and return rendered content.

        Args:
            url: URL to navigate to.

        Returns:
            JSON string with page content and metadata.
        """
        try:
            page = self._require_running_page()
        except RuntimeError as e:
            return self._error(str(e))

        # Check if page is still valid before attempting navigation
        if not self._is_page_valid():
            logger.warning("Page is closed, attempting to restart browser...")
            if not await self._ensure_page():
                return self._error(
                    "Browser crashed and could not be restarted"
                )

        try:
            # Navigate to URL
            await page.goto(url, timeout=BROWSER_COMMAND_TIMEOUT * 1000)

            # Wait for page to settle
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Get and persist page content
            content = await self.get_page_content()
            content_path = _build_content_filepath(page.url, "open")
            content_path.write_text(content, encoding="utf-8")

            # Safely get title with fallback
            try:
                title = (
                    await page.title() if self._is_page_valid() else "Unknown"
                )
            except Exception:
                title = "Unknown"

            return self._success(
                {
                    "url": page.url,
                    "title": title,
                    "content_file": str(content_path),
                    "content_preview": (
                        content[:500] + "..."
                        if len(content) > 500
                        else content
                    ),
                    "content_size": len(content),
                }
            )

        except Exception as e:
            logger.error(f"Navigation error: {e}")

            # Check if browser crashed during navigation
            if not self._is_page_valid():
                logger.warning(
                    "Browser crashed during navigation, attempting restart..."
                )
                if await self._ensure_page():
                    return self._error(str(e), recovery=True)

            return self._error(str(e))

    async def click(self, selector: str) -> str:
        """Click element by CSS selector and return updated content.

        Args:
            selector: CSS selector for element to click.

        Returns:
            JSON string with updated page content.
        """
        try:
            page = self._require_running_page()
        except RuntimeError as e:
            return self._error(str(e))

        # Check if page is still valid before attempting click
        if not self._is_page_valid():
            logger.warning("Page is closed, attempting to restart browser...")
            if not await self._ensure_page():
                return self._error(
                    "Browser crashed and could not be restarted"
                )

        try:
            # Click the element
            await page.click(selector, timeout=10000)

            # Wait for any navigation/updates
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Get and persist updated content
            content = await self.get_page_content()
            content_path = _build_content_filepath(page.url, "click")
            content_path.write_text(content, encoding="utf-8")

            # Safely get title with fallback
            try:
                title = (
                    await page.title() if self._is_page_valid() else "Unknown"
                )
            except Exception:
                title = "Unknown"

            return self._success(
                {
                    "url": page.url,
                    "title": title,
                    "content_file": str(content_path),
                    "content_preview": (
                        content[:500] + "..."
                        if len(content) > 500
                        else content
                    ),
                    "content_size": len(content),
                }
            )

        except Exception as e:
            logger.error(f"Click error: {e}")

            # Check if browser crashed during click
            if not self._is_page_valid():
                logger.warning(
                    "Browser crashed during click, attempting restart..."
                )
                if await self._ensure_page():
                    return self._error(str(e), recovery=True)

            return self._error(str(e))

    async def screenshot(self, path: str) -> str:
        """Take a screenshot of the current page.

        Args:
            path: File path to save screenshot.

        Returns:
            JSON string with file path.
        """
        try:
            page = self._require_running_page()
        except RuntimeError as e:
            return self._error(str(e))

        # Check if page is still valid before attempting screenshot
        if not self._is_page_valid():
            logger.warning("Page is closed, attempting to restart browser...")
            if not await self._ensure_page():
                return self._error(
                    "Browser crashed and could not be restarted"
                )

        try:
            await page.screenshot(path=path)
            return self._success(
                {
                    "success": True,
                    "file_path": path,
                    "note": "Use vision tools to analyze the screenshot.",
                }
            )

        except Exception as e:
            logger.error(f"Screenshot error: {e}")

            # Check if browser crashed during screenshot
            if not self._is_page_valid():
                logger.warning(
                    "Browser crashed during screenshot, attempting restart..."
                )
                if await self._ensure_page():
                    return self._error(str(e), recovery=True)

            return self._error(str(e))

    async def get_page_content(self) -> str:
        """Get current page content as clean text.

        Returns:
            Page content as text, with scripts and styles removed.
        """
        try:
            page = self._require_running_page()
        except RuntimeError as e:
            return self._error(str(e))

        # Check if page is still valid
        if not self._is_page_valid():
            logger.warning("Page is closed, attempting to restart browser...")
            if not await self._ensure_page():
                return self._error(
                    "Browser crashed and could not be restarted"
                )

        try:
            # Get text content from body, excluding scripts and styles
            content = await page.evaluate("""
                () => {
                    // Clone the document to avoid modifying the original
                    const clone = document.body.cloneNode(true);

                    // Remove script and style elements
                    const remove = ['script', 'style', 'noscript'];
                    remove.forEach(tag => {
                        clone.querySelectorAll(tag).forEach(el => el.remove());
                    });

                    // Get text content
                    return clone.innerText || clone.textContent || '';
                }
            """)

            # Clean up whitespace
            lines = (line.strip() for line in content.splitlines())
            return "\n".join(line for line in lines if line)

        except Exception as e:
            logger.warning(f"Error getting page content: {e}")
            return await page.content()
