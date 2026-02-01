"""
Aria2 Chainlit web UI.

This module wires Chainlit event handlers into a LlamaIndex AgentWorkflow
that coordinates specialist agents through handoffs.

Conversation state is stored per-Chainlit-session using a token-limited
`ChatMemoryBuffer`. The workflow manages specialist agents and handoffs.

The workflow manages agent handoffs and maintains conversation context across
specialist interactions.
"""

import os

import chainlit as cl
from llama_index.core.agent.workflow import AgentStream, ToolCall
from loguru import logger

from aria.llm import get_agent_workflow, get_chat_llm, get_default_memory
from aria.ui import maybe_remove_step, send_tool_step

MAIN_LLAMACPP_API_URL = "http://skynet.tago.lan:7070/v1"
MEMORY_LLAMACPP_API_URL = "http://skynet.tago.lan:7070/v1"
CHAT_MEMORY_TOKEN_LIMIT = 1024 * 8
MAX_FACTS = 20
MAX_ITERATIONS = 100

log_path = os.path.expanduser(".files/debug.log")
logger.remove()
logger.add(
    log_path,
    rotation="10 MB",
    level="DEBUG",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
)

shared_llm = get_chat_llm(api_base=MAIN_LLAMACPP_API_URL)
workflow = get_agent_workflow(llm=shared_llm)
memory = get_default_memory(
    llm=shared_llm, tokens=CHAT_MEMORY_TOKEN_LIMIT, max_facts=MAX_FACTS
)


@cl.on_chat_start
async def start():
    """
    Chainlit chat-start handler.
    """
    pass


@cl.on_message
async def main(message: cl.Message):
    """
    Chainlit message handler.

    Args:
        message (cl.Message): The inbound user message.
    """
    msg = cl.Message(content="")

    handler = workflow.run(
        user_msg=message.content, memory=memory, max_iterations=MAX_ITERATIONS
    )

    step: cl.Step | None = None
    # Stream events as they arrive
    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            logger.debug(
                {
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_kwargs": event.tool_kwargs,
                }
            )

            step = await send_tool_step(event)
        elif isinstance(event, AgentStream):
            step = await maybe_remove_step(step)
            await msg.stream_token(event.delta)

    await msg.update()

    # Finalize the run
    _ = await handler
