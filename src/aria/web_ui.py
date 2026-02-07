import chainlit as cl
from chainlit.types import ThreadDict
from llama_index.core.agent.workflow import AgentStream, ToolCall
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory import Memory
from loguru import logger
from sqlalchemy import create_engine

from aria.agents import get_prompt_enhancer_agent
from aria.agents.prompt_enhancer import PromptEnhancementResult
from aria.config import (
    CHAT_HISTORY_DB_URL,
    CHAT_OPENAI_API,
    DEBUG_LOGS_PATH,
    EMBEDDINGS_API_URL,
    LOCAL_STORAGE_PATH,
    MAX_ITERATIONS,
    SQLITE_CONN_INFO,
    TOKEN_LIMIT,
    VECTOR_DB,
)
from aria.db.layer import SQLiteSQLAlchemyDataLayer
from aria.db.local_storage_client import LocalStorageClient
from aria.db.models import Base
from aria.llm import (
    get_agent_workflow,
    get_chat_llm,
    get_default_memory,
    get_embeddings_model,
)
from aria.ui import maybe_remove_step, send_tool_step

log_path = DEBUG_LOGS_PATH
logger.add(
    log_path,
    rotation="10 MB",
    level="DEBUG",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
)

llm = get_chat_llm(api_base=CHAT_OPENAI_API)
embeddings = get_embeddings_model(api_base=EMBEDDINGS_API_URL)


agents_workflow = get_agent_workflow(llm)
prompt_enhancer = get_prompt_enhancer_agent(llm=llm)


@cl.data_layer
def get_data_layer():
    engine = create_engine(CHAT_HISTORY_DB_URL)

    # Create tables (idempotent - won't drop existing tables)
    Base.metadata.create_all(engine)

    # Use local storage for elements (images, files, etc.)
    storage_client = LocalStorageClient(storage_path=LOCAL_STORAGE_PATH)

    return SQLiteSQLAlchemyDataLayer(
        conninfo=SQLITE_CONN_INFO,
        storage_provider=storage_client,
        show_logger=True,  # Enable to debug data layer issues
    )


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """Authenticate user against database using password field."""
    import json

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from aria.db.auth import verify_password
    from aria.db.models import User

    # Create database session (sync since this is a sync callback)
    engine = create_engine(CHAT_HISTORY_DB_URL)

    try:
        with Session(engine) as session:
            # Find user by identifier (username)
            user = session.execute(
                select(User).where(User.identifier == username)
            ).scalar_one_or_none()

            if not user:
                logger.debug(f"User not found: {username}")
                return None

            # Verify password using new password field
            user_password = str(user.password)
            if user_password and verify_password(password, user_password):
                metadata = json.loads(str(user.metadata_))
                logger.debug(f"User authenticated: {username}")
                return cl.User(
                    identifier=str(user.identifier),
                    metadata=metadata,
                )

            logger.debug(f"Invalid password for user: {username}")
            return None

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


@cl.on_chat_start
async def on_chat_start():
    """
    Chainlit chat-start handler.

    Initializes a new chat session.
    Memory will be initialized on first message since thread_id is not available yet.
    """
    logger.debug("Starting new chat session")
    await cl.context.emitter.set_commands(
        [
            {
                "id": "Enhance",
                "icon": "wand-sparkles",
                "description": "Enhance Prompt",
                "button": None,
                "persistent": True,
            }
        ]
    )


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Chainlit chat-resume handler.

    Called when a user resumes a previous conversation thread.
    This restores the conversation history to the LLM memory.

    Args:
        thread: The thread data containing steps (messages) and metadata
    """
    thread_id = thread.get("id")
    thread_name = thread.get("name")
    logger.debug(f"Resuming thread: {thread_id} - {thread_name}")

    steps = thread.get("steps", [])
    logger.debug(f"Thread has {len(steps)} total steps")

    # Filter for root-level messages only (parentId == None)
    # Chainlit automatically displays the messages in the UI from the database
    root_messages = [m for m in steps if m.get("parentId") is None]
    logger.debug(f"Thread has {len(root_messages)} root-level messages")

    memory = get_default_memory(
        vector_db=VECTOR_DB,
        thread_id=thread_id,
        embed_model=embeddings,
        token_limit=TOKEN_LIMIT,
    )

    # Restore the conversation history by replaying messages into memory
    steps_restored = 0
    for step in root_messages:
        content = step.get("output", "")
        message_type = step.get("type")
        if not content or message_type not in [
            "user_message",
            "assistant_message",
        ]:
            continue

        role = (
            MessageRole.USER
            if message_type == "user_message"
            else MessageRole.ASSISTANT
        )

        message = ChatMessage(role=role, content=content)
        await memory.aput(message)
        steps_restored += 1

    # Store memory in user session for reuse
    cl.user_session.set("memory", memory)

    logger.info(f"Restored {steps_restored} steps for thread {thread_id}")


@cl.on_message
async def on_message(message: cl.Message):
    """
    Chainlit message handler.

    Args:
        message (cl.Message): The inbound user message.
    """
    msg = cl.Message(content="")

    prompt = message.content
    if msg.command == "Enhance":
        # Let's try to use the prompt enhancer
        response = await prompt_enhancer.run(user_msg=message.content)
        if response.structured_response:
            ouput: PromptEnhancementResult = response.structured_response
            prompt = ouput.enhanced

    # Try to get existing memory from session
    memory: Memory | None = cl.user_session.get("memory")

    # If not found (new chat or session issue), create new memory instance
    if memory is None:
        memory = get_default_memory(
            vector_db=VECTOR_DB,
            thread_id=message.thread_id,
            embed_model=embeddings,
            token_limit=TOKEN_LIMIT,
        )
        # Store in session for future messages
        cl.user_session.set("memory", memory)
        logger.debug(f"Created new Memory for thread {message.thread_id}")

    handler = agents_workflow.run(
        user_msg=prompt, memory=memory, max_iterations=MAX_ITERATIONS
    )

    step: cl.Step | None = None
    # Stream events as they arrive
    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            step = await send_tool_step(event)
        elif isinstance(event, AgentStream):
            step = await maybe_remove_step(step)
            await msg.stream_token(event.delta)

    # Send the final message - this persists it to the database for thread resumption
    await msg.send()

    # Finalize the run
    _ = await handler
