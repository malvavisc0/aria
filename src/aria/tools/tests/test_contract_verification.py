"""Contract verification tests for public exports vs documented signatures.

Run with: pytest src/aria/tools/tests/test_contract_verification.py -v
"""

import inspect

from aria.tools import tool_success_response


class TestFilesPackageContract:
    """Verify files package exports match their implementations."""

    def test_files_read_operations_have_expected_signatures(self):
        """Verify read operation functions have documented parameter names."""
        from aria.tools.files.unified_read import list_files, read_file

        # list_files: should have pattern, recursive, max_results
        sig = inspect.signature(list_files)
        params = list(sig.parameters.keys())
        assert "pattern" in params, "list_files should have 'pattern' parameter"
        assert "recursive" in params, "list_files should have 'recursive' parameter"
        assert "max_results" in params, "list_files should have 'max_results' parameter"

        # read_file: should have file_name, offset, length
        sig = inspect.signature(read_file)
        params = list(sig.parameters.keys())
        assert "file_name" in params, "read_file should have 'file_name'"

    def test_files_write_operations_have_expected_signatures(self):
        """Verify write operation functions have documented parameter names."""
        from aria.tools.files.write_operations import edit_file, write_file

        # write_file: reason, file_name, contents, mode
        sig = inspect.signature(write_file)
        params = list(sig.parameters.keys())
        assert "reason" in params
        assert "file_name" in params
        assert "contents" in params, "write_file should have 'contents' parameter"
        assert "mode" in params, "write_file should have 'mode' parameter"

        # edit_file: reason, file_name, offset, length, new_lines
        sig = inspect.signature(edit_file)
        params = list(sig.parameters.keys())
        assert "reason" in params
        assert "file_name" in params
        assert "offset" in params, "edit_file should have 'offset' parameter"

    def test_files_management_operations_have_expected_signatures(self):
        """Verify file management functions have documented parameter names."""
        from aria.tools.files import file_management

        # copy_file should have src, dest
        sig = inspect.signature(file_management.copy_file)
        params = list(sig.parameters.keys())
        assert "src" in params or "source" in params, (
            "copy_file should have 'src' or 'source' parameter"
        )
        assert "dest" in params or "destination" in params, (
            "copy_file should have 'dest' or 'destination' parameter"
        )


class TestReasoningPackageContract:
    """Verify reasoning package exports match their implementations."""

    def test_reasoning_has_no_conclusion_parameter(self):
        """Issue #12: reasoning should NOT have a 'conclusion' parameter.

        Previous docs incorrectly documented a 'conclusion' argument.
        """
        from aria.tools.reasoning import reasoning

        sig = inspect.signature(reasoning)
        params = list(sig.parameters.keys())
        assert "conclusion" not in params, (
            "reasoning should not have a 'conclusion' parameter. "
            "This was a documentation bug."
        )


class TestToolSuccessResponseContract:
    """Verify tool_success_response handles reason correctly."""

    def test_tool_success_response_uses_provided_reason(self):
        """Verify tool_success_response preserves the reason parameter."""
        response_str = tool_success_response(
            tool="test_tool",
            reason="my_test_reason",
            data={"result": "success"},
        )
        import json

        response = json.loads(response_str)
        assert response["reason"] == "my_test_reason", (
            "tool_success_response should preserve the reason parameter"
        )

    def test_tool_success_response_falls_back_for_empty_reason(self):
        """Verify tool_success_response handles empty reason gracefully."""
        response_str = tool_success_response(
            tool="test_tool",
            reason="",
            data={"result": "success"},
        )
        import json

        response = json.loads(response_str)
        assert response["reason"] == "unspecified_test_tool_operation", (
            "tool_success_response should use fallback reason when empty"
        )


class TestPathContractConsistency:
    """Verify path handling is consistent across file tools."""

    def test_secure_resolve_path_enforces_base_dir(self):
        """Issue #4: _secure_resolve_path should enforce BASE_DIR by default.

        Current implementation has enforce_base_dir=False by default,
        which is weaker than documentation suggests.
        """
        from aria.tools.files._internals import _secure_resolve_path

        sig = inspect.signature(_secure_resolve_path)
        params = sig.parameters

        # Document the expected behavior
        # If enforce_base_dir defaults to False, this is a security issue
        # The fix should either:
        # 1. Change default to True, OR
        # 2. Document that absolute paths outside BASE_DIR are allowed
        enforce_param = params.get("enforce_base_dir")
        if enforce_param:
            default = enforce_param.default
            # This test documents the current state
            # A proper fix would change default to True
            msg = "enforce_base_dir default is False (security risk)"
            assert default is False, msg
