# File Tools (`aria.tools.files.functions`)

This file documents the tools implemented in [`aria.tools.files.functions`](src/aria2/tools/files/functions.py:1).

## Available tools

---

## File Reading Tools

### `read_file_chunk(intent: str, file_name: str, chunk_size: int = 100, offset: int = 0)`
Read file in chunks - PRIMARY method for reading files.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR
- `chunk_size`: Lines to read (default: 100, max: 10000)
- `offset`: Starting line number (0-indexed, default: 0)

**Returns:**
- JSON with lines, offset, chunk_size, total_lines, has_more, next_offset

**When to use:**
- Large files (>500 lines) to avoid memory issues
- Iterative file processing
- When you need pagination through file content

**Reason Example:**
```python
read_file_chunk("Read first 100 lines of config to find database settings", "config.py", 100, 0)
```

**Note:**
- Use `has_more` and `next_offset` to iterate through large files
- This is the PRIMARY method for reading files - use for all files except small ones (<500 lines)

---

### `read_full_file(intent: str, file_name: str, max_lines: int = 1000)`
Read entire file content - ONLY for small files.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR
- `max_lines`: Safety limit (default: 1000)

**Returns:**
- JSON with content (full file as string), total_lines

**When to use:**
- Small files (<500 lines)
- Configuration files
- Short scripts or documents

**Warning:**
- Only use for small files. For larger files, use `read_file_chunk()`.

**Reason Example:**
```python
read_full_file("Read entire config to understand all settings", "config.json")
```

---

### `get_file_info(intent: str, file_name: str)`
Get file metadata including size, lines, and MIME type.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR

**Returns:**
- JSON with file_name, total_lines, file_size_bytes, mime_type

**When to use:**
- Before reading files to understand their size
- Deciding between `read_full_file` and `read_file_chunk`
- File discovery and inventory
- Checking file types and sizes

**Reason Example:**
```python
get_file_info("Check file size to decide how to read it", "example.txt")
```

---

### `file_exists(intent: str, file_name: str)`
Check if file or directory exists within BASE_DIR.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR

**Returns:**
- JSON with exists, is_file, is_directory flags

**When to use:**
- Before attempting read or write operations
- For conditional file operations
- To validate file existence

**Reason Example:**
```python
file_exists("Verify config exists before reading it", "config.json")
```

---

### `get_file_permissions(intent: str, file_name: str)`
Get file permissions and ownership information.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR

**Returns:**
- JSON with mode_octal, mode_symbolic, permissions breakdown, accessibility flags, owner_uid, group_gid, timestamps

**When to use:**
- Checking access rights before operations
- Verifying file security
- Understanding file ownership

**Reason Example:**
```python
get_file_permissions("Check if I can write to this file", "config.json")
```

---

## File Writing Tools

### `write_full_file(intent: str, file_name: str, contents: str)`
Write entire file content - creates or overwrites file atomically.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR where file will be saved
- `contents`: Complete file content to write

**Returns:**
- JSON with file_name, bytes_written, lines_written, created, backup_created flags

**When to use:**
- Creating new files
- Overwriting existing files completely
- Writing complete file content at once

**Features:**
- Uses atomic write (temp file + rename) to prevent corruption
- Automatically creates backup with `.backup` extension if file exists
- Content must not exceed MAX_FILE_SIZE (100MB)

**Reason Example:**
```python
write_full_file("Create new module with refactored authentication logic", "auth.py", code)
```

---

### `append_to_file(intent: str, file_name: str, contents: str)`
Append content to end of file without reading it.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR
- `contents`: Content to append to the file

**Returns:**
- JSON with bytes_appended, new_total_lines, new_file_size

**When to use:**
- Adding content to existing files
- Logging information
- Incremental file building

**Reason Example:**
```python
append_to_file("Add new test case to existing test file", "test.py", test_code)
```

---

## File Editing Tools

### `insert_lines_at(intent: str, file_name: str, new_lines: list[str], offset: int)`
Insert lines at specific position without loading entire file.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR
- `new_lines`: List of lines to insert (without newline characters)
- `offset`: Line number to insert at (0-indexed, 0 = beginning of file)

**Returns:**
- JSON with lines_inserted, offset, old/new_total_lines

**When to use:**
- Adding new lines to existing files
- Inserting code blocks
- Adding comments or documentation

**Reason Example:**
```python
insert_lines_at("Add import statement at top of file", "main.py", ["import logging"], 0)
```

---

### `replace_lines_range(intent: str, file_name: str, new_lines: list[str], offset: int, length: int)`
Replace range of lines - SURGICAL editing without loading entire file.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR
- `new_lines`: New lines to insert (without newline characters)
- `offset`: Starting line number (0-indexed)
- `length`: Number of existing lines to replace

**Returns:**
- JSON with lines_replaced, new_lines_inserted, offset, old/new_total_lines, backup_created

**When to use:**
- Refactoring existing code
- Fixing bugs in specific functions
- Surgical updates to existing files

**Features:**
- A backup is automatically created before modification with `.backup` extension
- This is the recommended method for refactoring functions in large files

**Reason Example:**
```python
replace_lines_range("Fix the null pointer bug in process_data function", "main.py", new_code, 234, 10)
```

---

### `delete_lines_range(intent: str, file_name: str, offset: int, length: int)`
Delete range of lines from file without loading entire file.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: Relative path from BASE_DIR
- `offset`: Starting line number (0-indexed)
- `length`: Number of lines to delete

**Returns:**
- JSON with lines_deleted, offset, old/new_total_lines, backup_created

**When to use:**
- Removing deprecated code
- Cleaning up commented sections
- Deleting specific lines or blocks

**Features:**
- A backup is automatically created before deletion with `.backup` extension

**Reason Example:**
```python
delete_lines_range("Remove deprecated authentication code", "auth.py", 100, 15)
```

---

## File Management Tools

### `copy_file(intent: str, source: str, destination: str, overwrite: bool = False)`
Copy file to new location.

**Args:**
- `intent`: Your intended outcome with this tool call
- `source`: Source file path
- `destination`: Destination file path
- `overwrite`: Allow overwriting if destination exists (default: False)

**Returns:**
- JSON with source, destination, bytes_copied, success

**When to use:**
- Duplicating files
- Creating backups
- Copying templates

**Reason Example:**
```python
copy_file("Create backup before modifying critical config", "config.json", "config.backup.json")
```

---

### `move_file(intent: str, source: str, destination: str)`
Move file (alias for rename_file) with security validation.

**Args:**
- `intent`: Your intended outcome with this tool call
- `source`: Source file path
- `destination`: Destination file path

**Returns:**
- JSON formatted response containing move results

**When to use:**
- Relocating files
- Reorganizing project structure
- Moving files between directories

**Reason Example:**
```python
move_file("Organize helper functions into utils directory", "helper.py", "utils/helper.py")
```

---

### `rename_file(intent: str, old_name: str, new_name: str)`
Rename or move file within BASE_DIR.

**Args:**
- `intent`: Your intended outcome with this tool call
- `old_name`: Current file path (relative to BASE_DIR)
- `new_name`: New file path (relative to BASE_DIR)

**Returns:**
- JSON with old_name, new_name, success flag

**When to use:**
- Renaming files
- Moving files to different directories
- Reorganizing file structure

**Note:**
- Use `move_file()` for a more intuitive alias of this function

**Reason Example:**
```python
rename_file("Rename to follow naming convention", "temp.py", "user_service.py")
```

---

### `delete_file(intent: str, file_name: str)`
Permanently delete file from BASE_DIR.

**Args:**
- `intent`: Your intended outcome with this tool call
- `file_name`: File to delete (relative to BASE_DIR)

**Returns:**
- JSON with file_name, deleted, backup_created flags

**When to use:**
- Removing temporary files
- Cleaning up obsolete files
- Deleting generated files

**Features:**
- A backup is automatically created before deletion with `.backup` extension

**Reason Example:**
```python
delete_file("Remove temporary test file after validation", "temp_test.py")
```

---

## Directory Operations

### `create_directory(intent: str, dir_name: str)`
Create directory within BASE_DIR.

**Args:**
- `intent`: Your intended outcome with this tool call
- `dir_name`: Relative path for new directory (from BASE_DIR)

**Returns:**
- JSON with dir_name, created, already_existed flags

**When to use:**
- Setting up project structure
- Creating directories for organization
- Preparing directories for file operations

**Features:**
- Creates parent directories automatically

**Reason Example:**
```python
create_directory("Set up utils directory for helper modules", "src/utils")
```

---

### `get_directory_tree(intent: str, path: str = ".", max_depth: int = 3)`
Get hierarchical directory structure for project understanding.

**Args:**
- `intent`: Your intended outcome with this tool call
- `path`: Relative path from BASE_DIR (default: `"."` for root)
- `max_depth`: Maximum depth to traverse (default: 3)

**Returns:**
- JSON with tree structure, total_files, total_directories

**When to use:**
- Understanding project structure
- File discovery and navigation
- Building mental model of codebase

**Reason Example:**
```python
get_directory_tree("Understand project structure to plan refactoring", "src", 2)
```

---

### `list_files(intent: str, pattern: str = "**/*", recursive: bool = False, max_results: int = 500)`
List files matching glob pattern within BASE_DIR.

**Args:**
- `intent`: Your intended outcome with this tool call
- `pattern`: Glob pattern (default: `"**/*"` for all files)
- `recursive`: Search subdirectories (default: False)
- `max_results`: Maximum files to return (default: 500)

**Returns:**
- JSON with files array, count, truncated flag

**When to use:**
- Finding files matching specific patterns
- File inventory and discovery
- Listing project contents

**Reason Example:**
```python
list_files("Find all Python test files to run", "**/*.py", recursive=True)
```

---

## Search Tools

### `search_files_by_name(intent: str, regex_pattern: str, recursive: bool = True, max_results: int = 1000)`
Search for files by name using regex pattern.

**Args:**
- `intent`: Your intended outcome with this tool call
- `regex_pattern`: Regex pattern to match file names
- `recursive`: Search subdirectories (default: True)
- `max_results`: Maximum results to return (default: 1000)

**Returns:**
- JSON with matches array, count, truncated flag

**When to use:**
- Finding test files
- Locating specific file patterns
- File discovery with complex naming patterns

**Reason Example:**
```python
search_files_by_name("Locate all test files for the auth module", r"test_auth.*\\.py")
```

---

### `search_in_files(intent: str, regex_pattern: str, file_pattern: str = "**/*", recursive: bool = False, max_files: int = 100, max_matches: int = 1000, context_lines: int = 2)`
Search file contents using regex - STREAMING search.

**Args:**
- `intent`: Your intended outcome with this tool call
- `regex_pattern`: Regex pattern to search for
- `file_pattern`: Glob pattern for files to search (default: `"**/*"`)
- `recursive`: Search subdirectories (default: False)
- `max_files`: Maximum files to search (default: 100)
- `max_matches`: Maximum matches to return (default: 1000)
- `context_lines`: Lines of context around matches (default: 2)

**Returns:**
- JSON with matches (file, line_number, line_content, context), total_matches, files_searched

**When to use:**
- Code search and analysis
- Finding specific patterns in code
- Searching for TODO comments or fixes
- Locating function calls or variable usage

**Features:**
- Files are read line-by-line to avoid memory issues with large files
- Provides context lines before and after matches

**Reason Example:**
```python
search_in_files("Find all TODO comments to create task list", r"TODO:", "**/*.py", recursive=True)
```

---

## Tool Selection Guidelines

## Reading strategy
- **Small files (≤500 lines)**: Use `read_full_file`
- **Large files (>500 lines)**: Use `read_file_chunk` (track `has_more`, `next_offset`)
- **Check first**: Use `get_file_info` to determine file size
- **Search content**: Use `search_in_files` (regex + filters)
- **Validate**: Use `file_exists` before reads

## Writing and editing strategy
- **New/rewrite**: Use `write_full_file` (atomic)
- **Update sections**: Use `replace_lines_range` (surgical, auto-backup)
- **Add content**: Use `insert_lines_at` (position), `append_to_file` (end)
- **Remove**: Use `delete_lines_range` (auto-backup), `delete_file` (auto-backup)
- **Duplicate**: Use `copy_file` (optional overwrite)
- **Relocate**: Use `move_file`, `rename_file`

## Directory and search strategy
- **Organize**: Use `create_directory`, `get_directory_tree`
- **Find files**: Use `list_files`, `search_files_by_name` (regex)
- **Search content**: Use `search_in_files` (regex search with context)
- **Permissions**: Use `get_file_permissions`

---

## Safety Best Practices

1. **Auto-backup**: Destructive operations (`replace_lines_range`, `delete_lines_range`, `delete_file`) automatically create `.backup` files
2. **Atomic writes**: `write_full_file` uses temp file + rename to prevent corruption
3. **Check existence**: Always use `file_exists` before operations
4. **Backups retained**: On failure, backups are kept for recovery
5. **Granular tools**: Prefer `replace_lines_range` over `write_full_file` for updates
6. **File validation**: Check `get_file_info` before reading large files
7. **Size limits**: Respect MAX_FILE_SIZE (100MB) limits

---

## Error Handling

- Tools return JSON-formatted responses with error information
- Check `metadata.error` for error messages
- Handle truncated results gracefully (check `truncated` flag)
- Respect `max_results` limits
- Use `file_exists` to avoid operations on non-existent files
- Backups are automatically created before destructive operations

---

## Performance Considerations

1. **Use chunked reading** for large files (>500 lines)
2. **Limit search results** with `max_results`, `max_files`, `max_matches`
3. **Use streaming search** for content search (`search_in_files`)
4. **Check file size** before reading with `get_file_info`
5. **Prefer granular edits** (`replace_lines_range`) over full rewrites
6. **Use appropriate patterns** for file searches (more specific = faster)

---

## Common Patterns

## Pattern 1: Safe file reading
```python
# 1. Check if file exists
if file_exists("Verify file before reading", "data.txt")["result"]["exists"]:
    # 2. Get file info
    info = get_file_info("Check size to choose read method", "data.txt")
    
    # 3. Choose reading method based on size
    if info["result"]["total_lines"] < 500:
        content = read_full_file("Read small config file", "data.txt")
    else:
        # Read in chunks
        chunk = read_file_chunk("Read first chunk of large file", "data.txt", chunk_size=100, offset=0)
        while chunk["result"]["has_more"]:
            # Process chunk
            chunk = read_file_chunk("Read next chunk", "data.txt", offset=chunk["result"]["next_offset"])
```

## Pattern 2: Surgical file edit
```python
# 1. Find the lines to edit
matches = search_in_files("Find old function to replace", r"def old_function", file_pattern="module.py")

# 2. Replace specific function
replace_lines_range(
    "Replace old function with new implementation",
    "module.py",
    ["def new_function():", "    return 'updated'"],
    offset=matches["result"]["matches"][0]["line_number"] - 1,
    length=5
)
# Backup automatically created!
```

## Pattern 3: Project organization
```python
# 1. Create directory structure
create_directory("Set up utils directory", "src/utils")
create_directory("Set up tests directory", "tests")

# 2. Move files to appropriate locations
move_file("Organize helper into utils", "helper.py", "src/utils/helper.py")
move_file("Move test to tests directory", "test_helper.py", "tests/test_helper.py")

# 3. Verify structure
tree = get_directory_tree("Verify new structure", ".", max_depth=2)
```

---

## Tips

- Always check `file_exists` before operations
- Use `get_file_info` to decide between `read_full_file` and `read_file_chunk`
- Prefer `replace_lines_range` over `write_full_file` for updates
- Backups are automatic for destructive operations
- Use `search_in_files` for code analysis and pattern finding
- Respect file size limits and use chunked operations for large files
- **Provide specific, unique reasons for each tool call** - don't repeat the same reason
