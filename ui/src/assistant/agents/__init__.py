from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Type, Union

from agno.agent.agent import Agent
from agno.knowledge.agent import AgentKnowledge
from agno.memory.agent import AgentMemory
from agno.memory.classifier import MemoryClassifier
from agno.memory.db.sqlite import SqliteMemoryDb
from agno.memory.manager import MemoryManager
from agno.memory.summarizer import MemorySummarizer
from agno.models.base import Model
from agno.storage.base import Storage
from agno.storage.sqlite import SqliteStorage
from agno.tools.function import Function
from agno.tools.thinking import ThinkingTools
from agno.tools.toolkit import Toolkit
from assistant.agents import descriptions, goals, instructions, roles, toolkits
from assistant.knowledge import get_knowledge_base
from assistant.models import CHATBOT_MODEL, TOOL_MODEL, VISION_MODEL, completion
from pydantic import BaseModel


def _get_agent(
    session_id: str,
    name: str,
    model: Model,
    description: Optional[str] = None,
    role: Optional[str] = None,
    goal: Optional[str] = None,
    instructions: Optional[List[str]] = None,
    storage: Optional[Storage] = None,
    tools: Optional[List[Union[Toolkit, Callable, Function, Dict]]] = None,
    reasoning: Optional[bool] = False,
    memory: Optional[AgentMemory] = None,
    knowledge: Optional[AgentKnowledge] = None,
    search_knowledge: Optional[bool] = False,
    debug_mode: Optional[bool] = False,
    response_model: Optional[Type[BaseModel]] = None,
    use_json_mode: Optional[bool] = False,
    markdown: Optional[bool] = False,
) -> Agent:
    return Agent(
        session_id=session_id,
        name=name,
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
        add_history_to_messages=memory is not None,
        num_history_responses=5,
        use_json_mode=use_json_mode,
        response_model=response_model,
        markdown=markdown,
        debug_mode=debug_mode,
        add_datetime_to_instructions=True,
    )


def _get_memory(thread_id: str, model: Model) -> AgentMemory:
    db_file = (Path("/opt/memory") / f"{thread_id}.db").as_posix()
    classifier = MemoryClassifier(model=model)
    manager = MemoryManager(model=model)
    summarizer = MemorySummarizer(model=model)

    memory = AgentMemory(
        db=SqliteMemoryDb(db_file=db_file),
        create_user_memories=True,
        create_session_summary=True,
        update_user_memories_after_run=True,
        classifier=classifier,
        manager=manager,
        summarizer=summarizer,
    )
    return memory


def _get_storage(thread_id: str) -> SqliteStorage:
    db_file = (Path("/opt/storage") / f"{thread_id}.db").absolute().as_posix()
    return SqliteStorage(
        table_name="storage",
        db_file=db_file,
    )


def build(
    llm: Model,
    kind: Literal[
        "chatter",
        "vision",
        "scientist",
        "finance",
        "youtube",
        "researcher",
        "medic",
        "crawler",
        "wikipedia",
        "reasoning",
    ],
    thread_id: Optional[str] = None,
    debug_mode: Optional[bool] = False,
    search_knowledge: Optional[bool] = False,
) -> Agent:
    agent_memory = None
    agent_storage = None
    agent_knowledge = None
    search_knowledge = False
    if thread_id:
        agent_memory = _get_memory(thread_id=thread_id, model=llm)
        agent_storage = _get_storage(thread_id=thread_id)
        agent_knowledge = get_knowledge_base(thread_id=thread_id)

    agent_name = ""
    agent_role = None
    agent_goal = None
    agent_description = None
    agent_instructions = None
    agent_tools = None
    agent_reasoning = False

    agent_response_model = None
    agent_json_mode = False

    agent_output_markdown = False

    if kind == "chatter":
        agent_name = "Aria"
        agent_goal = goals.CHATTER
        agent_role = roles.CHATTER
        agent_description = descriptions.CHATTER
        agent_instructions = instructions.CHATTER
        if agent_knowledge:
            search_knowledge = True
    elif kind == "reasoning":
        agent_name = "Einstein"
        agent_goal = goals.EINSTEIN
        agent_role = roles.EINSTEIN
        agent_description = descriptions.EINSTEIN
        agent_instructions = instructions.EINSTEIN
        agent_tools = [ThinkingTools()]
        if agent_knowledge:
            search_knowledge = True
    elif kind == "vision":
        agent_name = "Vision"
        agent_goal = goals.VISION
        agent_role = roles.VISION
        agent_description = descriptions.VISION
        agent_instructions = instructions.VISION
        agent_knowledge = None
        search_knowledge = False
        agent_memory = None
        agent_storage = None
    elif kind == "scientist":
        agent_name = "Scientist"
        agent_goal = goals.SCIENTIST
        agent_role = roles.SCIENTIST
        agent_description = descriptions.SCIENTIST
        agent_instructions = instructions.SCIENTIST
        agent_tools = [toolkits.arxiv]
    elif kind == "medic":
        agent_name = "Dr. Smith"
        agent_goal = goals.MEDIC
        agent_role = roles.MEDIC
        agent_description = descriptions.MEDIC
        agent_instructions = instructions.MEDIC
        agent_tools = [toolkits.pubmed]
        agent_reasoning = True
    elif kind == "wikipedia":
        agent_name = "Jimmy"
        agent_goal = goals.WIKIPEDIA
        agent_role = roles.WIKIPEDIA
        agent_description = descriptions.WIKIPEDIA
        agent_instructions = instructions.WIKIPEDIA
        agent_tools = [toolkits.wikipedia]
    elif kind == "youtube":
        agent_name = "Steve"
        agent_goal = goals.YOUTUBE
        agent_role = roles.YOUTUBE
        agent_description = descriptions.YOUTUBE
        agent_instructions = instructions.YOUTUBE
        agent_tools = [toolkits.youtube]
        agent_reasoning = True
    elif kind == "finance":
        agent_name = "Carl"
        agent_goal = goals.FINANCE
        agent_role = roles.FINANCE
        agent_description = descriptions.FINANCE
        agent_instructions = instructions.FINANCE + instructions.EINSTEIN
        agent_tools = [toolkits.finance]
    elif kind == "crawler":
        agent_name = "Spider"
        agent_goal = goals.CRAWLER
        agent_role = roles.CRAWLER
        agent_description = descriptions.CRAWLER
        agent_instructions = instructions.CRAWLER + instructions.EINSTEIN
        agent_tools = [toolkits.website]
    elif kind == "researcher":
        agent_name = "Barton"
        agent_goal = goals.RESEARCHER
        agent_role = roles.RESEARCHER
        agent_description = descriptions.RESEARCHER
        agent_instructions = (
            instructions.RESEARCHER
            + instructions.WIKIPEDIA
            + instructions.MEDIC
            + instructions.FINANCE
        )
        agent_tools = [
            toolkits.searxng,
            toolkits.finance,
            toolkits.pubmed,
            toolkits.wikipedia,
        ]
        agent_output_markdown = True
    else:
        ValueError(f"Unknown agent kind: {kind}")

    return _get_agent(
        session_id=thread_id,
        name=agent_name,
        role=agent_role,
        goal=agent_goal,
        description=agent_description,
        instructions=agent_instructions,
        tools=agent_tools,
        reasoning=agent_reasoning,
        model=llm,
        storage=agent_storage,
        knowledge=agent_knowledge,
        search_knowledge=search_knowledge,
        debug_mode=debug_mode,
        memory=agent_memory,
        response_model=agent_response_model,
        use_json_mode=agent_json_mode,
        markdown=agent_output_markdown,
    )


def setup_model(kind: str, has_images: bool = False):
    model = TOOL_MODEL
    temperature = 0.5
    if kind == "vision" or has_images:
        model = VISION_MODEL
        kind = "vision"
        temperature = 0.5
    elif kind in ["chatter", "reasoning", "researcher"]:
        model = CHATBOT_MODEL
        temperature = 0.65
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
