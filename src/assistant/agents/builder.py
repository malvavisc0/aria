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

from assistant.agents.settings.configs import build as build_config
from assistant.models import (
    CHATBOT_MODEL,
    TOOL_MODEL,
    VISION_MODEL,
    completion,
)

REDIS_USERNAME = environ.get("REDIS_USERNAME", "default")
REDIS_PASSWORD = environ.get("REDIS_PASSWORD", "12345678")
REDIS_HOST = environ.get("REDIS_HOST", "redis")
REDIS_PORT = environ.get("REDIS_PORT", 6379)
REDIS_DB = environ.get("REDIS_DB", 0)


def _get_agent(
    session_id: str,
    model: Model,
    user_id: Optional[str] = None,
    description: Optional[str] = None,
    role: Optional[str] = None,
    goal: Optional[str] = None,
    instructions: Optional[List[str]] = None,
    storage: Optional[Storage] = None,
    tools: Optional[List[Union[Toolkit, Callable, Function, Dict]]] = None,
    reasoning: Optional[bool] = False,
    memory: Optional[Memory] = None,
    knowledge: Optional[AgentKnowledge] = None,
    search_knowledge: Optional[bool] = False,
    debug_mode: Optional[bool] = False,
    markdown: Optional[bool] = False,
) -> Agent:
    return Agent(
        session_id=session_id,
        model=model,
        user_id=user_id,
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
        enable_agentic_memory=True if memory else False,
        enable_user_memories=True if memory else False,
        enable_session_summaries=True if memory else False,
        markdown=markdown,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def _get_memory(thread_id: str, model: Model) -> Memory:
    memory = Memory(
        db=RedisMemoryDb(
            prefix=thread_id,
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
        ),
        memory_manager=MemoryManager(model=model),
        summarizer=SessionSummarizer(model=model),
    )
    return memory


def _get_storage(thread_id: str) -> RedisStorage:
    return RedisStorage(
        prefix=thread_id,
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
    )


async def build(
    llm: Model,
    kind: Optional[str] = "chatter",
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    debug_mode: Optional[bool] = False,
    knowledge: Optional[AgentKnowledge] = None,
) -> Agent:
    memory = None
    storage = None
    knowledge = None
    if thread_id:
        memory = _get_memory(thread_id=thread_id, model=llm)
        storage = _get_storage(thread_id=thread_id)

    config = build_config(kind=kind)

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
        user_id=user_id,
    )


def setup_model(kind: str, has_images: bool = False):
    model = TOOL_MODEL
    temperature = 0.25
    if kind == "vision" or has_images:
        model = VISION_MODEL
        kind = "vision"
        temperature = 0.35
    elif kind in ["chatter", "reasoning"]:
        model = CHATBOT_MODEL
        temperature = 0.7
    llm = completion(model=model, temperature=temperature)
    return llm


def build_group(
    types: List[str], thread_id: str, has_images: bool = False
) -> List[Agent]:
    agents = []
    for kind in types:
        llm = setup_model(kind=kind, has_images=has_images)
        agent = build(llm=llm, kind=kind, thread_id=thread_id)
        agents.append(agent)
    return agents
