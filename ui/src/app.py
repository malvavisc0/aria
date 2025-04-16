from typing import Dict, Optional

import chainlit as cl
from agno.utils.log import log_debug
from assistant.steps import process_elements, run_agent
from chainlit.types import ThreadDict
from commands.init import COMMANDS


@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    return default_user


async def initialize_webui():
    await cl.context.emitter.set_commands(COMMANDS)


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    log_debug(f"Resuming thread: {thread.get('id')}")
    await initialize_webui()


@cl.on_chat_start
async def on_chat_start():
    await initialize_webui()


@cl.on_message
async def on_message(message: cl.Message):
    agent = "chatter" if not message.command else message.command.lower()

    images = await process_elements(message=message, thread_id=message.thread_id)

    await run_agent(
        kind=agent,
        content=message.content,
        thread_id=message.thread_id,
        images=images,
    )
