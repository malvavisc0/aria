import os
import shutil
from typing import List, Optional

import chainlit as cl
from agno.knowledge.agent import AgentKnowledge
from agno.media import Image
from agno.models.message import Message
from agno.tools.mcp import MultiMCPTools
from chainlit.element import ElementBased
from loguru import logger
from mimetypes import guess_type

from assistant.agents.builder import build as build_agent
from assistant.agents.builder import setup_model
from assistant.agents.settings.configs import build as build_config


@cl.step(type="tool")
def process_images(elements: List[ElementBased]) -> List[Image]:
    """
    Processes a list of elements to extract and return their corresponding images.

    Parameters:
     elements (List[ElementBased]): A list of ElementBased objects, each representing an element with a path to an image file.

    Returns:
     List[Image]: A list of Image objects containing the images extracted from the elements.

    Raises:
     FileNotFoundError: If any of the image files specified in the elements do not exist.
     IOError: If there is an error reading any of the image files.
    """
    if len(elements) == 0:
        return []
    images = []
    for element in elements:
        with open(element.path, mode="rb") as image:
            mime_type, encoding = guess_type(element.path)
            image_format = mime_type.replace("image/","")
            images.append(Image(format=image_format, content=image.read()))
            logger.info(f"Added {element.path} to images")
    return images


@cl.step(type="tool")
def process_files(
    elements: List[ElementBased],
    thread_id: str,
) -> List[cl.Pdf | cl.Text]:
    """
    Process a list of elements by copying their files to a designated directory and converting them to appropriate objects.

    Parameters:
     elements (List[ElementBased]): A list of elements to be processed. Each element should have 'path' and 'mime' attributes.
     thread_id (str): A unique identifier for the thread, used to create a directory for the processed files.

    Returns:
     List[cl.Pdf | cl.Text]: A list of processed files as Pdf or Text objects, depending on their MIME type.
    """
    if len(elements) == 0:
        return []
    files = []
    for element in elements:
        file_name = os.path.basename(element.path)
        destination = f"/opt/knowledge/{thread_id}/{file_name}"
        shutil.copyfile(element.path, destination)
        logger.info(f"Copied {element.path} to {destination}")
        if element.mime == "application/pdf":
            files.append(cl.Pdf(name=element.name, path=destination))
        elif element.mime == "text/plain":
            files.append(cl.Text(name=element.name, path=destination))
    return files


@cl.step(type="llm")
async def run_agent(
    kind: str,
    content: str,
    knowledge: AgentKnowledge,
    thread_id: str,
    images: Optional[List[Image]] = [],
):
    """
    Runs an agent based on the provided parameters.

    Parameters:
     kind (str): The type of agent to run.
     content (str): The content to be processed by the agent.
     knowledge (AgentKnowledge): The knowledge base associated with the agent.
     thread_id (str): The ID of the thread associated with the agent.
     user_id (str): The ID of the user associated with the agent.
     images (Optional[List[Image]]): A list of images to be processed by the agent, if applicable.
    """
    ui_msg = cl.Message(content="")
    has_images = bool(images)
    kind = "vision" if has_images else kind

    user_message = Message(role="user", content=content, images=images)
    llm = setup_model(kind=kind, has_images=has_images)
    config = build_config(kind=kind)

    agent = await build_agent(
        llm=llm,
        config=config,
        thread_id=thread_id,
        knowledge=knowledge,
    )

    mcp_servers_urls = []
    mcp_servers = cl.user_session.get("mcp_servers", {})
    for server_name, server_url in mcp_servers.items():
        server_url = mcp_servers.get(server_name)
        if server_url and server_url not in mcp_servers_urls:
            mcp_servers_urls.append(server_url)

    if len(mcp_servers_urls) == 0:
        response = await agent.arun(message=user_message)
        async for chunk in response:
            await ui_msg.stream_token(token=str(chunk.content))
    elif len(mcp_servers_urls) >= 1:
        logger.info(f"Multiple MCP servers found: {mcp_servers_urls}")
        async with MultiMCPTools(urls=mcp_servers_urls) as mcp_tools:
            agent.tools += [mcp_tools]
            response = await agent.arun(message=user_message)
            async for chunk in response:
                await ui_msg.stream_token(token=str(chunk.content))

    await ui_msg.send()
