"""Tool schema compatibility helpers.

Some OpenAI-compatible API servers (notably llama.cpp's OpenAI shim) are
stricter about JSON Schema than OpenAI itself. In particular, schemas emitted
for untyped/`Any` parameters can end up as `{ "title": "Param" }` without a
`type`, which can cause 400 responses like:

`JSON schema conversion failed: Unrecognized schema: {"title":"Ticker"}`

This module provides a lightweight validation + filtering step so we can drop
incompatible tools at agent creation time instead of crashing at runtime.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from llama_index.core.tools import BaseTool
from loguru import logger


def _schema_has_type(schema: object) -> bool:
    """Return True if schema looks like a valid JSON Schema leaf.

    llama.cpp expects each parameter schema to have a recognizable shape.
    The common failure mode we guard against is a dict with only `title` (and
    maybe `default`), i.e. no `type`/`anyOf`/`oneOf`.
    """

    if not isinstance(schema, dict):
        return False

    if "type" in schema:
        return True

    # Some schemas are expressed via combinators.
    if any(k in schema for k in ("anyOf", "oneOf", "allOf", "$ref")):
        return True

    # Enum-only schemas are also acceptable.
    if "enum" in schema:
        return True

    return False


def is_llamacpp_compatible_tool_schema(tool: BaseTool) -> Tuple[bool, str]:
    """Best-effort validation of the tool schema.

    The schema returned by `tool.metadata.to_openai_tool()` must be acceptable
    to OpenAI-compatible servers. llama.cpp is stricter than OpenAI.
    """

    try:
        spec = tool.metadata.to_openai_tool(skip_length_check=True)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return False, f"to_openai_tool() failed: {type(exc).__name__}: {exc}"

    if not isinstance(spec, dict):
        return False, "tool spec is not a dict"

    # Only validate function tools.
    if spec.get("type") != "function":
        return True, ""

    fn = spec.get("function")
    if not isinstance(fn, dict):
        return False, "missing function block"

    params = fn.get("parameters")
    if not isinstance(params, dict):
        return False, "missing parameters"

    if params.get("type") != "object":
        return False, "parameters.type must be 'object'"

    props = params.get("properties", {})
    if not isinstance(props, dict):
        return False, "parameters.properties must be an object"

    for prop_name, prop_schema in props.items():
        if not _schema_has_type(prop_schema):
            return (
                False,
                (
                    f"property '{prop_name}' has no recognizable schema type "
                    f"(got {prop_schema})"
                ),
            )

    return True, ""


def filter_tools_for_llamacpp(
    tools: Sequence[BaseTool], *, agent_name: str
) -> List[BaseTool]:
    """Filter a tool list to avoid llama.cpp schema-conversion 400s."""

    kept: List[BaseTool] = []
    for tool in tools:
        ok, reason = is_llamacpp_compatible_tool_schema(tool)
        if ok:
            kept.append(tool)
            continue

        tool_name = getattr(tool.metadata, "name", "<unknown>")
        logger.warning(
            "Dropping tool due to incompatible JSON Schema for llama.cpp: "
            f"agent={agent_name} tool={tool_name} reason={reason}"
        )

    return kept
