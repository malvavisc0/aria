"""Shell execution tool functions.

This module provides functions for executing shell commands safely with
proper timeout handling, output capture, and security constraints.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from aria.tools.shell.constants import (
    BASE_DIR,
    BLOCKED_COMMANDS,
    BLOCKED_UNIX,
    BLOCKED_WINDOWS,
    CURRENT_OS,
    DEFAULT_TIMEOUT,
    IS_LINUX,
    IS_MACOS,
    IS_WINDOWS,
    MAX_OUTPUT_SIZE,
    MAX_TIMEOUT,
    SAFE_COMMANDS_SET,
    SHELL,
)
from aria.tools.shell.exceptions import (
    CommandBlockedError,
    WorkingDirectoryError,
)

# Shell operators that could be used for injection.
_SHELL_OPERATORS_RE = re.compile(
    r"[;|&`]"  # semicolon, pipe, ampersand, backtick
    r"|\$\("  # $( subshell
    r"|\|\|"  # logical OR
    r"|&&"  # logical AND
)


def _extract_command_name(command: str) -> str:
    """Extract the base command name from a command string.

    Args:
        command: The full command string.

    Returns:
        The first word (command name), or empty string if blank.
    """
    stripped = command.strip()
    return stripped.split()[0] if stripped else ""


def _is_blocked_command(command: str) -> bool:
    """Check if a command name is in the blocked list.

    Blocked list only — no implicit whitelist. Injection/operators are
    handled separately by ``_has_shell_operators``.

    Args:
        command: The full command string.

    Returns:
        True if the base command name is blocked, False otherwise.
    """
    cmd_name = _extract_command_name(command)

    if cmd_name in BLOCKED_COMMANDS:
        return True

    if IS_WINDOWS and cmd_name in BLOCKED_WINDOWS:
        return True

    if (IS_LINUX or IS_MACOS) and cmd_name in BLOCKED_UNIX:
        return True

    return False


def _has_shell_operators(command: str) -> bool:
    """Check if a command contains shell operators that could bypass security.

    Detects pipes, semicolons, &&, ||, backticks, and $() subshells.

    Args:
        command: The full command string.

    Returns:
        True if shell operators are found.
    """
    return bool(_SHELL_OPERATORS_RE.search(command))


def _validate_command(command: str) -> None:
    """Validate a command before execution.

    Args:
        command: The shell command to validate.

    Raises:
        CommandBlockedError: If the command is blocked or contains
            shell operators that could bypass the blocked list.
        ValueError: If the command is empty or too long.
    """
    if not command or not command.strip():
        raise ValueError("Command cannot be empty")

    if len(command) > 10000:
        raise ValueError("Command too long")

    if _is_blocked_command(command):
        raise CommandBlockedError(
            f"Command '{command}' is blocked for security reasons"
        )

    if _has_shell_operators(command):
        raise CommandBlockedError(
            f"Command '{command}' contains shell operators "
            "(pipes, chains, or subshells are not allowed)"
        )


def _validate_working_dir(working_dir: Optional[str]) -> Path:
    """Validate and resolve the working directory.

    Args:
        working_dir: The working directory path.

    Returns:
        Resolved Path object for the working directory.

    Raises:
        WorkingDirectoryError: If the working directory is invalid.
    """
    if working_dir is None:
        return BASE_DIR

    try:
        path = Path(working_dir).resolve()
    except (OSError, ValueError) as exc:
        raise WorkingDirectoryError(f"Invalid working directory path: {exc}") from exc

    if not path.exists():
        raise WorkingDirectoryError(f"Working directory does not exist: {working_dir}")
    if not path.is_dir():
        raise WorkingDirectoryError(
            f"Working directory is not a directory: {working_dir}"
        )
    return path


def _safe_json(data: Dict[str, Any]) -> str:
    """Convert a dictionary to a JSON string.

    Args:
        data: The dictionary to convert.

    Returns:
        JSON string representation of the data.
    """
    return json.dumps(data, indent=2, default=str)


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
        "operation": operation,
        "result": {
            "stdout": stdout[:MAX_OUTPUT_SIZE] if stdout else "",
            "stderr": stderr[:MAX_OUTPUT_SIZE] if stderr else "",
            "return_code": return_code,
            "execution_time": round(execution_time, 3),
            "timed_out": timed_out,
            "command": command,
            "platform": CURRENT_OS,
            "working_dir": working_dir,
        },
        "metadata": {
            "timestamp": datetime.now().isoformat(),
        },
    }


def execute_command(
    intent: str,
    command: str,
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> str:
    """Execute a shell command and return the result.

    Args:
        intent: Why you're executing (e.g., "Checking git status")
        command: The shell command to execute
        timeout: Timeout in seconds (default: 30, max: 300)
        working_dir: Working directory (default: BASE_DIR)
        env: Additional environment variables

    Returns:
        JSON with stdout, stderr, return_code, execution_time, timed_out.
        Blocked: sudo, chmod, shutdown, rm -rf, etc.
    """
    logger.info(f"Executing shell command: {command}")
    logger.debug(f"Executing command to achieve: {intent}")

    _validate_command(command)

    actual_timeout = min(
        timeout if timeout is not None else DEFAULT_TIMEOUT,
        MAX_TIMEOUT,
    )
    resolved_working_dir = _validate_working_dir(working_dir)
    working_dir_str = str(resolved_working_dir)

    env_vars = dict(os.environ)
    if env:
        env_vars.update(env)

    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=resolved_working_dir,
            env=env_vars,
            capture_output=True,
            text=True,
            timeout=actual_timeout,
        )
        elapsed = time.time() - start_time

        response = _build_response(
            "execute_command",
            command,
            working_dir_str,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            execution_time=elapsed,
        )
        logger.info("Command executed with return code %s", result.returncode)
        return _safe_json(response)

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.warning(f"Command timed out after {actual_timeout}s")
        return _safe_json(
            _build_response(
                "execute_command",
                command,
                working_dir_str,
                execution_time=elapsed,
                timed_out=True,
            )
        )

    except FileNotFoundError:
        cmd_name = _extract_command_name(command)
        logger.error(f"Command not found: {cmd_name}")
        return _safe_json(
            _build_response(
                "execute_command",
                command,
                working_dir_str,
                stderr=f"Command not found: {cmd_name}",
                return_code=127,
            )
        )

    except PermissionError:
        logger.error(f"Permission denied executing command: {command}")
        return _safe_json(
            _build_response(
                "execute_command",
                command,
                working_dir_str,
                stderr="Permission denied",
                return_code=1,
            )
        )


def execute_command_safe(
    intent: str,
    command_name: str,
    args: List[str],
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
) -> str:
    """Execute a whitelisted command without shell interpretation.

    This function only allows commands from a predefined whitelist and
    runs them with ``shell=False`` to prevent shell injection attacks.

    Args:
        intent: Why you're executing (e.g., "Listing directory")
        command_name: Name of the command from the safe list
            (ls, cat, git, python, etc.)
        args: List of arguments for the command
        timeout: Timeout in seconds (default: 30, max: 300)
        working_dir: Working directory (default: BASE_DIR)

    Returns:
        JSON with stdout, stderr, return_code, execution_time.
        Preferred over execute_command for security.
    """
    if command_name not in SAFE_COMMANDS_SET:
        raise CommandBlockedError(f"Command '{command_name}' is not in the safe list")

    logger.info(f"Executing safe command: {command_name} {args}")
    logger.debug(f"Safe command to achieve: {intent}")

    actual_timeout = min(
        timeout if timeout is not None else DEFAULT_TIMEOUT,
        MAX_TIMEOUT,
    )
    resolved_working_dir = _validate_working_dir(working_dir)
    working_dir_str = str(resolved_working_dir)

    # Resolve the full path to the command to avoid PATH-based attacks.
    cmd_path = shutil.which(command_name)
    if cmd_path is None:
        return _safe_json(
            _build_response(
                "execute_command",
                f"{command_name} {' '.join(args)}",
                working_dir_str,
                stderr=f"Command not found: {command_name}",
                return_code=127,
            )
        )

    cmd_list = [cmd_path, *args]
    display_command = f"{command_name} {' '.join(args)}"

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd_list,
            shell=False,
            cwd=resolved_working_dir,
            capture_output=True,
            text=True,
            timeout=actual_timeout,
        )
        elapsed = time.time() - start_time

        response = _build_response(
            "execute_command",
            display_command,
            working_dir_str,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            execution_time=elapsed,
        )
        logger.info("Safe command executed with return code %s", result.returncode)
        return _safe_json(response)

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.warning(f"Safe command timed out after {actual_timeout}s")
        return _safe_json(
            _build_response(
                "execute_command",
                display_command,
                working_dir_str,
                execution_time=elapsed,
                timed_out=True,
            )
        )

    except PermissionError:
        logger.error(f"Permission denied: {display_command}")
        return _safe_json(
            _build_response(
                "execute_command",
                display_command,
                working_dir_str,
                stderr="Permission denied",
                return_code=1,
            )
        )


def execute_command_batch(
    intent: str,
    commands: List[Dict[str, Any]],
    stop_on_error: bool = True,
) -> str:
    """Execute multiple commands in sequence.

    Args:
        intent: Why you're batching (e.g., "Git status check")
        commands: List of command dicts, each with:
            - command: The shell command to execute
            - timeout: Optional timeout in seconds
            - working_dir: Optional working directory
            - continue_on_error: Optional, continue if this fails
        stop_on_error: Stop execution if a command fails (default: True)

    Returns:
        JSON with results[], total_execution_time, success_count,
        failure_count, stopped_early. Reduces token usage vs multiple
        individual calls.
    """
    logger.info(f"Executing {len(commands)} commands in batch")

    results = []
    success_count = 0
    failure_count = 0
    total_execution_time = 0.0
    stopped_early = False

    for i, cmd_dict in enumerate(commands):
        command = cmd_dict.get("command", "")
        timeout = cmd_dict.get("timeout")
        working_dir = cmd_dict.get("working_dir")
        continue_on_error = cmd_dict.get("continue_on_error", False)

        try:
            result_str = execute_command(
                intent=f"Batch command {i+1}/{len(commands)}: {command}",
                command=command,
                timeout=timeout,
                working_dir=working_dir,
            )
            result = json.loads(result_str)
            results.append(result)

            return_code = result["result"].get("return_code", -1)
            if return_code == 0:
                success_count += 1
            else:
                failure_count += 1
                if not continue_on_error and stop_on_error:
                    stopped_early = True
                    break

            total_execution_time += result["result"].get("execution_time", 0)

        except Exception as e:
            results.append(
                {
                    "command": command,
                    "error": str(e),
                    "success": False,
                }
            )
            failure_count += 1
            if not continue_on_error and stop_on_error:
                stopped_early = True
                break

    response = {
        "operation": "execute_command_batch",
        "result": {
            "results": results,
            "total_execution_time": round(total_execution_time, 3),
            "success_count": success_count,
            "failure_count": failure_count,
            "stopped_early": stopped_early,
        },
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_commands": len(commands),
        },
    }

    logger.info(
        "Batch execution complete: %s success, %s failures",
        success_count,
        failure_count,
    )
    return _safe_json(response)


def get_platform_info(intent: str) -> str:
    """Get information about the current platform.

    Args:
        intent: Why you're checking (e.g., "Determining shell syntax")

    Returns:
        JSON with os (windows/linux/darwin), shell (bash/powershell/cmd),
        home, path_separator, temp_dir.
    """
    logger.info("Getting platform information")

    response = {
        "operation": "get_platform_info",
        "result": {
            "os": CURRENT_OS,
            "shell": SHELL,
            "home": str(Path.home()),
            "path_separator": "\\" if IS_WINDOWS else "/",
            "temp_dir": tempfile.gettempdir(),
        },
        "metadata": {
            "timestamp": datetime.now().isoformat(),
        },
    }

    logger.debug(f"Platform info: {CURRENT_OS}, shell: {SHELL}")
    return _safe_json(response)
