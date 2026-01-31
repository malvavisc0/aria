# Python Development Tools (`aria.tools.development.python`)

This file documents the tools implemented in [`aria.tools.development.python`](src/aria2/tools/development/python.py:1).

## Python execution and syntax

---

## Python Development Tools

### `check_python_syntax(intent: str, code: str, filename: str = "<string>")`
Check Python syntax using AST parsing.

**Args:**
- `code`: Python code to validate
- `filename`: Name for error reporting (default: `"<string>"`)

**Returns:**
- JSON formatted result with validation status and error details if invalid
- `result.valid`: boolean indicating if syntax is valid
- `result.error_type`: error type if invalid (e.g., "SyntaxError")
- `result.message`: error message if invalid
- `result.line_number`: line number of error (if applicable)

**When to use:**
- Before executing any Python code
- After creating or modifying Python files
- For validation of code snippets

**Example:**
```python
result = check_python_syntax("def foo():\n    pass")
result["result"]["valid"]  # True
```

---

### `check_python_file_syntax(intent: str, file_path: str)`
Check Python syntax of a file.

**Args:**
- `file_path`: Path to Python file

**Returns:**
- JSON formatted result with validation status

**When to use:**
- After creating or editing Python files
- Before executing Python files

**Example:**
```python
result = check_python_file_syntax("script.py")
result["result"]["valid"]  # True
```

---

### `execute_python_code(intent: str, code: str, filename: str = "<string>", timeout: int = 30, capture_output: bool = True, argv: List[str] | None = None)`
Execute Python code snippets in a sandboxed environment.

**Args:**
- `code`: Python code to execute
- `filename`: Name for error reporting (default: `"<string>"`)
- `timeout`: Maximum execution time in seconds (default: 30)
- `capture_output`: Whether to capture stdout/stderr (default: True)
- `argv`: Custom sys.argv for the script (default: [filename])

**Returns:**
- JSON formatted result with execution status, output, and error details
- `result.success`: boolean indicating success
- `result.stdout`: captured standard output
- `result.stderr`: captured standard error
- `result.exit_code`: exit code if script exited (SystemExit)
- `result.traceback`: exception traceback if error occurred

**Security Features:**
- Restricted builtins (blocks eval, exec, compile)
- Execution timeout enforced
- Isolated namespace
- Imports and file I/O are allowed

**When to use:**
- Small code snippets that don't need file context
- Quick tests or debugging code
- Code that doesn't interact with the filesystem as a file

**Important Note:** DO NOT use for files created with `write_full_file()` - use `execute_python_file()` instead, which provides proper file context and path resolution.

**Example:**
```python
# Quick snippet testing
result = execute_python_code("print('Hello')")
result["result"]["stdout"]  # 'Hello\\n'

# With custom argv for CLI scripts
result = execute_python_code(
    code, argv=["script.py", "--name", "Alice"]
)
```

---

### `execute_python_file(intent: str, file_path: str, timeout: int = 30, capture_output: bool = True, argv: List[str] | None = None)`
Execute a Python file in a sandboxed environment with proper file context.

**Args:**
- `file_path`: Path to Python file (relative to BASE_DIR or absolute)
- `timeout`: Maximum execution time in seconds (default: 30)
- `capture_output`: Whether to capture stdout/stderr (default: True)
- `argv`: Custom sys.argv for the script (default: [file_path])

**Returns:**
- JSON formatted result with execution status and output

**When to use:**
- Files created with `write_full_file()` - ALWAYS use this function
- Scripts that need `__file__` or `__dir__` variables
- CLI applications with argparse
- Any code that interacts with the filesystem as a file

**Provides:**
- Proper `__file__` and `__dir__` context for path resolution
- Correct `sys.argv` handling for CLI applications
- File path resolution (supports both absolute and BASE_DIR relative paths)

**Example:**
```python
# Execute a file created with write_full_file()
result = execute_python_file("script.py", timeout=10)
result["result"]["success"]  # True

# CLI application with arguments
result = execute_python_file(
    "cli.py", argv=["cli.py", "--name", "Bob", "--count", "3"]
)
```

---

## Security Features

## Restricted builtins
The following potentially dangerous operations are restricted:
- File system access (use file operation tools instead)
- Network operations
- Process spawning
- System calls
- Import of certain modules

## Execution timeout
- Default: 30 seconds
- Prevents infinite loops and runaway processes
- Configurable per execution

## Isolated namespace
- Each execution runs in isolated namespace
- No state persistence between executions
- Prevents interference between runs

---

## Best Practices

### 1. Always Validate First
```python
# GOOD: Validate before execution
check_python_syntax(code)
if valid:
    execute_python_code(code)

# BAD: Execute without validation
execute_python_code(code)  # May fail with syntax error
```

### 2. Use Correct Execution Function
```python
# GOOD: Use execute_python_file for files created with write_full_file
write_full_file("script.py", code)
execute_python_file("script.py")

# BAD: Using execute_python_code for files
write_full_file("script.py", code)
execute_python_code(code)  # Missing file context!
```

### 3. Handle Timeouts
```python
# Set appropriate timeout for task
execute_python_code(long_running_code, timeout=60)

# For quick operations, use default
execute_python_code(simple_calc)
```

### 4. Use argv for CLI Applications
```python
# CLI script with argparse
cli_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--name')
args = parser.parse_args()
print(f"Hello, {args.name}!")
"""

write_full_file("cli.py", cli_code)
execute_python_file("cli.py", argv=["cli.py", "--name", "Alice"])
```

---

## Workflow Patterns

## Pattern 1: Develop and test
```python
# 1. Write code
code = """
def process_data(items):
    return [x * 2 for x in items]

result = process_data([1, 2, 3, 4, 5])
print(result)
"""

# 2. Validate syntax
check_python_syntax(code)

# 3. Execute and verify
result = execute_python_code(code)

# 4. If good, save to file
write_full_file("processor.py", code)
```

## Pattern 2: Validate and execute file
```python
# 1. Check file syntax
check_python_file_syntax("script.py")

# 2. If valid, execute
execute_python_file("script.py", timeout=60)

# 3. Check results
# Review stdout/stderr from execution
```

## Pattern 3: Iterative development
```python
# 1. Read existing code
code = read_full_file("module.py")

# 2. Modify code
modified_code = code + "\n\n# New function\ndef new_func(): pass"

# 3. Validate changes
check_python_syntax(modified_code)

# 4. Test execution
execute_python_code(modified_code)

# 5. Save if successful
write_full_file("module.py", modified_code)
```

## Pattern 4: CLI application development
```python
# 1. Create CLI script
cli_script = """
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='Process data')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    # Process data
    with open(args.input) as f:
        data = f.read()
    
    result = data.upper()
    
    with open(args.output, 'w') as f:
        f.write(result)
    
    print(f"Processed {args.input} -> {args.output}")

if __name__ == '__main__':
    main()
"""

# 2. Save and validate
write_full_file("cli_tool.py", cli_script)
check_python_file_syntax("cli_tool.py")

# 3. Execute with arguments
execute_python_file(
    "cli_tool.py",
    argv=["cli_tool.py", "--input", "data.txt", "--output", "result.txt"]
)
```

---

## Error Handling

## Syntax errors
```python
result = check_python_syntax(code)
if not result['result']['valid']:
    print(f"Syntax error: {result['result']['message']}")
    print(f"Line {result['result']['line_number']}")
    # Fix code and retry
```

## Runtime errors
```python
result = execute_python_code(code)
if result['result']['stderr']:
    print(f"Runtime error: {result['result']['stderr']}")
    if 'traceback' in result['result']:
        print(result['result']['traceback'])
    # Debug and fix
```

## Timeout errors
```python
result = execute_python_code(code, timeout=5)
if "timeout" in result.get('error', '').lower():
    # Increase timeout or optimize code
    execute_python_code(code, timeout=30)
```

---

## Common Use Cases

1. **Code Validation:** Check syntax before committing changes
2. **Quick Testing:** Test functions and logic snippets
3. **Data Processing:** Run data transformation scripts
4. **CLI Applications:** Execute command-line tools with arguments
5. **Prototyping:** Experiment with code before finalizing
6. **Script Execution:** Run complete Python programs with proper context
7. **Test Verification:** Execute test scripts to verify functionality

---

## Limitations

1. **No persistent state:** Each execution is isolated
2. **Restricted operations:** File system, network, and system calls limited
3. **Timeout constraints:** Long-running code may be terminated
4. **Import restrictions:** Some modules may not be available
5. **Resource limits:** Memory and CPU usage may be constrained

---

## Tips

- Always use `check_python_syntax` before execution
- Use `execute_python_file` for files created with `write_full_file`
- Use `argv` parameter for CLI applications
- Set appropriate timeouts for your use case
- Check both stdout and stderr in results
- Handle errors gracefully and provide clear feedback
- Test code incrementally rather than all at once

---

## Runtime limits and policies

### `get_restricted_builtins(intent: str)`
Return the restricted builtins list used by the sandbox.

### `get_timeout_limits(intent: str)`
Return the default and maximum timeout limits for the sandbox.
