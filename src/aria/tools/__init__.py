"""Aria tool package.

This top-level package exports common helpers used by multiple tool
subpackages.
"""

from typing import Annotated

from pydantic import Field

from aria.tools.decorators import log_tool_call
from aria.tools.utils import (
    get_function_name,
    safe_json,
    tool_error_response,
    tool_response,
    tool_success_response,
    utc_timestamp,
)

#: Annotated type for the ``reason`` parameter shared by all tools.
#: Ensures the JSON schema sent to the LLM includes both a description
#: and marks the field as required.
Reason = Annotated[
    str,
    Field(description="Required. Brief explanation of why you are calling this tool."),
]

__all__: list[str] = [
    "Reason",
    "get_function_name",
    "log_tool_call",
    "safe_json",
    "tool_error_response",
    "tool_response",
    "tool_success_response",
    "utc_timestamp",
]
