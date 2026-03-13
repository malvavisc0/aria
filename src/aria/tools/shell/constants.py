"""Shell execution constants.

This module provides platform detection, timeout limits, and command
whitelists for safe shell command execution.
"""

import os
import platform
from pathlib import Path

from aria.config.folders import Data

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

MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
MAX_LINE_LENGTH = 10000

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

# Whitelist of allowed commands for execute_command
# Only commands in this list can be executed by the shell tool.
SAFE_COMMANDS = [
    # File operations
    "ls",
    "dir",
    "cat",
    "type",
    "cd",
    "pwd",
    "mkdir",
    "rmdir",
    "rm",
    "del",
    "cp",
    "copy",
    "mv",
    "move",
    "touch",
    "find",
    "grep",
    "rg",
    "head",
    "tail",
    "less",
    "more",
    "wc",
    "du",
    "df",
    "stat",
    "tree",
    # Git
    "git",
    # Python
    "python",
    "python3",
    "pip",
    "pip3",
    "uv",
    # System info
    "uname",
    "whoami",
    "id",
    "hostname",
    "ps",
    "top",
    "htop",
    "vm_stat",
    "free",
    "uptime",
    # Networking
    "curl",
    "wget",
    "ping",
    "ip",
    "netstat",
    "ss",
    "nslookup",
    "dig",
    "traceroute",
    "tracert",
    # Archive
    "tar",
    "zip",
    "unzip",
    "gzip",
    "gunzip",
    "7z",
    # Text editors
    "nano",
    "vim",
    "vi",
    "code",
    "sed",
    "awk",
    # Misc
    "echo",
    "printf",
    "date",
    "cal",
    "which",
    "where",
    "chmod",
    "chown",
    # Windows-specific
    "powershell",
    "cmd",
]


BASE_DIR = Path(os.environ.get("TOOLS_DATA_FOLDER", str(Data.path))).resolve()
BASE_DIR.mkdir(parents=True, exist_ok=True)
