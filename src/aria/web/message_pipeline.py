"""Message processing pipeline for the Aria web UI.

This module handles incoming user messages and orchestrates the agent workflow:
- Prompt enhancement (optional)
- File path extraction from uploaded files
- Memory management per thread
- Agent workflow execution with streaming responses
- Error handling and user feedback

The main entry point is `on_message_handler` which is called by Chainlit
whenever a user sends a message.
"""

from __future__ import annotations

import re
from typing import Any

import chainlit as cl
import httpx
from llama_index.core.agent.workflow import AgentOutput, AgentStream, ToolCall
from llama_index.core.memory import Memory
from loguru import logger

from aria.agents.prompt_enhancer import PromptEnhancementResult
from aria.config.models import Chat as ChatConfig
from aria.helpers.ui import maybe_remove_step, send_tool_step
from aria.web.session import create_memory, extract_file_paths
from aria.web.state import AppStateNotInitializedError, _state

# Regex patterns to detect LLM thinking/reasoning content
# These match opening tags (partial content being streamed)
THINKING_OPEN_PATTERNS = [
    re.compile(r"💭", re.IGNORECASE),
    re.compile(r"<think>", re.IGNORECASE),
    re.compile(r"<reasoning", re.IGNORECASE),
    re.compile(r"<reflection", re.IGNORECASE),
]

# These match closing tags
THINKING_CLOSE_PATTERNS = [
    re.compile(r"💭", re.IGNORECASE),
    re.compile(r"</think>", re.IGNORECASE),
    re.compile(r"</reasoning>", re.IGNORECASE),
    re.compile(r"</reflection>", re.IGNORECASE),
]


class ThinkingBlockDetector:
    """State machine to detect thinking/reasoning blocks across stream deltas.

    Handles the case where thinking tags are split across multiple deltas
    (e.g. ``<think`` in one chunk and ``ing>`` in the next) by maintaining
    a small pending buffer.
    """

    def __init__(self) -> None:
        self._pending: str = ""
        self._in_thinking: bool = False

    def process_delta(self, delta: str) -> tuple[bool, bool]:
        """Process a stream delta and return ``(entered, exited)`` flags.

        Args:
            delta: Text chunk from the LLM stream.

        Returns:
            (entered, exited) booleans for thinking block transitions.
        """
        self._pending += delta
        entered = False
        exited = False

        if not self._in_thinking:
            for pattern in THINKING_OPEN_PATTERNS:
                if pattern.search(self._pending):
                    self._in_thinking = True
                    entered = True
                    self._pending = ""
                    break
        else:
            for pattern in THINKING_CLOSE_PATTERNS:
                if pattern.search(self._pending):
                    self._in_thinking = False
                    exited = True
                    self._pending = ""
                    break

        # Keep pending buffer bounded to avoid unbounded growth
        if len(self._pending) > 50:
            self._pending = self._pending[-20:]

        return entered, exited

    @property
    def in_thinking(self) -> bool:
        """Whether we are currently inside a thinking block."""
        return self._in_thinking


def _extract_text_from_blocks(blocks: Any) -> str:
    """Extract text content from message blocks."""
    if not blocks:
        return ""
    parts = []
    for block in blocks:
        value = getattr(block, "text", None) or getattr(block, "content", None)
        if value and isinstance(value, str):
            parts.append(value.strip())
    return "\n".join(parts)


def _extract_response_text(response: Any) -> str:
    """Extract text content from an agent response object."""
    if response is None:
        return ""
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    blocks = getattr(response, "blocks", None)
    return _extract_text_from_blocks(blocks)


async def _handle_message(message: cl.Message) -> str:
    """Process and enhance a user message before agent execution.

    Handles prompt enhancement if requested via command, and extracts
    file paths from uploaded files to include in the prompt.

    Args:
        message: The incoming Chainlit message from the user.

    Returns:
        str: Processed prompt ready for agent execution.
    """
    prompt = message.content

    if message.command == "Enhance":
        if not _state.prompt_enhancer:
            logger.warning(
                "Prompt enhancer not available, returning original prompt"
            )
            return prompt
        try:
            response = await _state.prompt_enhancer.run(
                user_msg=message.content
            )
            results: PromptEnhancementResult = response.structured_response
            prompt = results.enhanced
            logger.debug("Prompt enhancement completed successfully")
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")

    file_paths = extract_file_paths(message)
    if file_paths:
        paths_block = "\n".join(f"- {p}" for p in file_paths)
        prompt = f"{prompt}\n\n[Uploaded files]:\n{paths_block}"
        logger.debug(f"Appended {len(file_paths)} file path(s) to prompt")

    return prompt


async def _show_thinking_step() -> cl.Step:
    """Show a 'thinking' step in the UI while the LLM is reasoning."""
    step = cl.Step(
        name="Thinking",
        type="tool",
        show_input=False,
        default_open=False,
    )
    await step.send()
    return step


async def _stream_agent_response(
    handler: Any,
    output: cl.Message,
) -> bool:
    """Stream agent events to the UI and return whether output was emitted.

    Iterates over the agent's streaming events, manages thinking-block
    detection, tool-call steps, and content buffering.

    Args:
        handler: The running agent workflow handler (with ``stream_events``
            and ``__await__``).
        output: The Chainlit message to stream tokens into.

    Returns:
        True if any visible content was emitted, False otherwise.
    """
    current_step: cl.Step | None = None
    thinking_step: cl.Step | None = None
    last_agent_output: AgentOutput | None = None
    stream_buffer: list[str] = []
    emitted_output = False
    thinking_detector = ThinkingBlockDetector()

    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            await maybe_remove_step(current_step)
            await maybe_remove_step(thinking_step)
            thinking_step = None
            current_step = await send_tool_step(event)
        elif isinstance(event, AgentStream):
            delta = event.delta or ""
            if delta:
                entered, exited = thinking_detector.process_delta(delta)
                if entered:
                    # Clear buffer — thinking content won't be shown
                    stream_buffer.clear()
                    await maybe_remove_step(current_step)
                    current_step = None
                    thinking_step = await _show_thinking_step()
                elif exited:
                    await maybe_remove_step(thinking_step)
                    thinking_step = None
                elif not thinking_detector.in_thinking:
                    stream_buffer.append(delta)
        elif isinstance(event, AgentOutput):
            last_agent_output = event
            if not event.tool_calls:
                await maybe_remove_step(current_step)
                await maybe_remove_step(thinking_step)
                thinking_step = None
                current_step = None
                content = "".join(
                    stream_buffer
                ).strip() or _extract_response_text(event.response)
                if content:
                    await output.stream_token(content)
                    emitted_output = True
                stream_buffer.clear()

    # Final fallback — use the handler result if nothing was emitted
    handler_result = await handler

    if not emitted_output:
        await maybe_remove_step(current_step)
        await maybe_remove_step(thinking_step)
        current_step = None
        thinking_step = None
        result_response = getattr(handler_result, "response", None)
        content = "".join(stream_buffer).strip() or _extract_response_text(
            result_response
        )
        if content:
            await output.stream_token(content)
            emitted_output = True

    if not emitted_output:
        agent_name = (
            last_agent_output.current_agent_name
            if last_agent_output is not None
            else "unknown"
        )
        tool_call_count = (
            len(last_agent_output.tool_calls)
            if last_agent_output is not None and last_agent_output.tool_calls
            else 0
        )
        logger.warning(
            "No assistant output emitted for message "
            f"(agent={agent_name}, tool_calls={tool_call_count})."
        )
        output.content = (
            "I couldn't produce a visible response for that request. "
            "Please try again."
        )

    return emitted_output


async def on_message_handler(message: cl.Message) -> None:
    """Handle incoming user messages and execute the agent workflow.

    This is the main entry point for processing user messages. It:
    1. Validates app state is initialized
    2. Processes the message (enhancement, file extraction)
    3. Gets or creates memory for the thread
    4. Runs the agent workflow with streaming response
    5. Handles errors and sends appropriate feedback to user

    Args:
        message: The incoming Chainlit message from the user.
    """
    output = cl.Message(content="")

    try:
        _state.validate_initialized()
        prompt = await _handle_message(message)

        memory: Memory | None = cl.user_session.get("memory")
        if memory is None:
            memory = create_memory(message.thread_id)
            cl.user_session.set("memory", memory)
            logger.debug(f"Created new Memory for thread {message.thread_id}")

        handler = _state.agents_workflow.run(
            user_msg=prompt,
            memory=memory,
            max_iterations=ChatConfig.max_iteration,
        )

        await _stream_agent_response(handler, output)
        await output.send()

    except AppStateNotInitializedError as e:
        logger.error(f"App state not initialized: {e}")
        output.content = (
            "The application is not fully initialized. "
            "Please wait a moment and try again."
        )
        await output.send()

    except httpx.TimeoutException as e:
        logger.error(f"Request timed out: {e}")
        output.content = (
            "The model took too long to respond. " "Please try again."
        )
        await output.send()

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error processing message: {e}")

        if "maximum context length" in error_msg.lower():
            output.content = (
                "The conversation has grown too large for the embeddings "
                "model to process. Please start a new conversation."
            )
        else:
            output.content = "An error occurred. Please try again."
        await output.send()
