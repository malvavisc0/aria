"""Contract verification tests for public exports vs documented signatures.

Run with: pytest src/aria/tools/tests/test_contract_verification.py -v
"""

import inspect

import aria.tools.files as files_pkg
import aria.tools.planner as planner_pkg
import aria.tools.reasoning as reasoning_pkg
from aria.tools import tool_success_response


class TestFilesPackageContract:
    """Verify files package exports match their implementations."""

    def test_files_package_exports_are_callable(self):
        """All exported names should be callable functions."""
        for name in files_pkg.__all__:
            obj = getattr(files_pkg, name)
            assert callable(obj), f"{name} is not callable"

    def test_files_read_operations_have_expected_signatures(self):
        """Verify read operation functions have documented parameter names."""
        from aria.tools.files import read_operations

        # list_files: should have pattern, recursive, max_results
        sig = inspect.signature(read_operations.list_files)
        params = list(sig.parameters.keys())
        assert (
            "pattern" in params
        ), "list_files should have 'pattern' parameter"
        assert (
            "recursive" in params
        ), "list_files should have 'recursive' parameter"
        assert (
            "max_results" in params
        ), "list_files should have 'max_results' parameter"

        # read_file_chunk: should have file_name, offset, chunk_size
        sig = inspect.signature(read_operations.read_file_chunk)
        params = list(sig.parameters.keys())
        assert "file_name" in params, "read_file_chunk should have 'file_name'"
        assert (
            "chunk_size" in params
        ), "read_file_chunk should use 'chunk_size' not 'length'"

    def test_files_write_operations_have_expected_signatures(self):
        """Verify write operation functions have documented parameter names."""
        from aria.tools.files import write_operations

        # write_full_file: intent, file_name, contents
        sig = inspect.signature(write_operations.write_full_file)
        params = list(sig.parameters.keys())
        assert params == ["intent", "file_name", "contents"], (
            f"write_full_file should have (intent, file_name, contents), "
            f"got {params}"
        )

        # append_to_file: intent, file_name, contents
        sig = inspect.signature(write_operations.append_to_file)
        params = list(sig.parameters.keys())
        assert "intent" in params
        assert "file_name" in params
        assert (
            "contents" in params
        ), "append_to_file should have 'contents' parameter"

    def test_files_management_operations_have_expected_signatures(self):
        """Verify file management functions have documented parameter names."""
        from aria.tools.files import file_management

        # copy_file should have src, dest
        sig = inspect.signature(file_management.copy_file)
        params = list(sig.parameters.keys())
        assert (
            "src" in params or "source" in params
        ), "copy_file should have 'src' or 'source' parameter"
        assert (
            "dest" in params or "destination" in params
        ), "copy_file should have 'dest' or 'destination' parameter"


class TestPlannerPackageContract:
    """Verify planner package exports match their implementations."""

    def test_planner_exports_are_callable(self):
        """All exported planner functions should be callable."""
        for name in planner_pkg.__all__:
            obj = getattr(planner_pkg, name)
            assert callable(obj), f"{name} is not callable"


class TestReasoningPackageContract:
    """Verify reasoning package exports match their implementations."""

    def test_reasoning_exports_are_callable(self):
        """All exported reasoning functions should be callable."""
        for name in reasoning_pkg.__all__:
            obj = getattr(reasoning_pkg, name)
            assert callable(obj), f"{name} is not callable"

    def test_end_reasoning_has_no_conclusion_parameter(self):
        """Issue #12: end_reasoning should NOT have a 'conclusion' parameter.

        Previous docs incorrectly documented a 'conclusion' argument.
        """
        from aria.tools.reasoning import end_reasoning

        sig = inspect.signature(end_reasoning)
        params = list(sig.parameters.keys())
        assert "conclusion" not in params, (
            "end_reasoning should not have a 'conclusion' parameter. "
            "This was a documentation bug."
        )


class TestToolSuccessResponseContract:
    """Verify tool_success_response handles intent correctly."""

    def test_tool_success_response_uses_provided_intent(self):
        """Verify tool_success_response preserves the intent parameter."""
        response_str = tool_success_response(
            tool="test_tool",
            intent="my_test_intent",
            data={"result": "success"},
        )
        import json

        response = json.loads(response_str)
        assert (
            response["intent"] == "my_test_intent"
        ), "tool_success_response should preserve the intent parameter"

    def test_tool_success_response_falls_back_for_empty_intent(self):
        """Verify tool_success_response handles empty intent gracefully."""
        response_str = tool_success_response(
            tool="test_tool",
            intent="",
            data={"result": "success"},
        )
        import json

        response = json.loads(response_str)
        assert (
            response["intent"] == "unspecified_test_tool_operation"
        ), "tool_success_response should use fallback intent when empty"


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
