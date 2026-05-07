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

import asyncio

import chainlit as cl
import httpx
from llama_index.core.agent.workflow import AgentOutput, AgentStream, ToolCall
from llama_index.core.memory import Memory
from loguru import logger
from workflows.handler import WorkflowHandler

from aria.agents.prompt_enhancer import PromptEnhancementResult
from aria.config.models import Chat as ChatConfig
from aria.helpers.ui import maybe_remove_step, send_tool_step
from aria.web.session import create_memory, extract_file_paths
from aria.web.state import AppStateNotInitializedError, _state

# Markdown wrappers for thinking content (blockquote style)
_THINKING_OPEN = "> "
_THINKING_CLOSE = "\n\n"


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
            logger.warning("Prompt enhancer not available, returning original prompt")
            return prompt
        try:
            response = await asyncio.wait_for(
                _state.prompt_enhancer.run(user_msg=message.content),
                timeout=30.0,
            )
            results: PromptEnhancementResult = response.structured_response
            prompt = results.enhanced
            logger.debug("Prompt enhancement completed successfully")
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            # Notify user so they know the original prompt was used
            await cl.ErrorMessage(
                content="Prompt enhancement failed, using original prompt.",
            ).send()

    # Deduplicate while preserving order (same file attached twice)
    file_paths = list(dict.fromkeys(extract_file_paths(message)))
    if file_paths:
        paths_block = "\n".join(f"- {p}" for p in file_paths)
        prompt = f"{prompt}\n\n[Uploaded files]:\n{paths_block}"
        logger.debug(f"Appended {len(file_paths)} file path(s) to prompt")

    # Inject thread context so Aria can pass --thread-id when spawning workers
    thread_id = message.thread_id
    if thread_id:
        prompt = f"[Thread ID: {thread_id}]\n\n{prompt}"
        logger.debug(f"Injected thread_id={thread_id} into prompt")

    return prompt


async def _stream_agent_response(
    handler: WorkflowHandler,
    output: cl.Message,
) -> bool:
    """Stream agent events to the UI and return whether output was emitted.

    Iterates over the agent's streaming events, manages thinking-block
    rendering and tool-call steps.  Thinking content is detected via
    LlamaIndex's ``AgentStream.thinking_delta`` field (both XML-tag and
    structured-reasoning styles are handled upstream by the framework).

    Args:
        handler: The running agent workflow handler (with ``stream_events``
            and ``__await__``).
        output: The Chainlit message to stream tokens into.

    Returns:
        True if any visible content was emitted, False otherwise.
    """
    current_step: cl.Step | None = None
    emitted = False
    thinking_opened = False

    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            await maybe_remove_step(current_step)
            if thinking_opened:
                await output.stream_token(_THINKING_CLOSE)
                thinking_opened = False
            current_step = await send_tool_step(event)

        elif isinstance(event, AgentStream):
            # LlamaIndex separates thinking from content via thinking_delta
            if event.thinking_delta:
                if not thinking_opened:
                    await maybe_remove_step(current_step)
                    current_step = None
                    await output.stream_token(_THINKING_OPEN)
                    thinking_opened = True
                    emitted = True
                await output.stream_token(event.thinking_delta.replace("\n", "\n> "))
            elif event.delta:
                if thinking_opened:
                    await output.stream_token(_THINKING_CLOSE)
                    thinking_opened = False
                await output.stream_token(event.delta)
                emitted = True

        elif isinstance(event, AgentOutput) and not event.tool_calls:
            if current_step is not None:
                await maybe_remove_step(current_step)
                current_step = None
            if thinking_opened:
                await output.stream_token(_THINKING_CLOSE)
                thinking_opened = False
            if not emitted and event.response.content:
                await output.stream_token(event.response.content)
                emitted = True

    # Always await the handler to retrieve the final result and avoid
    # unawaited-coroutine warnings.
    handler_result = await handler

    # Fallback — use the final result if nothing was streamed
    if not emitted:
        content = getattr(handler_result.response, "content", None) or ""
        if content:
            await output.stream_token(content)
            emitted = True

    if thinking_opened:
        await output.stream_token(_THINKING_CLOSE)

    if not emitted:
        logger.warning("No assistant output emitted for message.")

    return emitted


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
    if not _state.agents_workflow:
        logger.warning("Message received but agents_workflow is not configured")
        return

    try:
        _state.validate_initialized()
        prompt = await _handle_message(message)

        memory: Memory | None = cl.user_session.get("memory")
        # Reuse existing memory only if it belongs to the same thread;
        # Memory.session_id is set by create_memory() to the thread_id.
        if memory is None or memory.session_id != message.thread_id:
            memory = create_memory(message.thread_id)
            cl.user_session.set("memory", memory)
            logger.debug(f"Created new Memory for thread {message.thread_id}")

        handler = _state.agents_workflow.run(
            user_msg=prompt,
            memory=memory,
            max_iterations=ChatConfig.max_iteration,
        )

        output = cl.Message(content="")
        await _stream_agent_response(handler, output)
        await output.send()

    except AppStateNotInitializedError as e:
        logger.error(f"App state not initialized: {e}")
        await cl.Message(
            content=(
                "The application is not fully initialized. "
                "Please wait a moment and try again."
            )
        ).send()

    except httpx.TimeoutException as e:
        logger.error(f"Request timed out: {e}")
        await cl.Message(
            content="The model took too long to respond. Please try again."
        ).send()

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error processing message: {e}")

        if "maximum context length" in error_msg.lower():
            error_content = (
                "The conversation has grown too large for the model's "
                "context window. Please start a new conversation."
            )
        else:
            error_content = "An error occurred. Please try again."
        await cl.Message(content=error_content).send()
