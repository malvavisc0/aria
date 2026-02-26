# Shell Tools (`aria.tools.shell.functions`)

This file documents the tools implemented in `aria.tools.shell.functions`.

## Available tools

---

### `execute_command(intent: str, command: str, timeout: int | None = None, working_dir: str | None = None, env: dict[str, str] | None = None)`

Execute a shell command with `shell=True` and return the result.

**Args:**
- `intent`: Purpose/reason for executing the command
- `command`: The shell command to execute
- `timeout`: Timeout in seconds (default: 30, max: 300)
- `working_dir`: Working directory (default: BASE_DIR)
- `env`: Additional environment variables

**Returns:**
- JSON string with `stdout`, `stderr`, `return_code`, `execution_time`, `timed_out`

**Security:**
- Commands are validated against a blocked list before execution
- Shell operators (pipes, chains, subshells) are rejected
- Timeout is enforced and capped at 300 seconds

**When to use:**
- General-purpose shell commands
- Commands that need shell features like globbing or redirection

**Example:**
```python
execute_command("List Python files in project", "ls *.py", timeout=10)
```

---

### `execute_command_safe(intent: str, command_name: str, args: list[str], timeout: int | None = None, working_dir: str | None = None)`

Execute a whitelisted command without shell interpretation (`shell=False`).

**Args:**
- `intent`: Purpose/reason for executing the command
- `command_name`: Name of the command from the safe list
- `args`: List of arguments for the command
- `timeout`: Timeout in seconds (default: 30, max: 300)
- `working_dir`: Working directory (default: BASE_DIR)

**Returns:**
- JSON string with execution results

**Security:**
- Only commands from the safe whitelist are allowed
- Runs with `shell=False` — no shell injection possible
- Arguments are passed as a list, not concatenated into a string

**When to use:**
- Preferred over `execute_command` when the command is in the safe list
- File operations: `ls`, `cat`, `mkdir`, `cp`, `mv`, `rm`
- Development tools: `git`, `npm`, `pip`, `python`, `node`, `uv`
- System info: `whoami`, `hostname`, `date`, `uptime`

**Example:**
```python
execute_command_safe("Check git status", "git", ["status"], timeout=10)
execute_command_safe("List directory contents", "ls", ["-la", "/tmp"])
```

---

### `execute_command_batch(intent: str, commands: list[dict], stop_on_error: bool = True)`

Execute multiple shell commands in sequence.

**Args:**
- `intent`: Purpose/reason for executing the commands
- `commands`: List of command dicts, each with:
    - `command`: The shell command to execute
    - `timeout`: Optional timeout in seconds
    - `working_dir`: Optional working directory
    - `continue_on_error`: Optional, continue if this command fails
- `stop_on_error`: Stop execution if a command fails (default: True)

**Returns:**
- JSON string with `results`, `total_execution_time`, `success_count`, `failure_count`, `stopped_early`

**When to use:**
- Running multiple related commands that don't depend on each other's output
- Reduces token usage compared to separate tool calls

**When NOT to use:**
- When you need output from one command to decide the next command

**Example:**
```python
execute_command_batch(
    "Gather project info",
    [
        {"command": "git status", "timeout": 10},
        {"command": "git branch", "timeout": 10},
        {"command": "git log -1 --oneline", "timeout": 5},
    ],
)
```

---

### `get_platform_info(intent: str)`

Get information about the current operating system and shell.

**Args:**
- `intent`: Purpose/reason for getting platform info

**Returns:**
- JSON string with `os`, `shell`, `home`, `path_separator`, `temp_dir`

**When to use:**
- When you need detailed platform information beyond what is in the system prompt
- Rarely needed — platform basics are already in the Additional Notes

**Example:**
```python
get_platform_info("Determine temp directory for scratch files")
```

---

## Safe Commands Reference

| Category | Commands |
|----------|----------|
| File Operations | `ls`, `dir`, `cat`, `type`, `mkdir`, `rmdir`, `cp`, `copy`, `mv`, `move`, `rm`, `del` |
| Text Processing | `grep`, `findstr`, `sed`, `awk`, `sort`, `uniq`, `wc`, `head`, `tail` |
| System Info | `whoami`, `hostname`, `date`, `time`, `uptime`, `df`, `du`, `free`, `vm_stat` |
| Network | `ping`, `curl`, `wget`, `nslookup`, `dig` |
| Development | `git`, `npm`, `pip`, `python`, `node`, `uv` |

## Blocked Commands

Commands that are always rejected: `shutdown`, `reboot`, `halt`, `poweroff`, `sudo`, `su`, `runas`, `doas`, `chmod`, `chown`, `dd`, `shred`, `passwd`, `useradd`, `userdel`, `iptables`, `fdisk`, `diskpart`, `mkfs`, and others.

Shell operators (`|`, `;`, `&&`, `||`, backticks, `$()`) are also rejected in `execute_command` to prevent chaining blocked commands.

---

## Tips

- Prefer `execute_command_safe` over `execute_command` when the command is whitelisted
- Use `execute_command_batch` to reduce token usage for multiple related commands
- Set appropriate timeouts — default is 30s, max is 300s
- Check `return_code` in results to determine success (0) or failure
- Check `timed_out` flag to detect timeout conditions
