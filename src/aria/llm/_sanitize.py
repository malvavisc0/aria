"""Sanitization utilities for malformed tool-call arguments.

The ``ministral`` tool-call parser in vLLM sometimes produces malformed
``function.arguments`` strings (e.g. two concatenated JSON objects, trailing
garbage, or non-JSON text).  When LlamaIndex stores these in the chat history
and replays them on the next turn, vLLM's ``_postprocess_messages`` crashes
with ``JSONDecodeError: Extra data``.

This module provides helpers to clean up such arguments and a subclass of
:class:`~llama_index.llms.openai_like.OpenAILike` that applies them
transparently before every API call.
"""

import json
import re
from typing import Any, List, Sequence

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ToolCallBlock,
)
from llama_index.llms.openai_like import OpenAILike
from loguru import logger


def _sanitize_tool_call_args(arguments: Any) -> dict[str, Any]:
    """Ensure tool-call arguments are returned as a JSON-safe object.

    The model sometimes emits malformed JSON in ``function.arguments``
    (e.g. two concatenated JSON objects, trailing garbage, or non-JSON
    text).  When this string is forwarded to vLLM's
    ``_postprocess_messages`` it crashes with a 400 Bad Request because
    ``json.loads()`` raises ``JSONDecodeError: Extra data``.

    This helper attempts to recover a valid JSON object from the raw
    string.  If recovery fails, it returns an empty dict ``{}`` so the
    request can at least proceed (the tool will report a missing-argument
    error which is handled gracefully by the agent loop).
    """
    # Already a dict — nothing to do.
    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, (list, tuple)):
        return {"value": list(arguments)}

    if arguments is None:
        return {}

    if not isinstance(arguments, str):
        return {"value": arguments}

    # Fast path: valid JSON.
    try:
        parsed = json.loads(arguments)
        if isinstance(parsed, dict):
            return parsed
        # Non-dict JSON (e.g. a bare string) — wrap it.
        return {"value": parsed}
    except (json.JSONDecodeError, ValueError):
        pass

    # Slow path: attempt to extract the *first* complete JSON object.
    # This handles the "Extra data" case where the model emitted two
    # concatenated objects like  {"k":"v"}{"k2":"v2"}
    try:
        decoder = json.JSONDecoder()
        obj, _end = decoder.raw_decode(arguments.strip())
        if isinstance(obj, dict):
            logger.warning(
                "Recovered tool-call arguments from malformed JSON "
                "(truncated at char {}): {}",
                _end,
                arguments[:200],
            )
            return obj
        return {"value": obj}
    except (json.JSONDecodeError, ValueError):
        pass

    # Last resort: try to pull key=value pairs with a regex.
    kv_pattern = re.compile(r'"(\w+)"\s*:\s*"([^"]*)"')
    matches = kv_pattern.findall(arguments)
    if matches:
        recovered = {k: v for k, v in matches}
        logger.warning("Regex-recovered tool-call arguments: {}", recovered)
        return recovered

    logger.warning(
        "Could not sanitize tool-call arguments, defaulting to {{}}: {}",
        arguments[:200],
    )
    return {}


def _sanitize_tool_call_arguments_json(arguments: Any) -> str:
    """Return a JSON string safe for OpenAI-compatible `function.arguments`.

    vLLM expects `function.arguments` to remain a JSON string, not a Python
    dict. This helper preserves that wire-format invariant.
    """
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
            return json.dumps(parsed, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass

    sanitized = _sanitize_tool_call_args(arguments)
    return json.dumps(sanitized, ensure_ascii=False, separators=(",", ":"))


def _sanitize_messages(messages: Sequence[ChatMessage]) -> List[ChatMessage]:
    """Return *messages* with tool-call arguments guaranteed to be valid JSON.

    Two code paths carry tool calls inside ``ChatMessage``:

    1. ``ToolCallBlock`` objects in ``message.blocks`` — the modern path.
    2. ``additional_kwargs["tool_calls"]`` — legacy / streaming path
       using ``ChoiceDeltaToolCall`` objects.

    Both are sanitised here so vLLM never sees malformed JSON.
    """
    sanitized: List[ChatMessage] = []
    for msg in messages:
        changed = False

        # --- Path 1: ToolCallBlock in blocks ---
        # The OpenAI API requires `function.arguments` to be a JSON *string*.
        # LlamaIndex may store tool_kwargs as a dict (after parsing or via the
        # `or {}` fallback).  If a dict reaches utils.py, the openai SDK's
        # Pydantic model coerces it with str() → Python repr with single quotes
        # → vLLM fails with "Expecting property name enclosed in double quotes".
        new_blocks = list(msg.blocks)
        for i, block in enumerate(new_blocks):
            if isinstance(block, ToolCallBlock):
                raw = block.tool_kwargs
                if isinstance(raw, dict):
                    fixed_str = json.dumps(raw, ensure_ascii=False)
                elif isinstance(raw, str):
                    fixed_str = _sanitize_tool_call_arguments_json(raw)
                else:
                    fixed_str = json.dumps(
                        _sanitize_tool_call_args(raw),
                        ensure_ascii=False,
                    )
                if fixed_str != raw:
                    logger.debug(
                        "Sanitized ToolCallBlock.tool_kwargs: {} → {}",
                        repr(raw)[:120],
                        repr(fixed_str)[:120],
                    )
                    new_blocks[i] = ToolCallBlock(
                        tool_name=block.tool_name,
                        tool_kwargs=fixed_str,
                        tool_call_id=block.tool_call_id,
                    )
                    changed = True

        # --- Path 2: additional_kwargs["tool_calls"] ---
        ak = msg.additional_kwargs
        if "tool_calls" in ak:
            raw_tool_calls = ak["tool_calls"]
            new_tool_calls = []
            for tc in raw_tool_calls:
                # ChoiceDeltaToolCall is a Pydantic model; .function.arguments
                # is the raw string we need to fix.
                if hasattr(tc, "function") and hasattr(
                    tc.function, "arguments"
                ):
                    raw_args = tc.function.arguments
                    fixed = _sanitize_tool_call_arguments_json(raw_args)
                    if fixed != raw_args:
                        logger.debug(
                            "Sanitized additional_kwargs tool_call args: "
                            "{} → {}",
                            repr(raw_args)[:120],
                            repr(fixed)[:120],
                        )
                        tc.function.arguments = fixed
                        changed = True
                elif isinstance(tc, dict):
                    func = tc.get("function", {})
                    if "arguments" in func:
                        raw_args = func["arguments"]
                        fixed = _sanitize_tool_call_arguments_json(raw_args)
                        if fixed != raw_args:
                            func["arguments"] = fixed
                            changed = True
                new_tool_calls.append(tc)

        if changed:
            sanitized.append(
                ChatMessage(
                    role=msg.role,
                    blocks=new_blocks,
                    additional_kwargs=ak,
                    content=msg.content,
                )
            )
        else:
            sanitized.append(msg)

    return sanitized


class SanitizedOpenAILike(OpenAILike):
    """OpenAILike subclass that sanitizes tool-call arguments before API calls.

    The ``ministral`` tool-call parser in vLLM sometimes produces
    malformed ``function.arguments`` strings (e.g. two concatenated JSON
    objects).  When LlamaIndex stores these in the chat history and
    replays them on the next turn, vLLM's ``_postprocess_messages``
    crashes with ``JSONDecodeError: Extra data``.

    This subclass intercepts ``achat`` and ``astream_chat`` to clean up
    any malformed arguments before they reach the API.
    """

    async def achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> "ChatResponse":
        messages = _sanitize_messages(messages)
        return await super().achat(messages, **kwargs)

    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> "ChatResponseAsyncGen":
        messages = _sanitize_messages(messages)
        return await super().astream_chat(messages, **kwargs)
