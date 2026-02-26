"""Shell execution constants.

This module provides platform detection, timeout limits, and command
whitelists for safe shell command execution.
"""

import os
import platform
from pathlib import Path

# ============================================================================
# Platform Detection
# ============================================================================

CURRENT_OS = platform.system().lower()  # windows, linux, darwin
IS_WINDOWS = CURRENT_OS == "windows"
IS_MACOS = CURRENT_OS == "darwin"
IS_LINUX = CURRENT_OS == "linux"


def detect_shell() -> str:
    """Detect the default shell for the current platform.

    Returns:
        The shell name: "powershell", "cmd", "bash", or "zsh".
    """
    if IS_WINDOWS:
        # Check for PowerShell vs CMD
        if os.environ.get("PSMODULEPATH"):
            return "powershell"
        return "cmd"
    elif IS_MACOS:
        return os.environ.get("SHELL", "/bin/zsh")
    else:  # Linux and others
        return os.environ.get("SHELL", "/bin/bash")


SHELL = detect_shell()

# ============================================================================
# Timeout Limits
# ============================================================================

DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 300

# ============================================================================
# Output Limits
# ============================================================================

MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
MAX_LINE_LENGTH = 10000

# ============================================================================
# Safe Commands by Category
# ============================================================================

SAFE_COMMANDS = {
    "file_ops": [
        "ls",
        "dir",
        "cat",
        "type",
        "mkdir",
        "rmdir",
        "cp",
        "copy",
        "mv",
        "move",
        "rm",
        "del",
    ],
    "text": [
        "grep",
        "findstr",
        "sed",
        "awk",
        "sort",
        "uniq",
        "wc",
        "head",
        "tail",
    ],
    "system": [
        "whoami",
        "hostname",
        "date",
        "time",
        "uptime",
        "df",
        "du",
        "free",
        "vm_stat",
    ],
    "network": ["ping", "curl", "wget", "nslookup", "dig"],
    "dev": ["git", "npm", "pip", "python", "node", "uv"],
}

# Flatten safe commands for easy lookup
SAFE_COMMANDS_SET = {cmd for cmds in SAFE_COMMANDS.values() for cmd in cmds}

# ============================================================================
# Blocked Commands (Never Allowed)
# ============================================================================

BLOCKED_COMMANDS = [
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "useradd",
    "userdel",
    "passwd",
    "usermod",
    "iptables",
    "netsh",
    "route",
    "ifconfig",
    "format",
    "fdisk",
    "diskpart",
    "mkfs",
    "sudo",
    "su",
    "runas",
    "doas",
    "chmod",
    "chown",
    "icacls",
    "dd",
    "shred",
    "wipe",
]

# Windows-specific blocked commands
BLOCKED_WINDOWS = [
    "reg",
    "regedit",
    "sc",
    "net",
    "taskkill",
    "taskmgr",
]

# Unix-specific blocked commands
BLOCKED_UNIX = [
    "kill",
    "killall",
    "pkill",
    "systemctl",
    "service",
    "crontab",
    "at",
    "batch",
]

# ============================================================================
# Base Directory for Operations
# ============================================================================

BASE_DIR = Path(os.environ.get("TOOLS_DATA_FOLDER", ".files")).resolve()
BASE_DIR.mkdir(exist_ok=True)
