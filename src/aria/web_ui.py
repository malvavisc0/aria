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
from llama_index.core.memory import (
    FactExtractionMemoryBlock,
    InsertMethod,
    Memory,
)
from loguru import logger

from aria2.llm import get_agent_workflow, get_chat_llm
from aria2.ui import display_ui_feedback

MAIN_LLAMACPP_API_URL = "http://skynet.tago.lan:7070/v1"
MEMORY_LLAMACPP_API_URL = "http://skynet.tago.lan:7070/v1"
CHAT_MEMORY_TOKEN_LIMIT = 1024 * 24
MAX_FACTS = 20
MAX_ITERATIONS = 50

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


@cl.on_chat_start
async def start():
    """
    Chainlit chat-start handler.
    """
    memory_llm = get_chat_llm(api_base=MEMORY_LLAMACPP_API_URL)
    memory = Memory.from_defaults(
        insert_method=InsertMethod.USER,
        token_limit=CHAT_MEMORY_TOKEN_LIMIT,
        token_flush_size=1024 * 4,
        chat_history_token_ratio=0.7,
        memory_blocks=[
            FactExtractionMemoryBlock(
                llm=memory_llm, max_facts=MAX_FACTS, priority=1
            )
        ],
    )
    cl.user_session.set("memory", memory)


@cl.on_message
async def main(message: cl.Message):
    """
    Chainlit message handler.

    Args:
        message (cl.Message): The inbound user message.
    """
    msg = cl.Message(content="")

    handler = workflow.run(user_msg=message.content)

    # Stream events as they arrive
    async for event in handler.stream_events():
        if isinstance(event, AgentStream):
            await msg.stream_token(event.delta)
        elif isinstance(event, ToolCall):
            logger.debug(
                {
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_kwargs": event.tool_kwargs,
                }
            )
            await display_ui_feedback(event=event, message=msg)

    await msg.update()

    # Finalize the run
    _ = await handler
