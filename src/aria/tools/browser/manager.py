"""Browser daemon lifecycle management.

The BrowserManager follows the same pattern as LlamaCppServerManager:
- Started during on_app_startup() if the binary is available
- Stopped during on_app_shutdown()
- Agents use browser tools without worrying about lifecycle

Example:
    ```python
    from aria.tools.browser.manager import BrowserManager, set_browser_manager

    # During app startup
    manager = BrowserManager(binary_path)
    if manager.start():
        set_browser_manager(manager)

    # During app shutdown
    manager.stop()
    set_browser_manager(None)
    ```
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger

from aria.tools.browser.constants import BROWSER_COMMAND_TIMEOUT

# Module-level singleton — set during app startup
_manager: Optional["BrowserManager"] = None


def get_browser_manager() -> Optional["BrowserManager"]:
    """Get the global BrowserManager instance.

    Returns None if agent-browser is not installed or not started.
    """
    return _manager


def set_browser_manager(manager: Optional["BrowserManager"]) -> None:
    """Set the global BrowserManager instance.

    Called from on_app_startup() and on_app_shutdown().
    """
    global _manager
    _manager = manager


class BrowserManager:
    """Manages the agent-browser daemon lifecycle.

    Started during on_app_startup(), stopped during on_app_shutdown().
    Agents use browser tools without worrying about lifecycle.

    The browser daemon is started by opening a blank page, which
    initializes the Chromium process. All subsequent commands
    (open, click, etc.) operate against this running daemon.

    Attributes:
        _binary: Path to the agent-browser binary.
        _running: Whether the daemon is currently running.
    """

    def __init__(self, binary_path: Path):
        """Initialize the browser manager.

        Args:
            binary_path: Path to the agent-browser binary.
        """
        from aria.config.api import AgentBrowser

        self._binary = binary_path
        self._running = False
        self._env = AgentBrowser.get_env()

    def start(self) -> bool:
        """Start the browser daemon by opening a blank page.

        This initializes the Chromium process that persists
        for all subsequent commands.

        Returns:
            True if started successfully, False otherwise.
        """
        result = self.run_command("open", "about:blank")
        if "error" not in result:
            self._running = True
            logger.info("Browser daemon started")
            return True
        else:
            logger.warning(f"Failed to start browser daemon: {result}")
            return False

    def stop(self) -> None:
        """Stop the browser daemon.

        Called from on_app_shutdown().
        """
        if self._running:
            try:
                self.run_command("close", json_output=False)
                logger.info("Browser daemon stopped")
            except Exception as e:
                logger.warning(f"Error stopping browser daemon: {e}")
            finally:
                self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the browser daemon is running."""
        return self._running

    def run_command(
        self,
        *args: str,
        json_output: bool = True,
        timeout: int = BROWSER_COMMAND_TIMEOUT,
    ) -> dict:
        """Run a browser command against the running daemon.

        Args:
            *args: Command arguments, e.g. 'open', 'https://example.com'
            json_output: Whether to request JSON output
            timeout: Command timeout in seconds

        Returns:
            Parsed JSON response or dict with output/error keys
        """
        cmd = [str(self._binary)]
        if json_output:
            cmd.append("--json")
        cmd.extend(args)

        logger.debug(f"Running browser command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env,
            )

            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or f"Command failed: {' '.join(args)}"
                )
                logger.debug(
                    f"Browser command failed (rc={result.returncode}): "
                    f"{' '.join(cmd)}"
                )
                logger.debug(f"  stdout: {result.stdout.strip()}")
                logger.debug(f"  stderr: {result.stderr.strip()}")
                return {"error": error_msg}

            if json_output and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout}
            return {"output": result.stdout}

        except subprocess.TimeoutExpired:
            return {"error": f"Browser command timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}
