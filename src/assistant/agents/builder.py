from os import environ
from typing import Callable, Dict, List, Optional, Union

from agno.agent.agent import Agent
from agno.knowledge.agent import AgentKnowledge
from agno.memory.v2.db.redis import RedisMemoryDb
from agno.memory.v2.manager import MemoryManager
from agno.memory.v2.memory import Memory
from agno.memory.v2.summarizer import SessionSummarizer
from agno.models.base import Model
from agno.storage.base import Storage
from agno.storage.redis import RedisStorage
from agno.tools.function import Function
from agno.tools.toolkit import Toolkit

from assistant.agents.models import (
    CHATBOT_MODEL,
    TOOL_MODEL,
    VISION_MODEL,
    completion,
)
from assistant.agents.settings.configs import AgentConfig

REDIS_USERNAME = environ.get("REDIS_USERNAME", "default")
REDIS_PASSWORD = environ.get("REDIS_PASSWORD", "12345678")
REDIS_HOST = environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(environ.get("REDIS_PORT", 6379))
REDIS_DB = int(environ.get("REDIS_DB", 0))


def _get_agent(
    session_id: str,
    model: Model,
    description: Optional[str] = None,
    role: Optional[str] = None,
    goal: Optional[str] = None,
    instructions: Optional[List[str]] = None,
    storage: Optional[Storage] = None,
    tools: Optional[List[Union[Toolkit, Callable, Function, Dict]]] = None,
    memory: Optional[Memory] = None,
    knowledge: Optional[AgentKnowledge] = None,
    search_knowledge: bool = False,
    debug_mode: bool = False,
    markdown: bool = False,
    reasoning: bool = False,
) -> Agent:
    return Agent(
        session_id=session_id,
        model=model,
        tools=tools,
        description=description,
        instructions=instructions,
        role=role,
        goal=goal,
        storage=storage,
        stream=True,
        show_tool_calls=False,
        reasoning=reasoning,
        knowledge=knowledge,
        search_knowledge=search_knowledge,
        memory=memory,
        add_history_to_messages=True if memory else False,
        read_chat_history=True if memory else False,
        enable_agentic_memory=True if memory else False,
        enable_user_memories=True if memory else False,
        enable_session_summaries=True if memory else False,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def _get_memory(thread_id: str, model_id: str = TOOL_MODEL) -> Memory:
    model = completion(model=model_id, temperature=0.0)
    memory = Memory(
        db=RedisMemoryDb(
            prefix=thread_id,
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
        ),
        memory_manager=MemoryManager(
            model=model,
        ),
        summarizer=SessionSummarizer(
            model=model,
        ),
    )
    return memory


def _get_storage() -> RedisStorage:
    return RedisStorage(
        prefix="agno_storage_",
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
    )


async def build(
    llm: Model,
    config: AgentConfig,
    thread_id: str,
    knowledge: Optional[AgentKnowledge] = None,
    debug_mode: bool = False,
) -> Agent:
    memory = None
    storage = None
    knowledge = None

    memory = _get_memory(thread_id=thread_id)
    storage = _get_storage()

    return _get_agent(
        session_id=thread_id,
        model=llm,
        role=config.role,
        goal=config.goal,
        description=config.description,
        instructions=config.instructions,
        tools=config.tools,
        reasoning=config.reasoning,
        memory=memory,
        storage=storage,
        knowledge=knowledge,
        search_knowledge=True if knowledge else False,
        markdown=config.markdown,
        debug_mode=debug_mode,
    )


def setup_model(kind: str, has_images: bool = False):
    model = TOOL_MODEL
    temperature = 0.3
    if kind == "vision" or has_images:
        model = VISION_MODEL
        kind = "vision"
        temperature = 0.5
    elif kind in ["chatter", "reasoning"]:
        model = CHATBOT_MODEL
        temperature = 0.5
    llm = completion(model=model, temperature=temperature)
    return llm
