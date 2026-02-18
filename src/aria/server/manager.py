"""Server manager for controlling the Chainlit webserver lifecycle.

This module provides the ServerManager class for starting, stopping,
and monitoring the Aria Chainlit webserver process.
"""

import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from aria.config.folders import Data as DataConfig
from aria.config.service import Server


@dataclass
class ServerStatus:
    """Status information for the webserver.

    Attributes:
        running: Whether the server is currently running.
        pid: Process ID of the running server, or None if not running.
        host: The host address the server is bound to.
        port: The port number the server is listening on.
        started_at: Timestamp when the server was started, or None.
    """

    running: bool
    pid: int | None
    host: str
    port: int
    started_at: datetime | None

    @property
    def uptime_seconds(self) -> float | None:
        """Calculate uptime in seconds.

        Returns:
            Uptime in seconds, or None if the server is not running.
        """
        if self.started_at is None:
            return None
        return (datetime.now() - self.started_at).total_seconds()


class ServerManager:
    """Manages the Chainlit webserver lifecycle.

    This class provides methods to start, stop, restart, and monitor
    the Aria Chainlit webserver. It handles both development (uv) and
    installed package (pip) environments.

    Process state is persisted to a JSON file, allowing the manager
    to track servers started by other processes (e.g., CLI to GUI).

    Attributes:
        pid: Process ID of the running server, or None if not running.
        started_at: Timestamp when the server was started, or None.
        uptime: Uptime in seconds, or None if not running.

    Example:
        ```python
        manager = ServerManager()

        # Start in background
        manager.start()
        print(f"Server PID: {manager.pid}")

        # Check status
        status = manager.get_status()
        print(f"Running: {status.running}, Uptime: {status.uptime_seconds}s")

        # Stop the server
        manager.stop()
        ```
    """

    PID_FILE = DataConfig.path / "server.json"

    def __init__(self):
        """Initialize the ServerManager.

        Reads host and port configuration from the Server config class,
        resolves the path to web_ui.py relative to the package location,
        and loads any existing process state from the PID file.
        """
        self._host = Server.host
        self._port = Server.port
        self._process: subprocess.Popen | None = None
        self._started_at: datetime | None = None

        # Resolve path to web_ui.py in the installed package
        import aria

        package_dir = Path(aria.__file__).parent
        self._target = str(package_dir / "web_ui.py")

        # Load existing state from PID file
        self._load_state()

    def _load_state(self) -> None:
        """Load process state from the PID file.

        If the PID file exists and the process is still running,
        restores the _started_at timestamp.
        """
        if not self.PID_FILE.exists():
            return

        try:
            with open(self.PID_FILE, "r") as f:
                data = json.load(f)

            pid = data.get("pid")
            started_at_str = data.get("started_at")

            if pid and self._is_process_running(pid):
                self._started_at = datetime.fromisoformat(started_at_str)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    def _save_state(self) -> None:
        """Save process state to the PID file."""
        # Ensure data directory exists
        self.PID_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "pid": self.pid,
            "host": self._host,
            "port": self._port,
            "started_at": (
                self._started_at.isoformat() if self._started_at else None
            ),
        }

        with open(self.PID_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _clear_state(self) -> None:
        """Clear the PID file."""
        if self.PID_FILE.exists():
            self.PID_FILE.unlink()

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """Check if a process with the given PID is running.

        Args:
            pid: Process ID to check.

        Returns:
            True if the process is running, False otherwise.
        """
        try:
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
            return True
        except (OSError, ProcessLookupError):
            return False

    @property
    def pid(self) -> int | None:
        """Get the process ID of the running server.

        Returns:
            Process ID, or None if the server is not running.
        """
        if self._process is not None:
            return self._process.pid

        # Try to get PID from saved state
        if self.PID_FILE.exists():
            try:
                with open(self.PID_FILE, "r") as f:
                    data = json.load(f)
                return data.get("pid")
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    @property
    def started_at(self) -> datetime | None:
        """Get the time when the server was started.

        Returns:
            Start timestamp, or None if the server is not running.
        """
        return self._started_at

    @property
    def uptime(self) -> float | None:
        """Get the uptime in seconds.

        Returns:
            Uptime in seconds, or None if the server is not running.
        """
        if self._started_at is None:
            return None
        return (datetime.now() - self._started_at).total_seconds()

    def _build_command(self) -> list[str]:
        """Build the chainlit run command.

        Detects whether running in a uv development environment or as an
        installed package, and builds the appropriate command.

        Returns:
            List of command arguments for subprocess.
        """
        # Check if we're in a uv environment
        # Heuristic: uv in executable path or pyproject.toml exists
        in_uv = "uv" in sys.executable or Path("pyproject.toml").exists()

        if in_uv:
            cmd = [
                "uv",
                "run",
                "chainlit",
                "run",
                "--no-cache",
                "--host",
                self._host,
                "--port",
                str(self._port),
                "--root-path",
                str(Path.cwd()),
                self._target,
            ]
        else:
            cmd = [
                "chainlit",
                "run",
                "--no-cache",
                "--host",
                self._host,
                "--port",
                str(self._port),
                "--root-path",
                str(Path.cwd()),
                self._target,
            ]

        return cmd

    def start(self) -> bool:
        """Start the webserver as a background subprocess.

        Returns:
            True if the server was started successfully,
            False if the server is already running.
        """
        if self.is_running():
            return False

        cmd = self._build_command()
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._started_at = datetime.now()
        self._save_state()
        return True

    def run(self) -> None:
        """Run the webserver in the foreground (blocking).

        This method blocks until the server is stopped (Ctrl+C).
        """
        cmd = self._build_command()
        self._started_at = datetime.now()
        self._save_state()
        try:
            subprocess.run(cmd)
        finally:
            self._clear_state()

    def stop(self, timeout: float = 10.0) -> bool:
        """Stop the running webserver.

        Sends SIGTERM to the process, then SIGKILL if it doesn't
        terminate within the timeout period.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown.

        Returns:
            True if the server was stopped successfully,
            False if the server was not running.
        """
        if not self.is_running():
            return False

        pid = self.pid
        if pid is None:
            return False

        # If we have a Popen object, use it
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        else:
            # Otherwise, kill by PID
            try:
                os.kill(pid, signal.SIGTERM)
                # Wait for process to terminate
                import time

                start_time = time.time()
                while time.time() - start_time < timeout:
                    if not self._is_process_running(pid):
                        break
                    time.sleep(0.1)
                else:
                    # Force kill if still running
                    os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        self._process = None
        self._started_at = None
        self._clear_state()
        return True

    def restart(self, timeout: float = 10.0) -> bool:
        """Restart the webserver.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown.

        Returns:
            True if the server was restarted successfully.
        """
        if self.is_running():
            self.stop(timeout)
        return self.start()

    def is_running(self) -> bool:
        """Check if the server is currently running.

        Returns:
            True if the server is running, False otherwise.
        """
        # Check if we have an active Popen object
        if self._process is not None:
            return self._process.poll() is None

        # Check if there's a running process from the PID file
        pid = self.pid
        if pid is not None:
            return self._is_process_running(pid)

        return False

    def get_status(self) -> ServerStatus:
        """Get detailed server status.

        Returns:
            ServerStatus dataclass with current server information.
        """
        return ServerStatus(
            running=self.is_running(),
            pid=self.pid,
            host=self._host,
            port=self._port,
            started_at=self._started_at,
        )
