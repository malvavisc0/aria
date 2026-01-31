"""Prompt Enhancer Agent

This module defines a specialized agent for enhancing and optimizing prompts
to maximize effectiveness when interacting with AI systems. The agent applies
prompt engineering best practices to improve clarity, specificity, and overall
quality of user prompts.
"""

from pathlib import Path
from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from loguru import logger
from pydantic import BaseModel, Field


class PromptEnhancementResult(BaseModel):
    """Data model for storing prompt enhancement results.

    This model captures both the original prompt and its enhanced version,
    along with a rationale explaining the enhancement decisions made.
    """

    original: str = Field(description="Exact user input (unchanged)")
    enhanced: str = Field(description="Improved version of the prompt")
    rationale: str = Field(
        description="One paragraph explaining changes (with no formatting)"
    )


class PromptEnhancerAgent(FunctionAgent):
    """
    A specialized agent for enhancing prompts for better AI responses.

    This agent extends FunctionAgent to provide prompt engineering
    capabilities including clarity improvement, context enrichment, and
    structural optimization. It transforms basic prompts into well-crafted
    instructions that elicit higher quality responses from AI systems.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the Prompt Enhancer Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        instructions_path = (
            Path(__file__).parent / "instructions" / "prompt_enhancer.md"
        )

        instructions = ""
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            instructions = file.read()

        return f"{instructions}\n\n## Extras\n{extras}"


def get_agent(llm: LLM, extras: Optional[str] = None) -> PromptEnhancerAgent:
    """
    Create a prompt enhancer agent with the given LLM.

    This function initializes and returns a FunctionAgent configured for
    prompt enhancement operations. The agent specializes in applying prompt
    engineering best practices to improve clarity, specificity, and
    effectiveness of user prompts.

    Args:
        llm (LLM): The language model to use for the agent
        extras (str, optional): Additional system prompt instructions to
                               append to the base system prompt.
                               Defaults to None.

    Returns:
        PromptEnhancerAgent: A configured prompt enhancement agent instance
                            ready for prompt optimization tasks

    Example:
        >>> from llama_index.core.llms import OpenAI
        >>> llm = OpenAI(model="gpt-4")
        >>> agent = get_agent(llm, extras="Focus on technical documentation")
        >>> # Agent is now ready to enhance prompts
    """
    tools = []
    logger.debug(f"Creating PromptEnhancerAgent with {len(tools)} tools")
    logger.debug(f"Tool names: {[tool.metadata.name for tool in tools]}")
    logger.debug(f"LLM type: {type(llm)}")

    agent = PromptEnhancerAgent(
        name="Prompt Enhancer",
        description=(
            "Specialized in enhancing prompts for better AI responses. "
            "Improves clarity, specificity, and effectiveness of prompts "
            "using prompt engineering best practices."
        ),
        tools=tools,
        llm=llm,
        system_prompt=PromptEnhancerAgent.get_system_prompt(extras or ""),
        streaming=False,
        verbose=False,
        output_cls=PromptEnhancementResult,
    )

    return agent
