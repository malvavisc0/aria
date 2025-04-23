import os
import shutil
from mimetypes import guess_type
from typing import List, Optional

import chainlit as cl
from agno.media import Image
from agno.models.message import Message
from chainlit.element import ElementBased
from loguru import logger

from assistant.agents.builder import build, setup_model
from assistant.agents.knowledge import get_knowledge_base


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
            images.append(Image(filepath=element.path))
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
    """
    Runs an agent with the provided kind, content, thread ID, and optional images.

    Parameters:
     kind (str): The kind of agent to run.
     content (str): The content to be processed by the agent.
     thread_id (str): The ID of the thread associated with the agent.
     images (Optional[List[Image]]): A list of images to be processed by the agent.

    The function performs the following steps:
    1. Initializes a message object.
    2. Checks if images are provided and sets the kind to "vision" if images are present.
    3. Sets up the language model based on the kind and whether images are present.
    4. Builds the agent with the specified kind, thread ID, language model, and debug mode.
    5. Loads the agent's knowledge if available.
    6. Creates a message object with the user's role, content, and images.
    7. Runs the agent asynchronously and streams the response.
    8. Sends the final message.
    """
    ui_msg = cl.Message(content="")

    has_images = False
    if images and len(images) > 0:
        kind = "vision"
        has_images = True

    user_message = Message(role="user", content=content, images=images)
    llm = setup_model(kind=kind, has_images=has_images)
    knowledge = get_knowledge_base(thread_id=thread_id)
    agent = await build(
        kind=kind,
        thread_id=thread_id,
        llm=llm,
        knowledge=knowledge,
        debug_mode=True,
        user_id=user_id,
    )

    response = await agent.arun(message=user_message, stream=True)
    async for chunk in response:
        if chunk.content:
            await ui_msg.stream_token(token=str(chunk.content))

    await ui_msg.send()
