"""Regression tests: every tool parameter must carry a description.

llama-index's auto-schema generation does NOT extract descriptions from
docstrings — it only picks up descriptions from ``Field(description=...)``
in explicit ``fn_schema`` models.  Without descriptions the LLM receives
bare parameter names with no guidance, leading to malformed tool calls.

These tests catch regressions where a new tool or parameter is added
without an explicit schema description.
"""

import json

import pytest

from aria.tools.registry import ALL_CATEGORIES, get_tools

# Categories that require an LLM API key or external services and
# may fail to load in CI.  We still want to test the tools that DO
# load, so we skip categories that fail and test everything else.
_SKIP_LOAD: set[str] = set()


def _load_tools_safely() -> list:
    """Load tools from all categories, skipping ones that fail to import."""
    tools = []
    for cat in ALL_CATEGORIES:
        try:
            tools.extend(get_tools([cat]))
        except Exception:
            _SKIP_LOAD.add(cat)
    return tools


TOOLS = _load_tools_safely()
TOOL_MAP = {t.metadata.name: t for t in TOOLS}


class TestAllToolSchemasHaveDescriptions:
    """Every parameter on every tool must have a Field description."""

    @pytest.mark.parametrize(
        "tool_name",
        sorted(TOOL_MAP.keys()),
    )
    def test_all_parameters_have_descriptions(self, tool_name: str):
        tool = TOOL_MAP[tool_name]
        schema = tool.metadata.fn_schema
        if schema is None:
            pytest.skip(f"{tool_name}: no fn_schema (not a function tool)")

        props = schema.model_json_schema().get("properties", {})
        missing = [param for param, info in props.items() if "description" not in info]
        assert not missing, (
            f"{tool_name}: parameters missing descriptions: {missing}\n"
            f"Schema:\n{json.dumps(props, indent=2)}"
        )


class TestAriaAgentToolSchemas:
    """Focused check on the tools the Aria agent uses every turn."""

    @pytest.fixture(autouse=True)
    def _load_aria_tools(self):
        from aria.tools.registry import AX, CORE_LITE, FILES_LITE

        self.tools = get_tools([CORE_LITE, FILES_LITE, AX])
        self.tool_map = {t.metadata.name: t for t in self.tools}

    def _schema_params(self, tool_name: str) -> dict:
        tool = self.tool_map[tool_name]
        schema = tool.metadata.fn_schema
        assert schema is not None, f"{tool_name} has no fn_schema"
        return schema.model_json_schema().get("properties", {})

    def test_reasoning_schema(self):
        props = self._schema_params("reasoning")
        assert props["action"]["description"]
        assert props["content"]["description"]

    def test_shell_schema(self):
        props = self._schema_params("shell")
        assert props["commands"]["description"]

    def test_ax_schema(self):
        props = self._schema_params("ax")
        assert props["family"]["description"]
        assert props["command"]["description"]

    def test_read_file_schema(self):
        props = self._schema_params("read_file")
        assert props["file_name"]["description"]
        assert "absolute" in props["file_name"]["description"].lower()

    def test_write_file_schema(self):
        props = self._schema_params("write_file")
        assert props["file_name"]["description"]
        assert props["contents"]["description"]
        assert props["mode"]["description"]

    def test_edit_file_schema(self):
        props = self._schema_params("edit_file")
        assert props["file_name"]["description"]
        assert props["offset"]["description"]
        assert props["length"]["description"]
        assert props["new_lines"]["description"]

    def test_list_files_schema(self):
        props = self._schema_params("list_files")
        assert props["pattern"]["description"]

    def test_search_files_schema(self):
        props = self._schema_params("search_files")
        assert props["pattern"]["description"]
        assert props["mode"]["description"]
