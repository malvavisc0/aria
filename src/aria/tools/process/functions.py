"""Process manager tool for background process management."""

import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger

from aria.tools import tool_response
from aria.tools.decorators import log_tool_call

# Maximum lines of output to retain per stream
_MAX_LOG_LINES = 200

# Maximum number of concurrent processes
_MAX_PROCESSES = 5


@dataclass
class ManagedProcess:
    """A background process with non-blocking output capture."""

    proc: subprocess.Popen
    stdout_lines: deque = field(default_factory=lambda: deque(maxlen=_MAX_LOG_LINES))
    stderr_lines: deque = field(default_factory=lambda: deque(maxlen=_MAX_LOG_LINES))
    _threads: list = field(default_factory=list)

    def start_capture(self) -> None:
        """Start background threads to capture stdout/stderr."""
        if self.proc.stdout:
            t = threading.Thread(
                target=self._reader,
                args=(self.proc.stdout, self.stdout_lines),
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        if self.proc.stderr:
            t = threading.Thread(
                target=self._reader,
                args=(self.proc.stderr, self.stderr_lines),
                daemon=True,
            )
            t.start()
            self._threads.append(t)

    @staticmethod
    def _reader(stream, buf: deque) -> None:
        """Read lines from *stream* into *buf* until EOF."""
        try:
            for line in stream:
                buf.append(line)
        except (ValueError, OSError):
            # Stream closed
            pass


# In-memory process registry (processes die when the server restarts)
_processes: Dict[str, ManagedProcess] = {}


def _is_command_blocked(command: str) -> bool:
    """Check if a command contains blocked patterns."""
    blocked = [
        "sudo",
        "su ",
        "shutdown",
        "reboot",
        "halt",
        "rm -rf /",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:",
    ]
    cmd_lower = command.lower()
    return any(b in cmd_lower for b in blocked)


@log_tool_call
def process(
    reason: str,
    action: str,
    name: Optional[str] = None,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    timeout: Optional[int] = None,
) -> str:
    """Manage long-running background processes.

    When to use:
        - Use this to start processes that run in the background
          (e.g., dev servers, build watchers, data pipelines).
        - Use this to check status, read logs, or stop background
          processes.
        - Do NOT use this for one-off commands — use `shell` instead.
        - Do NOT use this for Python code execution — use `python`.

    Why:
        Unlike `shell` (which waits for completion), this tool manages
        processes that run asynchronously. You can start a server, check
        its logs later, and stop it when done.

    Actions:
        - "start": Start a new background process (requires name,
            command).
        - "stop": Stop a running process (requires name).
        - "status": Get status of a process (requires name).
        - "logs": Get recent output from a process (requires name).
        - "list": List all managed processes.

    Args:
        reason: Why you're managing this process (for logging/auditing).
        action: One of: start, stop, status, logs, list.
        name: Unique name for the process.
        command: Command to execute (for start).
        args: Optional list of command arguments.
        timeout: Timeout in seconds (for start).

    Returns:
        JSON with action-specific process data.

    Important:
        - In-memory only — processes are lost on server restart.
        - Maximum 5 concurrent processes.
        - Blocked commands include: sudo, shutdown, reboot, rm -rf /,
          fork bombs.
        - Logs retain the last 200 lines per stream (stdout/stderr).
    """
    action = action.lower().strip()

    if action == "start":
        return _action_start(reason, name, command, args, timeout)
    elif action == "stop":
        return _action_stop(reason, name)
    elif action == "status":
        return _action_status(reason, name)
    elif action == "logs":
        return _action_logs(reason, name)
    elif action == "list":
        return _action_list(reason)
    else:
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "error": f"Unknown action '{action}'. "
                "Valid: start, stop, status, logs, list",
            },
        )


def _action_start(
    reason: str,
    name: Optional[str],
    command: Optional[str],
    args: Optional[List[str]],
    timeout: Optional[int],
) -> str:
    """Start a new background process."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )
    if not command:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'command' parameter."},
        )

    if name in _processes:
        managed = _processes[name]
        if managed.proc.poll() is None:
            return tool_response(
                tool="process",
                reason=reason,
                data={"error": f"Process '{name}' is already running."},
            )

    if _is_command_blocked(command):
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Command contains blocked patterns."},
        )

    active_count = sum(1 for m in _processes.values() if m.proc.poll() is None)
    if active_count >= _MAX_PROCESSES:
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "error": (
                    f"Maximum of {_MAX_PROCESSES} concurrent processes "
                    f"reached ({active_count} running). Stop one first."
                ),
            },
        )

    cmd_list = [command] + (args or [])
    try:
        proc = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        managed = ManagedProcess(proc=proc)
        managed.start_capture()
        _processes[name] = managed
        logger.info(f"Started process '{name}': {cmd_list}")
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "action": "start",
                "name": name,
                "pid": proc.pid,
                "message": f"Process '{name}' started (PID: {proc.pid})",
            },
        )
    except FileNotFoundError:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Command not found: {command}"},
        )
    except Exception as exc:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Failed to start process: {exc}"},
        )


def _action_stop(reason: str, name: Optional[str]) -> str:
    """Stop a running process."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    managed = _processes.get(name)
    if managed is None or managed.proc.poll() is not None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' is not running."},
        )

    managed.proc.terminate()
    try:
        managed.proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        managed.proc.kill()
        managed.proc.wait()

    logger.info(f"Stopped process '{name}'")
    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "stop",
            "name": name,
            "message": f"Process '{name}' stopped",
        },
    )


def _action_status(reason: str, name: Optional[str]) -> str:
    """Get process status."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    managed = _processes.get(name)
    if managed is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    return_code = managed.proc.poll()
    status = "running" if return_code is None else f"exited ({return_code})"
    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "status",
            "name": name,
            "pid": managed.proc.pid,
            "status": status,
            "return_code": return_code,
        },
    )


def _action_logs(reason: str, name: Optional[str]) -> str:
    """Get recent output from a process (non-blocking).

    Returns the last ``_MAX_LOG_LINES`` lines captured by the background
    reader threads.  This never blocks, even if the process is still
    running.
    """
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    managed = _processes.get(name)
    if managed is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    stdout = "".join(managed.stdout_lines)
    stderr = "".join(managed.stderr_lines)

    # Truncate to last 5 KB to keep response size reasonable
    if len(stdout) > 5000:
        stdout = stdout[-5000:]
    if len(stderr) > 5000:
        stderr = stderr[-5000:]

    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "logs",
            "name": name,
            "stdout": stdout,
            "stderr": stderr,
        },
    )


def _action_list(reason: str) -> str:
    """List all managed processes."""
    entries = []
    for name, managed in _processes.items():
        return_code = managed.proc.poll()
        entries.append(
            {
                "name": name,
                "pid": managed.proc.pid,
                "status": "running" if return_code is None else "exited",
                "return_code": return_code,
            }
        )

    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "list",
            "count": len(entries),
            "processes": entries,
        },
    )
