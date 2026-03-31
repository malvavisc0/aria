"""
Tests for sys.argv handling in Python code execution.

This test suite verifies that:
1. sys.argv is properly isolated during code execution
2. Custom argv values can be passed to scripts
3. SystemExit exceptions are handled gracefully
4. Scripts using argparse work correctly
"""

import json

from aria.tools.development.python import execute_python_code


class TestArgvHandling:
    """Test sys.argv handling in code execution."""

    def test_argparse_with_default_argv(self):
        """Test that argparse works with default argv (no arguments)."""
        code = """
import argparse

parser = argparse.ArgumentParser(description='Test CLI')
parser.add_argument('--name', type=str, default='World')
parser.add_argument('--count', type=int, default=1)

args = parser.parse_args()

for i in range(args.count):
    print(f"Hello, {args.name}! (greeting #{i+1})")
"""
        result = execute_python_code("Testing argparse", code)
        result_dict = json.loads(result)

        assert result_dict["data"]["result"]["success"] is True
        assert "Hello, World!" in result_dict["data"]["result"]["stdout"]

    def test_argparse_with_custom_argv(self):
        """Test that argparse works with custom argv values."""
        code = """
import argparse

parser = argparse.ArgumentParser(description='Test CLI')
parser.add_argument('--name', type=str, default='World')
parser.add_argument('--count', type=int, default=1)

args = parser.parse_args()

for i in range(args.count):
    print(f"Hello, {args.name}! (greeting #{i+1})")
"""
        result = execute_python_code(
            "Testing argparse with custom argv",
            code,
            argv=["test_cli.py", "--name", "Alice", "--count", "3"],
        )
        result_dict = json.loads(result)

        assert result_dict["data"]["result"]["success"] is True
        stdout = result_dict["data"]["result"]["stdout"]
        assert "Hello, Alice!" in stdout
        assert stdout.count("Hello, Alice!") == 3

    def test_sys_exit_zero(self):
        """Test that sys.exit(0) is handled gracefully."""
        code = """
import sys
print("Before exit")
sys.exit(0)
"""
        result = execute_python_code("Testing sys.exit(0)", code)
        result_dict = json.loads(result)

        assert result_dict["data"]["result"]["success"] is True
        assert result_dict["data"]["result"]["exit_code"] == 0

    def test_sys_exit_nonzero(self):
        """Test that sys.exit(1) is handled and marked as failure."""
        code = """
import sys
print("Before exit")
sys.exit(1)
"""
        result = execute_python_code("Testing sys.exit(1)", code)
        result_dict = json.loads(result)

        assert result_dict["data"]["result"]["success"] is False
        assert result_dict["data"]["result"]["exit_code"] == 1

    def test_argparse_help_flag(self):
        """Test that argparse --help is handled gracefully."""
        code = """
import argparse

parser = argparse.ArgumentParser(description='Test CLI')
parser.add_argument('--name', type=str, default='World')

args = parser.parse_args()
print(f"Hello, {args.name}!")
"""
        result = execute_python_code(
            "Testing argparse help", code, argv=["script.py", "--help"]
        )
        result_dict = json.loads(result)

        # --help causes sys.exit(0), which should be success
        assert result_dict["data"]["result"]["success"] is True
        assert result_dict["data"]["result"]["exit_code"] == 0

    def test_argv_isolation(self):
        """Test that sys.argv changes don't affect parent process."""
        code = """
import sys
print(f"sys.argv: {sys.argv}")
"""
        # Execute with custom argv
        result = execute_python_code(
            "Testing argv isolation", code, argv=["test.py", "arg1", "arg2"]
        )
        result_dict = json.loads(result)

        assert result_dict["data"]["result"]["success"] is True
        assert (
            "['test.py', 'arg1', 'arg2']"
            in result_dict["data"]["result"]["stdout"]
        )

        # Verify parent process argv is unchanged
        import sys

        assert "test.py" not in sys.argv
        assert "arg1" not in sys.argv
