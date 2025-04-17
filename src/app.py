from os import environ
from typing import Dict, Optional

import chainlit as cl
from agno.utils.log import log_debug
from chainlit.types import ThreadDict

from assistant.steps import process_elements, run_agent
from commands import COMMANDS

OAUTH_GOOGLE_CLIENT_ID = environ.get("OAUTH_GOOGLE_CLIENT_ID")
OAUTH_GOOGLE_CLIENT_SECRET = environ.get("OAUTH_GOOGLE_CLIENT_SECRET")

if OAUTH_GOOGLE_CLIENT_ID and OAUTH_GOOGLE_CLIENT_SECRET:

    @cl.oauth_callback
    def oauth_callback(
        provider_id: str,
        token: str,
        raw_user_data: Dict[str, str],
        default_user: cl.User,
    ) -> Optional[cl.User]:
        log_debug(f"OAuth callback for {default_user.display_name}")
        return default_user

else:

    @cl.password_auth_callback
    def auth_callback(username: str, password: str):
        if (username, password) == ("user", "password"):
            return cl.User(
                identifier="admin", metadata={"role": "admin", "provider": "credentials"}
            )
        else:
            return None


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    log_debug(f"Resuming thread: {thread.get('id')}")
    await cl.context.emitter.set_commands(COMMANDS)


@cl.on_chat_start
async def on_chat_start():
    log_debug("Starting chat")
    await cl.context.emitter.set_commands(COMMANDS)


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
