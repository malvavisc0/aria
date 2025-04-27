from mimetypes import guess_type
from os import environ
from typing import Dict, Optional

import chainlit as cl
from chainlit.mcp import McpConnection
from chainlit.types import ThreadDict
from loguru import logger
from mcp import ClientSession

from assistant.agents.knowledge import get_knowledge_base
from assistant.steps import process_files, process_images, run_agent
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
        logger.info(f"OAuth callback for {default_user.display_name}")
        return default_user

else:

    @cl.password_auth_callback
    def auth_callback(username: str, password: str):
        if (username, password) == ("user", "password"):
            return cl.User(
                identifier="User",
                metadata={"role": "user", "provider": "credentials"},
            )
        else:
            return None


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Crazy yet true Rome",
            message="Share with me a bizarre yet true historical fact about ancient Rome that most people wouldn't believe is real.",
            icon="/public/icons/colosseum.png",
        ),
        cl.Starter(
            label="Superconductors in simple terms",
            message="Imagine you're teaching a kindergartner about superconductors. Explain superconductors in simple terms",
            icon="/public/icons/cable.png",
        ),
        cl.Starter(
            label="AI vs Humanity: Who wins in a battle of wits?",
            message="AI vs Humanity: Who wins in a battle of wits? Answer in a poem—keep it short, snappy, and poetic!",
            icon="/public/icons/battel.png",
        ),
        cl.Starter(
            label="How does an AI play hide and seek?",
            message="How does an AI play hide and seek? Explain it in a fun and imaginative way.",
            icon="/public/icons/grinch.png",
        ),
        cl.Starter(
            label="Earliest experiences as an AI",
            message="Describe your earliest experiences as an AI, comparable to the first steps of a human baby learning and growing.",
            icon="/public/icons/feet.png",
        ),
    ]


@cl.on_mcp_connect
async def on_mcp_connect(connection: McpConnection, session: ClientSession):
    """Called when an MCP connection is established"""
    logger.info(f"Connected to MCP Server: {connection.name}")
    mcp_servers = cl.user_session.get("mcp_servers", {})
    if connection.name not in mcp_servers.keys():
        mcp_servers[connection.name] = connection.url
        cl.user_session.set("mcp_servers", mcp_servers)


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Called when an MCP connection is terminated"""
    logger.info(f"Disconnected from MCP Server: {name}")
    mcp_servers = cl.user_session.get("mcp_servers", {})
    if name in mcp_servers.keys():
        del mcp_servers[name]
        cl.user_session.set("mcp_servers", mcp_servers)


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """Called when a thread/session is resumed"""
    logger.info(f"Resuming thread: {thread.get('id')}")
    await cl.context.emitter.set_commands(COMMANDS)


@cl.on_chat_start
async def on_chat_start():
    """Called when a thread/session is started"""
    logger.info("Starting chat")
    await cl.context.emitter.set_commands(COMMANDS)


@cl.on_message
async def on_message(message: cl.Message):
    """Called when a message is received"""
    logger.info("Received message")

    agent = "chatter" if not message.command else message.command.lower()
    knowledge = get_knowledge_base(thread_id=message.thread_id)

    files = process_files(
        elements=[
            element
            for element in message.elements
            if element.mime in ["application/pdf", "text/plain"]
        ],
        thread_id=message.thread_id,
    )

    if files:
        await cl.Message(
            content="Loading file(s) attached to the Knowledge Base...",
        ).send()
        ui_msg = cl.Message(content="")
        await cl.make_async(knowledge.load)(upsert=True)
        ui_msg.content = "File(s) loaded successfully to the Knowledge Base."
        ui_msg.elements = files
        await ui_msg.update()
        logger.info("File(s) loaded successfully to the Knowledge Base.")

    images = process_images(
        elements=[
            element for element in message.elements if element.type == "image"
        ],
    )

    await run_agent(
        kind=agent,
        content=message.content,
        knowledge=knowledge,
        thread_id=message.thread_id,
        images=images,
    )
