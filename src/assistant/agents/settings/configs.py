"""
Improved agent configurations following the AI Agent Design Guidelines.
This file combines the improved descriptions, goals, roles, and instructions
into complete agent configurations.
"""

from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field

from assistant.agents import toolkits
from assistant.agents.settings import descriptions, goals, instructions, roles


class AgentConfig(BaseModel):
    """
    AgentConfig is a class that contains the improved configuration for an agent.
    """

    role: Annotated[Optional[str], Field(strict=True, default=None)] = None
    goal: Annotated[Optional[str], Field(strict=True, default=None)] = None
    description: Annotated[Optional[str], Field(strict=True, default=None)] = (
        None
    )
    instructions: Annotated[List[str], Field(strict=True, default=[])] = []
    tools: Annotated[List, Field(strict=True, default=[])] = [
        toolkits.thinking
    ]
    reasoning: Annotated[bool, Field(strict=True, default=False)] = True
    markdown: Annotated[bool, Field(strict=True, default=False)] = True


class ChatterConfig(AgentConfig):
    """
    ChatterConfig is a class that contains the improved configuration for a chatter agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.CHATTER
        self.goal = goals.CHATTER
        self.description = descriptions.CHATTER
        self.instructions = instructions.CHATTER
        self.reasoning = True


class ScientistConfig(AgentConfig):
    """
    ScientistConfig is a class that contains the improved configuration for a scientist agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.SCIENTIST
        self.goal = goals.SCIENTIST
        self.description = descriptions.SCIENTIST
        self.instructions = instructions.SCIENTIST
        self.tools += [toolkits.arxiv]
        self.reasoning = True


class ReasoningConfig(AgentConfig):
    """
    ReasoningConfig is a class that contains the improved configuration for a reasoning agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.description = descriptions.REASONING
        self.goal = goals.REASONING
        self.role = roles.REASONING
        self.instructions = instructions.REASONING
        self.reasoning = True


class VisionConfig(AgentConfig):
    """
    VisionConfig is a class that contains the improved configuration for a vision agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.VISION
        self.goal = goals.VISION
        self.description = descriptions.VISION
        self.instructions = instructions.VISION
        self.reasoning = True


class MedicConfig(AgentConfig):
    """
    MedicConfig is a class that contains the improved configuration for a medic agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.MEDIC
        self.goal = goals.MEDIC
        self.description = descriptions.MEDIC
        self.instructions = instructions.MEDIC
        self.tools += [toolkits.pubmed]
        self.reasoning = True


class WikipediaConfig(AgentConfig):
    """
    WikipediaConfig is a class that contains the improved configuration for a wikipedia agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.WIKIPEDIA
        self.goal = goals.WIKIPEDIA
        self.description = descriptions.WIKIPEDIA
        self.instructions = instructions.WIKIPEDIA
        self.tools += [toolkits.wikipedia]
        self.reasoning = True


class YoutubeConfig(AgentConfig):
    """
    YoutubeConfig is a class that contains the improved configuration for a youtube agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.YOUTUBE
        self.goal = goals.YOUTUBE
        self.description = descriptions.YOUTUBE
        self.instructions = instructions.YOUTUBE
        self.tools += [toolkits.youtube]
        self.reasoning = True


class FinanceConfig(AgentConfig):
    """
    FinanceConfig is a class that contains the improved configuration for a finance agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.FINANCE
        self.goal = goals.FINANCE
        self.description = descriptions.FINANCE
        self.instructions = instructions.FINANCE
        self.tools += [toolkits.finance]
        self.reasoning = True


class ResearcherConfig(AgentConfig):
    """
    ResearcherConfig is a class that contains the improved configuration for a researcher agent.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.role = roles.RESEARCHER
        self.goal = goals.RESEARCHER
        self.description = descriptions.RESEARCHER
        self.instructions = instructions.RESEARCHER
        self.reasoning = True
        self.tools += (
            [toolkits.searxng] + [toolkits.finance] + [toolkits.wikipedia]
        )


def build(
    kind: Literal[
        "chatter",
        "vision",
        "scientist",
        "finance",
        "youtube",
        "researcher",
        "medic",
        "wikipedia",
        "reasoning",
    ],
) -> AgentConfig:
    """
    Build an improved agent configuration based on the specified kind.
    """
    match kind:
        case "chatter":
            return ChatterConfig()
        case "scientist":
            return ScientistConfig()
        case "reasoning":
            return ReasoningConfig()
        case "vision":
            return VisionConfig()
        case "medic":
            return MedicConfig()
        case "wikipedia":
            return WikipediaConfig()
        case "youtube":
            return YoutubeConfig()
        case "finance":
            return FinanceConfig()
        case "researcher":
            return ResearcherConfig()
        case _:
            raise ValueError(f"Unknown agent type: {kind}")
