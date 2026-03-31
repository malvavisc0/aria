"""Shell execution tool functions.

This module provides functions for executing shell commands safely with
proper timeout handling, output capture, and security constraints.

Phase 6 consolidation: execute_command + execute_command_batch → shell
"""

import json
import shlex
import shutil
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from aria.tools import get_function_name, tool_response
from aria.tools.constants import DEFAULT_TIMEOUT, MAX_TIMEOUT
from aria.tools.shell.constants import CURRENT_OS
from aria.tools.shell.execution import _execute_command_internal
from aria.tools.shell.validation import (
    _validate_command,
    _validate_working_dir,
)


def _execute_single_command(
    intent: str,
    command_name: str,
    args: List[str],
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
    tool_name: str = "shell",
) -> str:
    """Execute a single whitelisted command without shell interpretation.

    Args:
        intent: Why you're executing
        command_name: Name of the command from the safe list
        args: List of arguments for the command
        timeout: Timeout in seconds (default: 30, max: 300)
        working_dir: Working directory (default: BASE_DIR)
        tool_name: Tool name for response (default: "shell")

    Returns:
        JSON with stdout, stderr, return_code, execution_time.
    """
    logger.info(f"Executing safe command: {command_name} {args}")
    logger.debug(f"Safe command to achieve: {intent}")

    # Validate against blocked commands before execution
    _validate_command(command_name)

    actual_timeout = min(
        timeout if timeout is not None else DEFAULT_TIMEOUT,
        MAX_TIMEOUT,
    )
    resolved_working_dir = _validate_working_dir(working_dir)

    # Resolve the full path to the command to avoid PATH-based attacks.
    cmd_path = shutil.which(command_name)
    if cmd_path is None:
        return tool_response(
            tool=tool_name,
            intent=intent,
            data={
                "stdout": "",
                "stderr": f"Command not found: {command_name}",
                "return_code": 127,
                "execution_time": 0.0,
                "timed_out": False,
                "command": f"{command_name} {' '.join(args)}",
                "platform": CURRENT_OS,
                "working_dir": str(resolved_working_dir),
            },
        )

    cmd_list = [cmd_path, *args]
    display_command = f"{command_name} {' '.join(args)}"
    response = _execute_command_internal(
        tool_name,
        display_command,
        cmd_list,
        resolved_working_dir,
        actual_timeout,
        shell=False,
    )
    return tool_response(
        tool=tool_name,
        intent=intent,
        data=response["data"],
    )


def shell(
    intent: str,
    commands: Union[Dict[str, Any], List[Dict[str, Any]]],
    stop_on_error: bool = True,
    timeout: Optional[int] = None,
    working_dir: Optional[str] = None,
) -> str:
    """Execute shell commands safely.

    Merges execute_command + execute_command_batch into one tool.
    Accepts a single command dict or a list of command dicts.

    Args:
        intent: Why you're executing (e.g., "Git status check")
        commands: Single dict or list of dicts, each with:
            - command_name: The command to execute
            - args: Optional list of command arguments
            - timeout: Optional timeout in seconds
            - working_dir: Optional working directory
            - continue_on_error: Optional, continue if this fails
            - command: (legacy) Full command string parsed via shlex
        stop_on_error: Stop execution if a command fails (default: True)
        timeout: Default timeout in seconds for all commands
        working_dir: Default working directory for all commands

    Returns:
        JSON with stdout, stderr, return_code for single command,
        or results[], total_execution_time, success_count for batch.
    """
    # Normalize single command to list
    if isinstance(commands, dict):
        commands = [commands]

    if not commands:
        return tool_response(
            tool=get_function_name(),
            intent=intent,
            data={
                "results": [],
                "total_execution_time": 0,
                "success_count": 0,
                "failure_count": 0,
                "stopped_early": False,
            },
        )

    # All commands go through batch execution for consistent format
    # (single dict was normalized to list above)
    results = []
    success_count = 0
    failure_count = 0
    total_execution_time = 0.0
    stopped_early = False

    for i, cmd_dict in enumerate(commands):
        command_name = cmd_dict.get("command_name", "")
        args = cmd_dict.get("args", [])
        cmd_timeout = cmd_dict.get("timeout", timeout)
        cmd_working_dir = cmd_dict.get("working_dir", working_dir)
        continue_on_error = cmd_dict.get("continue_on_error", False)

        # Legacy fallback for old batch payloads using a single command string.
        if not command_name and "command" in cmd_dict:
            parsed = shlex.split(str(cmd_dict.get("command", "")))
            command_name = parsed[0] if parsed else ""
            args = parsed[1:] if len(parsed) > 1 else []

        display_command = f"{command_name} {' '.join(args)}".strip()

        try:
            result_str = _execute_single_command(
                intent=(
                    f"Batch command {i+1}/{len(commands)}: "
                    f"{display_command}"
                ),
                command_name=command_name,
                args=args,
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
        "Batch execution complete: %s success, %s failures",
        success_count,
        failure_count,
    )
    return tool_response(
        tool=get_function_name(),
        intent=intent,
        data=data,
    )


# Backward-compatible aliases (used by tests during transition)
execute_command = _execute_single_command
execute_command_batch = shell
