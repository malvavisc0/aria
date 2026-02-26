"""
IMDB Expert Agent

This module defines a specialized agent for movie and TV series information
retrieval, providing tools for searching IMDb, getting details about titles
and people, and exploring TV series episodes.
"""

import importlib
from pathlib import Path
from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.tools.documentation import tool_help

IMDB_TOOLS = "aria.tools.imdb"


class IMDbExpertAgent(FunctionAgent):
    """
    A specialized agent for movie and TV series information retrieval.

    This agent extends FunctionAgent to provide IMDb search and lookup
    capabilities including title search, movie details, person information,
    filmography, TV episodes, reviews, and trivia.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the IMDB Expert Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        instructions_dir = Path(__file__).parent / "instructions"
        core_path = instructions_dir / "core_rules.md"
        instructions_path = instructions_dir / "imdb_expert.md"

        core = ""
        with open(core_path, mode="r", encoding="utf-8") as file:
            core = file.read()

        instructions = ""
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            instructions = file.read()

        return f"{core}\n\n{instructions}\n\n# Additional Notes\n{extras}"


def get_agent(
    llm: LLM,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] | None = None,
) -> IMDbExpertAgent:
    """
    Create an IMDB expert agent with the given LLM.

    Args:
        llm (LLM): The language model to use for the agent
        extras (str, optional): Additional system prompt instructions

    Returns:
        IMDbExpertAgent: A configured IMDB expert agent instance

    The agent is initialized with tools for:
    - Searching IMDb titles
    - Getting movie/series details
    - Getting person details and filmography
    - Getting TV series episodes
    - Getting reviews and trivia
    """
    imdb_tools = importlib.import_module(IMDB_TOOLS)

    tools_selection = {
        IMDB_TOOLS: [
            "search_imdb_titles",
            "get_movie_details",
            "get_person_details",
            "get_person_filmography",
            "get_all_series_episodes",
            "get_movie_reviews",
            "get_movie_trivia",
        ],
    }

    tools = [
        FunctionTool.from_defaults(fn=getattr(imdb_tools, name))
        for name in tools_selection[IMDB_TOOLS]
    ]

    # On-demand tool documentation.
    tools.append(FunctionTool.from_defaults(fn=tool_help))

    tools = filter_tools_for_llamacpp(tools, agent_name="IMDb Expert")

    agent = IMDbExpertAgent(
        name="Spielberg",
        description=(
            "Specialized in movie and TV series information, actor/director "
            "details, and entertainment research using IMDb data."
        ),
        tools=tools,
        llm=llm,
        system_prompt=IMDbExpertAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
