from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field

from assistant.agents import descriptions, goals, instructions, roles, toolkits, tools


class AgentConfig(BaseModel):
    """
    AgentConfig is a class that contains the configuration for an agent.
    """

    name: Annotated[str, Field(strict=True, default="Aria")]
    role: Annotated[Optional[str], Field(strict=True, default=None)]
    goal: Annotated[Optional[str], Field(strict=True, default=None)]
    description: Annotated[Optional[str], Field(strict=True, default=None)]
    instructions: Annotated[List[str], Field(strict=True, default=[])]
    tools: Annotated[List, Field(strict=True, default=[])]
    reasoning: Annotated[bool, Field(strict=True, default=True)]
    markdown: Annotated[bool, Field(strict=True, default=False)]


class ChatterAgentConfig(AgentConfig):
    role = roles.CHATTER
    goal = goals.CHATTER
    description = descriptions.CHATTER
    instructions = instructions.CHATTER
    

agents = {
        "chatter": ChatterAgentConfig(reasoning=False),
       
        
        
}

def build(
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
) -> AgentConfig:
    """
    Build an agent config.
    Parameters:
     kind: The kind of agent to build.
    """

    return agentts.get(kind)
    
    if kind == "chatter":
        return AgentConfig(
            role=roles.CHATTER,
            goal=goals.CHATTER,
            description=descriptions.CHATTER,
            instructions=instructions.CHATTER,
            reasoning=False,
        )
    elif kind == "scientist":
        return AgentConfig(
            role=roles.SCIENTIST,
            goal=goals.SCIENTIST,
            description=descriptions.SCIENTIST,
            instructions=instructions.SCIENTIST,
            tools=[toolkits.arxiv],
        )
    elif kind == "reasoning":
        return AgentConfig(
            role=roles.REASONING,
            goal=goals.REASONING,
            description=descriptions.REASONING,
            instructions=instructions.REASONING,
            tools=[toolkits.reasoning],
        )
    elif kind == "vision":
        return AgentConfig(
            role=roles.VISION,
            goal=goals.VISION,
            description=descriptions.VISION,
            instructions=instructions.VISION,
            reasoning=False,
        )
    elif kind == "medic":
        return AgentConfig(
            role=roles.MEDIC,
            goal=goals.MEDIC,
            description=descriptions.MEDIC,
            instructions=instructions.MEDIC,
            tools=[toolkits.pubmed],
        )
    elif kind == "wikipedia":
        return AgentConfig(
            role=roles.WIKIPEDIA,
            goal=goals.WIKIPEDIA,
            description=descriptions.WIKIPEDIA,
            instructions=instructions.WIKIPEDIA,
            tools=[toolkits.wikipedia],
        )
    elif kind == "youtube":
        return AgentConfig(
            role=roles.YOUTUBE,
            goal=goals.YOUTUBE,
            description=descriptions.YOUTUBE,
            instructions=instructions.YOUTUBE,
            tools=[toolkits.youtube],
        )
    elif kind == "finance":
        return AgentConfig(
            role=roles.FINANCE,
            goal=goals.FINANCE,
            description=descriptions.FINANCE,
            instructions=instructions.FINANCE,
            tools=[toolkits.finance],
        )
    elif kind == "crawler":
        return AgentConfig(
            role=roles.CRAWLER,
            goal=goals.CRAWLER,
            description=descriptions.CRAWLER,
            instructions=instructions.CRAWLER,
            tools=[toolkits.crawler],
        )
    elif kind == "researcher":
        return AgentConfig(
            role=roles.RESEARCHER,
            goal=goals.RESEARCHER,
            description=descriptions.RESEARCHER,
            instructions=instructions.RESEARCHER,
            tools=[toolkits.searxng, toolkits.finance, toolkits.wikipedia],
        )
    raise ValueError(f"Unknown agent kind: {kind}")
