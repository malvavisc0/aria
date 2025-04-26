import os
import shutil
from mimetypes import guess_type
from typing import List, Optional

import chainlit as cl
from agno.media import Image
from agno.models.message import Message
from agno.tools.mcp import MultiMCPTools
from chainlit.element import ElementBased
from loguru import logger

from assistant.agents.builder import build, setup_model
from assistant.agents.knowledge import get_knowledge_base
from assistant.agents.settings.configs import build as build_config


@cl.step(type="tool")
async def process_elements(
    elements: List[ElementBased], thread_id: str
) -> List[Image]:
    """
    Process a list of elements and handle them based on their type.

    Parameters:
     elements (List[ElementBased]): A list of elements to process.
     thread_id (str): The ID of the thread associated with the processing.

    Returns:
     List[Image]: A list of images extracted from the elements.
    """
    knowledge = get_knowledge_base(thread_id=thread_id)
    images = []
    files = []
    for element in elements:
        file_name = os.path.basename(element.path)
        element_type, encoding = guess_type(element.path)
        if element_type in ["image/jpeg", "image/png"]:
            with open(element.path, mode="rb") as image:
                format = element_type.split("/")[1]
                images.append(Image(format=format, content=image.read()))
            logger.info(f"Added {element.path} to images")
        elif element_type in ["application/pdf", "text/plain"]:
            destination = f"/opt/knowledge/{thread_id}/{file_name}"
            shutil.copyfile(element.path, destination)
            logger.info(f"Copied {element.path} to {destination}")
            if element_type == "application/pdf":
                files.append(cl.Pdf(name=element.name, path=destination))
            elif element_type == "text/plain":
                files.append(cl.Text(name=element.name, path=destination))

    if len(files) > 0:
        await cl.Message(
            content="Loading file(s) attached to the Knowledge Base...",
            elements=files,
        ).send()
        logger.info("Loading file(s) attached to the Knowledge Base")
        # knowledge.aload(recreate=True, upsert=True)
        await cl.make_async(knowledge.load)(upsert=True)
        await cl.Message(
            content="File(s) loaded to the Knowledge Base:", elements=files
        ).send()

    return images


@cl.step(type="llm")
async def run_agent(
    kind: str,
    content: str,
    thread_id: str,
    user_id: str,
    images: Optional[List[Image]] = [],
):
    """ """
    ui_msg = cl.Message(content="")

    has_images = False
    if images and len(images) > 0:
        kind = "vision"
        has_images = True

    user_message = Message(role="user", content=content, images=images)
    llm = setup_model(kind=kind, has_images=has_images)
    knowledge = get_knowledge_base(thread_id=thread_id)
    config = build_config(kind=kind)
    agent = await build(
        llm=llm,
        config=config,
        user_id=user_id,
        thread_id=thread_id,
        knowledge=knowledge,
        debug_mode=True,
    )

    mcp_servers_urls = []
    mcp_servers = cl.user_session.get("mcp_servers", {})
    for server_name, server_url in mcp_servers.items():
        server_url = mcp_servers.get(server_name)
        mcp_servers_urls.append(server_url)
        
    if len(mcp_servers_urls) == 0:
        response = await agent.arun(message=user_message)
        async for chunk in response:
            if not chunk.content:
                continue
            await ui_msg.stream_token(token=str(chunk.content))
    elif len(mcp_servers_urls) >= 1:
        logger.info(f"Multiple MCP servers found: {mcp_servers_urls}")
        async with MultiMCPTools(urls=mcp_servers_urls) as mcp_tools:
            agent.tools += [mcp_tools]
            response = await agent.arun(message=user_message)
            async for chunk in response:
                if not chunk.content:
                    continue
                await ui_msg.stream_token(token=str(chunk.content))
    
    await ui_msg.send()
