"""Tests for process manager tool."""

import json
import subprocess
import sys
import time

import pytest

from aria.tools.process import process
from aria.tools.process.functions import _processes


@pytest.fixture(autouse=True)
def clean_processes():
    """Clean up any processes after each test."""
    yield
    for name, managed in list(_processes.items()):
        if managed.proc.poll() is None:
            managed.proc.terminate()
            try:
                managed.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                managed.proc.kill()
    _processes.clear()


class TestProcessManager:
    """Test suite for process manager tool."""

    def test_start_process(self):
        """Test starting a background process."""
        result = process(
            "Start echo server",
            action="start",
            name="test_echo",
            command=sys.executable,
            args=["-c", "import time; time.sleep(0.5)"],
        )
        data = json.loads(result)
        assert data["data"]["action"] == "start"
        assert data["data"]["name"] == "test_echo"
        assert data["data"]["pid"] is not None

    def test_start_duplicate_process(self):
        """Test that starting a duplicate process fails."""
        process(
            "Start first",
            action="start",
            name="dup_test",
            command=sys.executable,
            args=["-c", "import time; time.sleep(2)"],
        )
        result = process(
            "Start duplicate",
            action="start",
            name="dup_test",
            command=sys.executable,
            args=["-c", "print('hello')"],
        )
        data = json.loads(result)
        assert "error" in data["data"]
        assert "already running" in data["data"]["error"].lower()

    def test_start_blocked_command(self):
        """Test that blocked commands are rejected."""
        result = process(
            "Blocked command",
            action="start",
            name="blocked",
            command="sudo",
            args=["rm", "-rf", "/"],
        )
        data = json.loads(result)
        assert "error" in data["data"]
        assert "blocked" in data["data"]["error"].lower()

    def test_start_missing_name(self):
        """Test start without name returns error."""
        result = process("No name", action="start", command="echo")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_start_missing_command(self):
        """Test start without command returns error."""
        result = process("No command", action="start", name="no_cmd")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_start_command_not_found(self):
        """Test that non-existent command returns error."""
        result = process(
            "Not found",
            action="start",
            name="not_found",
            command="nonexistent_command_xyz",
        )
        data = json.loads(result)
        assert "error" in data["data"]
        assert "not found" in data["data"]["error"].lower()

    def test_stop_process(self):
        """Test stopping a running process."""
        process(
            "Start for stop",
            action="start",
            name="stop_test",
            command=sys.executable,
            args=["-c", "import time; time.sleep(10)"],
        )
        result = process("Stop process", action="stop", name="stop_test")
        data = json.loads(result)
        assert data["data"]["action"] == "stop"
        assert data["data"]["name"] == "stop_test"

    def test_stop_nonexistent_process(self):
        """Test stopping a non-existent process."""
        result = process("Stop nonexistent", action="stop", name="ghost")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_status_running(self):
        """Test status of a running process."""
        process(
            "Start for status",
            action="start",
            name="status_test",
            command=sys.executable,
            args=["-c", "import time; time.sleep(2)"],
        )
        result = process("Get status", action="status", name="status_test")
        data = json.loads(result)
        assert data["data"]["status"] == "running"
        assert data["data"]["pid"] is not None

    def test_status_nonexistent(self):
        """Test status of non-existent process."""
        result = process("Status nonexistent", action="status", name="ghost")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_list_processes(self):
        """Test listing all processes."""
        process(
            "Start for list",
            action="start",
            name="list_test",
            command=sys.executable,
            args=["-c", "import time; time.sleep(1)"],
        )
        result = process("List all", action="list")
        data = json.loads(result)
        assert data["data"]["count"] >= 1
        names = [p["name"] for p in data["data"]["processes"]]
        assert "list_test" in names

    def test_list_empty(self):
        """Test listing when no processes exist."""
        result = process("List empty", action="list")
        data = json.loads(result)
        assert data["data"]["count"] == 0

    def test_invalid_action(self):
        """Test invalid action returns error."""
        result = process("Bad action", action="explode")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_logs_nonblocking_on_running_process(self):
        """Test that logs returns immediately even for a running process.

        This is the key regression test: the old implementation called
        proc.stdout.read() which blocks until EOF on a running process.
        The new implementation uses background reader threads so logs
        returns instantly.
        """
        # Start a process that prints output and keeps running
        process(
            "Start for logs",
            action="start",
            name="logs_test",
            command=sys.executable,
            args=[
                "-c",
                (
                    "import sys, time; "
                    "print('hello from stdout', flush=True); "
                    "print('hello from stderr', file=sys.stderr, flush=True); "
                    "time.sleep(30)"
                ),
            ],
        )

        # Give the reader threads a moment to capture the output
        time.sleep(0.3)

        # This must return immediately (not block for 30 seconds)
        result = process("Get logs", action="logs", name="logs_test")
        data = json.loads(result)
        assert data["data"]["action"] == "logs"
        assert "hello from stdout" in data["data"]["stdout"]
        assert "hello from stderr" in data["data"]["stderr"]

    def test_logs_after_process_exits(self):
        """Test that logs are available after a process exits."""
        process(
            "Start short-lived",
            action="start",
            name="exited_logs",
            command=sys.executable,
            args=["-c", "print('done')"],
        )

        # Wait for process to finish and reader threads to drain
        time.sleep(0.5)

        result = process("Get logs", action="logs", name="exited_logs")
        data = json.loads(result)
        assert "done" in data["data"]["stdout"]

    def test_logs_nonexistent(self):
        """Test logs for non-existent process."""
        result = process("Logs nonexistent", action="logs", name="ghost")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_logs_missing_name(self):
        """Test logs without name returns error."""
        result = process("No name", action="logs")
        data = json.loads(result)
        assert "error" in data["data"]
