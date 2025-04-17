import os
import shutil
from typing import AsyncIterator, List, Optional

import chainlit as cl
from agno.media import Image
from agno.models.message import Message
from agno.run.response import RunResponse

from assistant.agents import build, setup_model


@cl.step(type="tool")
async def process_elements(message: cl.Message, thread_id: str) -> List[Image]:
    """
    Processes elements from a message and returns a list of images.

    Parameters:
     message (cl.Message): The message containing elements to process.
     thread_id (str): The ID of the thread associated with the message.

    Returns:
     List[Image]: A list of Image objects representing the processed images.

    This function checks if the message contains elements. If not, it returns an empty list.
    For each element, it checks if the element has a valid path. If not, it skips to the next element.
    It creates the necessary directory structure if it doesn't exist and copies the file to the destination.
    If the element type is "image", it appends an Image object to the list of images to be returned.
    """
    if not message.elements:
        return []

    images = []
    for element in message.elements:
        if not element.path:
            continue
        os.makedirs(f"/opt/knowledge/{thread_id}/{element.type}", exist_ok=True)
        file_name = os.path.basename(element.path)
        destination = f"/opt/knowledge/{thread_id}/{element.type}/{file_name}"
        shutil.copyfile(element.path, destination)
        if element.type == "image":
            images.append(Image(filepath=element.path))
    return images


@cl.step(type="run")
async def run_agent(
    kind: str,
    content: str,
    thread_id: str,
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
    msg = cl.Message(content="")

    has_images = False
    if images and len(images) > 0:
        kind = "vision"
        has_images = True

    llm = setup_model(kind=kind, has_images=has_images)

    agent = build(kind=kind, thread_id=thread_id, llm=llm, debug_mode=True)
    if agent.knowledge:
        await cl.make_async(agent.knowledge.load)(recreate=True, upsert=True)

    message = Message(role="user", content=content, images=images)
    """
    aresponse: AsyncIterator[RunResponse] = await agent.arun(message=message, stream=True)
    async for chunk in aresponse:
        await msg.stream_token(token=str(chunk.content))
    """
    response = agent.run(message=message, stream=True)
    for chunk in response:
        await msg.stream_token(token=str(chunk.content))
    await msg.send()
