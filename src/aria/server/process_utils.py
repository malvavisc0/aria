"""Shared utilities for process management.

This module provides common functions for managing external processes,
including state persistence, process checking, and graceful shutdown.
"""

import json
import os
import signal
import time
from pathlib import Path
from typing import Any


def is_process_running(pid: int) -> bool:
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


def load_state(pid_file: Path) -> dict[str, Any]:
    """Load process state from a JSON file.

    Args:
        pid_file: Path to the JSON state file.

    Returns:
        Dictionary with the loaded state, or empty dict if file doesn't exist
        or is invalid.
    """
    if not pid_file.exists():
        return {}
    try:
        with open(pid_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError, ValueError):
        return {}


def save_state(pid_file: Path, data: dict[str, Any]) -> None:
    """Save process state to a JSON file.

    Creates parent directories if they don't exist.

    Args:
        pid_file: Path to the JSON state file.
        data: Dictionary to save.
    """
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pid_file, "w") as f:
        json.dump(data, f, indent=2)


def clear_state(pid_file: Path) -> None:
    """Clear the state file if it exists.

    Args:
        pid_file: Path to the JSON state file.
    """
    if pid_file.exists():
        pid_file.unlink()


def stop_process(pid: int, timeout: float = 10.0) -> bool:
    """Stop a process by PID with graceful shutdown.

    Sends SIGTERM first, then SIGKILL if the process doesn't stop
    within the timeout period.

    Args:
        pid: Process ID to stop.
        timeout: Maximum seconds to wait for graceful shutdown.

    Returns:
        True if the process was stopped, False if it wasn't running.
    """
    if not is_process_running(pid):
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not is_process_running(pid):
                return True
            time.sleep(0.1)
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        # Wait for process to actually terminate (max 2 seconds)
        kill_start = time.time()
        while time.time() - kill_start < 2.0:
            if not is_process_running(pid):
                return True
            time.sleep(0.1)
        # Process still running after SIGKILL (zombie?)
        return False
    except ProcessLookupError:
        return True  # Process already gone
