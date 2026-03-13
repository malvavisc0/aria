"""Shell execution tool functions.

This module provides functions for executing shell commands safely with
proper timeout handling, output capture, and security constraints.
"""

import json
import shlex
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from aria.tools import safe_json, utc_timestamp
from aria.tools.constants import DEFAULT_TIMEOUT, MAX_TIMEOUT
from aria.tools.shell.constants import CURRENT_OS, SAFE_COMMANDS, SHELL
from aria.tools.shell.exceptions import CommandBlockedError
from aria.tools.shell.execution import (
    _build_response,
    _execute_command_internal,
)
from aria.tools.shell.validation import (
    _has_shell_operators,
    _is_blocked_command,
    _validate_working_dir,
)


def execute_command(
    intent: str,
    command_name: str,
    args: List[str],
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
) -> str:
    """Execute a whitelisted command without shell interpretation.

    Args:
        intent: Why you're executing (e.g., "Listing directory")
        command_name: Name of the command from the safe list
            (ls, cat, git, python, etc.)
        args: List of arguments for the command
        timeout: Timeout in seconds (default: 30, max: 300)
        working_dir: Working directory (default: BASE_DIR)

    Returns:
        JSON with stdout, stderr, return_code, execution_time.
        Runs with shell=False for safety.
    """
    logger.info(f"Executing safe command: {command_name} {args}")
    logger.debug(f"Safe command to achieve: {intent}")

    # Validate against blocked commands before execution
    if _is_blocked_command(command_name):
        raise CommandBlockedError(
            f"Command '{command_name}' is blocked for security reasons"
        )

    # Validate command against safe list - only allow specific whitelisted
    # commands. This provides an additional layer of security.
    if _has_shell_operators(command_name):
        raise CommandBlockedError(
            f"Command '{command_name}' contains shell operators "
            "(pipes, chains, or subshells are not allowed)"
        )

    # Check if command is in the whitelist
    if command_name not in SAFE_COMMANDS:
        raise CommandBlockedError(
            f"Command '{command_name}' is not in the safe list"
        )

    actual_timeout = min(
        timeout if timeout is not None else DEFAULT_TIMEOUT,
        MAX_TIMEOUT,
    )
    resolved_working_dir = _validate_working_dir(working_dir)

    # Resolve the full path to the command to avoid PATH-based attacks.
    cmd_path = shutil.which(command_name)
    if cmd_path is None:
        return safe_json(
            _build_response(
                "execute_command",
                f"{command_name} {' '.join(args)}",
                str(resolved_working_dir),
                stderr=f"Command not found: {command_name}",
                return_code=127,
            )
        )

    cmd_list = [cmd_path, *args]
    display_command = f"{command_name} {' '.join(args)}"
    response = _execute_command_internal(
        "execute_command",
        display_command,
        cmd_list,
        resolved_working_dir,
        actual_timeout,
        shell=False,
    )
    return safe_json(response)


def execute_command_batch(
    intent: str,
    commands: List[Dict[str, Any]],
    stop_on_error: bool = True,
) -> str:
    """Execute multiple commands in sequence.

    Args:
        intent: Why you're batching (e.g., "Git status check")
        commands: List of command dicts, each with:
            - command_name: The command to execute
            - args: Optional list of command arguments
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
        command_name = cmd_dict.get("command_name", "")
        args = cmd_dict.get("args", [])
        timeout = cmd_dict.get("timeout")
        working_dir = cmd_dict.get("working_dir")
        continue_on_error = cmd_dict.get("continue_on_error", False)

        # Legacy fallback for old batch payloads using a single command string.
        if not command_name and "command" in cmd_dict:
            parsed = shlex.split(str(cmd_dict.get("command", "")))
            command_name = parsed[0] if parsed else ""
            args = parsed[1:] if len(parsed) > 1 else []

        display_command = f"{command_name} {' '.join(args)}".strip()

        try:
            result_str = execute_command(
                intent=(
                    f"Batch command {i+1}/{len(commands)}: "
                    f"{display_command}"
                ),
                command_name=command_name,
                args=args,
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
                    "command": display_command,
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
            "timestamp": utc_timestamp(),
            "total_commands": len(commands),
        },
    }

    logger.info(
        "Batch execution complete: %s success, %s failures",
        success_count,
        failure_count,
    )
    return safe_json(response)


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
            "path_separator": "\\" if CURRENT_OS == "windows" else "/",
            "temp_dir": tempfile.gettempdir(),
        },
        "metadata": {
            "timestamp": utc_timestamp(),
        },
    }

    logger.debug(f"Platform info: {CURRENT_OS}, shell: {SHELL}")
    return safe_json(response)
