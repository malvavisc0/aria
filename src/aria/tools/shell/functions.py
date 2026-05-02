"""Shell execution tool functions.

This module provides functions for executing shell commands with
proper timeout handling, output capture, and basic security constraints.

"""

import json
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from aria.tools import get_function_name, tool_response
from aria.tools.constants import DEFAULT_TIMEOUT, MAX_TIMEOUT
from aria.tools.decorators import log_tool_call
from aria.tools.shell.constants import CURRENT_OS
from aria.tools.shell.execution import _execute_command_internal
from aria.tools.shell.validation import (
    _validate_command,
    _validate_working_dir,
)


def _run_shell_command(
    reason: str,
    command: str,
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
    tool_name: str = "shell",
) -> str:
    """Execute a command string via the system shell.

    Args:
        reason: Why you're executing.
        command: Full command string (supports pipes, redirects, etc.).
        timeout: Timeout in seconds (default: 30, max: 300).
        working_dir: Working directory (default: BASE_DIR).
        tool_name: Tool name for response (default: "shell").

    Returns:
        JSON with stdout, stderr, return_code, execution_time.
    """
    logger.info(f"Executing shell command: {command}")
    logger.debug(f"Shell command reason: {reason}")

    # Validate against blocked commands before execution
    _validate_command(command)

    actual_timeout = min(
        timeout if timeout is not None else DEFAULT_TIMEOUT,
        MAX_TIMEOUT,
    )
    resolved_working_dir = _validate_working_dir(working_dir)

    response = _execute_command_internal(
        tool_name,
        command,
        command,
        resolved_working_dir,
        actual_timeout,
        shell=True,
    )
    return tool_response(
        tool=tool_name,
        reason=reason,
        data=response["data"],
    )


def _normalize_commands(
    commands: Union[str, Dict[str, Any], List[Any]],
) -> List[Dict[str, Any]]:
    """Normalize various command input formats into a uniform list.

    Supported formats:
        - ``"git status"`` — single string
        - ``["git status", "git push"]`` — list of strings
        - ``{"command": "git status"}`` — single dict with command key
        - ``[{"command": "git status"}, {"command": "git push"}]`` — list of dicts

    Args:
        commands: Input in any supported format.

    Returns:
        List of dicts, each with at least a ``command`` key.
    """
    if isinstance(commands, str):
        return [{"command": commands}]

    if isinstance(commands, dict):
        return [commands]

    if isinstance(commands, list):
        result = []
        for item in commands:
            if isinstance(item, str):
                result.append({"command": item})
            elif isinstance(item, dict):
                result.append(item)
        return result

    return []


@log_tool_call
def shell(
    reason: str,
    commands: Union[str, List[str], Dict[str, Any], List[Dict[str, Any]]],
    stop_on_error: bool = True,
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
) -> str:
    """Execute shell commands with timeout and security constraints.

    Args:
        reason: Why (logging).
        commands: str | list[str] | dict | list[dict].
            Dict keys: command, timeout, working_dir, continue_on_error.
        stop_on_error: Stop on first failure (default: True).
        timeout: Default timeout seconds (default: 30, max: 300).
        working_dir: Default working directory.

    Returns:
        JSON with results[] per command: stdout, stderr, return_code,
        execution_time, timed_out.
    """
    normalized = _normalize_commands(commands)

    if not normalized:
        return tool_response(
            tool=get_function_name(),
            reason=reason,
            data={
                "results": [],
                "total_execution_time": 0,
                "success_count": 0,
                "failure_count": 0,
                "stopped_early": False,
            },
        )

    results: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    total_execution_time = 0.0
    stopped_early = False

    for i, cmd_dict in enumerate(normalized):
        cmd_str = cmd_dict.get("command", "")
        cmd_timeout = cmd_dict.get("timeout", timeout)
        cmd_working_dir = cmd_dict.get("working_dir", working_dir)
        continue_on_error = cmd_dict.get("continue_on_error", False)

        display_command = cmd_str.strip()

        try:
            result_str = _run_shell_command(
                reason=(
                    f"Batch command {i + 1}/{len(normalized)}: "
                    f"{display_command}"
                ),
                command=cmd_str,
                timeout=cmd_timeout,
                working_dir=cmd_working_dir,
            )
            result = json.loads(result_str)
            results.append(result)

            return_code = result["data"].get("return_code", -1)
            if return_code == 0:
                success_count += 1
            else:
                failure_count += 1
                if not continue_on_error and stop_on_error:
                    stopped_early = True
                    break

            total_execution_time += result["data"].get("execution_time", 0)

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

    data = {
        "results": results,
        "total_execution_time": round(total_execution_time, 3),
        "success_count": success_count,
        "failure_count": failure_count,
        "stopped_early": stopped_early,
    }

    logger.info(
        "Batch execution complete: {} success, {} failures",
        success_count,
        failure_count,
    )
    return tool_response(
        tool=get_function_name(),
        reason=reason,
        data=data,
    )
