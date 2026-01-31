"""
Constants for Python code execution and validation.

These constants define security limits, restricted builtins, and system
configuration parameters for Python code execution.

For shared timeout constants, import from aria2.tools.constants.
"""

# Restricted builtins for safe execution
# These builtins are removed from the execution environment to prevent
# dangerous code evaluation and execution
RESTRICTED_BUILTINS = {
    "compile",  # Prevent arbitrary code compilation
    "eval",  # Prevent arbitrary code evaluation
    "exec",  # Prevent arbitrary code execution
    "execfile",  # Prevent file execution (Python 2)
}

# Note: imports and file I/O (open) are allowed for flexibility
# Users can import modules and read/write files as needed
