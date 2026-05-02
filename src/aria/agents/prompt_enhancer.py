"""Prompt Enhancer Agent

This module defines a specialized agent for enhancing and optimizing prompts
to maximize effectiveness when interacting with AI systems. The agent applies
prompt engineering best practices to improve clarity, specificity, and overall
quality of user prompts.
"""

from datetime import datetime

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from pydantic import BaseModel, Field

from aria.agents.instructions import load_agent_instructions


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
        return load_agent_instructions(
            "prompt_enhancer",
            extras,
            base_sections=["core"],
        )


def get_agent(
    llm: LLM,
) -> PromptEnhancerAgent:
    """
    Create a prompt enhancer agent with the given LLM.

    This function initializes and returns a FunctionAgent configured for
    prompt enhancement operations. The agent specializes in applying prompt
    engineering best practices to improve clarity, specificity, and
    effectiveness of user prompts.

    Args:
        llm (LLM): The language model to use for the agent

    Returns:
        PromptEnhancerAgent: A configured prompt enhancement agent instance
                            ready for prompt optimization tasks

    Example:
        >>> from llama_index.core.llms import OpenAI
        >>> llm = OpenAI(model="gpt-4")
        >>> agent = get_agent(llm, extras="Focus on technical documentation")
        >>> # Agent is now ready to enhance prompts
    """
    timestamp = datetime.now()
    extras = (
        f"- **Current date**: {timestamp.strftime('%B %dth')} "
        + f"- **Current time**: {timestamp.strftime('%H:%M')} "
        + f"- **Timezone**: {timestamp.astimezone().tzinfo}"
    )

    tools = []

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
