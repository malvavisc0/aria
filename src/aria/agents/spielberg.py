"""
IMDB Expert Agent

This module defines a specialized agent for movie and TV series information
retrieval, providing tools for searching IMDb, getting details about titles
and people, and exploring TV series episodes.
"""

import importlib
from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.instructions import load_agent_instructions

IMDB_TOOLS = "aria.tools.imdb"


class IMDbExpertAgent(FunctionAgent):
    """
    A specialized agent for movie and TV series information retrieval.

    This agent extends FunctionAgent to provide IMDb search and lookup
    capabilities including title search, movie details, person information,
    filmography, TV episodes, reviews, and trivia.
    """

    @staticmethod
    def get_system_prompt(extras: Optional[str] = None) -> str:
        """
        Return the system prompt for the IMDB Expert Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        return load_agent_instructions(
            agent_name="spielberg", extras=extras, include_core=True
        )


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

    logger.debug(f"Creating IMDbExpertAgent with {len(tools)} tools")

    agent = IMDbExpertAgent(
        name="Spielberg",
        description=(
            "Specialized in movie and TV series information, actor/director "
            "details, and entertainment research using IMDb data."
        ),
        tools=tools,
        llm=llm,
        system_prompt=IMDbExpertAgent.get_system_prompt(extras=extras),
        streaming=True,
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
