"""Command execution internals for shell execution tools.

This module provides internal helpers for command execution and
response building.
"""

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from aria.tools import get_function_name, utc_timestamp
from aria.tools.shell.constants import CURRENT_OS, MAX_OUTPUT_SIZE
from aria.tools.shell.validation import _extract_command_name


def _build_response(
    operation: str,
    command: str,
    working_dir: str,
    *,
    stdout: str = "",
    stderr: str = "",
    return_code: int = -1,
    execution_time: float = 0.0,
    timed_out: bool = False,
) -> Dict[str, Any]:
    """Build a standard command execution response dict.

    Args:
        operation: The operation name (e.g. "execute_command").
        command: The command that was executed.
        working_dir: The resolved working directory path.
        stdout: Captured standard output.
        stderr: Captured standard error.
        return_code: Process exit code.
        execution_time: Duration in seconds.
        timed_out: Whether the command timed out.

    Returns:
        Response dictionary with operation, result, and metadata.
    """
    return {
        "status": "success",
        "tool": get_function_name(),
        "reason": "",
        "timestamp": utc_timestamp(),
        "data": {
            "stdout": stdout[:MAX_OUTPUT_SIZE] if stdout else "",
            "stderr": stderr[:MAX_OUTPUT_SIZE] if stderr else "",
            "return_code": return_code,
            "execution_time": round(execution_time, 3),
            "timed_out": timed_out,
            "command": command,
            "platform": CURRENT_OS,
            "working_dir": working_dir,
        },
    }


def _execute_command_internal(
    operation: str,
    display_command: str,
    run_target: Union[str, List[str]],
    working_dir: Path,
    timeout: int,
    *,
    shell: bool,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Execute a command and return a standardized response dict.

    Args:
        operation: The operation name (e.g. ``execute_command``).
        display_command: Human-readable command for response payload.
        run_target: Command passed to ``subprocess.run``.
            When ``shell=True`` this should be a string.
            When ``shell=False`` this should be a list of strings.
        working_dir: Resolved working directory.
        timeout: Timeout in seconds.
        shell: Whether to execute via the system shell.
        env: Optional environment variables passed to subprocess.

    Returns:
        Standardized response dictionary from :func:`_build_response`.
    """
    start_time = time.time()
    working_dir_str = str(working_dir)

    try:
        result = subprocess.run(
            run_target,
            shell=shell,
            cwd=working_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start_time

        logger.info("Command executed with return code {}", result.returncode)
        if result.stdout:
            logger.info("stdout: {}", result.stdout[:2000])
        if result.stderr:
            logger.warning("stderr: {}", result.stderr[:2000])
        return _build_response(
            operation,
            display_command,
            working_dir_str,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            execution_time=elapsed,
        )

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.warning(f"Command timed out after {timeout}s")
        return _build_response(
            operation,
            display_command,
            working_dir_str,
            execution_time=elapsed,
            timed_out=True,
        )

    except FileNotFoundError:
        cmd_name = _extract_command_name(display_command)
        logger.error(f"Command not found: {cmd_name}")
        return _build_response(
            operation,
            display_command,
            working_dir_str,
            stderr=f"Command not found: {cmd_name}",
            return_code=127,
        )

    except PermissionError:
        logger.error(f"Permission denied executing command: {display_command}")
        return _build_response(
            operation,
            display_command,
            working_dir_str,
            stderr="Permission denied",
            return_code=1,
        )

    except Exception as exc:
        logger.error(f"Unexpected error executing command: {exc}")
        return _build_response(
            operation,
            display_command,
            working_dir_str,
            stderr=str(exc),
            return_code=1,
        )
