"""Worker agent — same capabilities as Aria, runs headlessly in background.

The WorkerAgent is a FunctionAgent configured with the same core + file
tools as Aria but with worker-specific instructions that mandate
autonomous execution and forbid sub-worker spawning.
"""

from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from loguru import logger

from aria.agents.instructions import load_agent_instructions
from aria.tools.registry import get_tools


class WorkerAgent(FunctionAgent):
    """Background worker agent. Same tools as Aria, no sub-spawning."""

    @staticmethod
    def get_system_prompt(
        extras: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> str:
        base = load_agent_instructions(
            agent_name="worker",
            extras=extras,
            base_sections=["core", "tools", "failure"],
        )
        if output_dir:
            base += (
                f"\n\n## Output Directory\n"
                f"Write all deliverables to: `{output_dir}`"
            )
        return base


def get_worker_agent(
    llm: LLM,
    extras: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> WorkerAgent:
    """Create a WorkerAgent with same tools as Aria (minus worker spawning)."""
    from aria.tools.registry import CORE, FILES

    tools = get_tools([CORE, FILES])

    logger.debug(f"Creating WorkerAgent with {len(tools)} tools")

    return WorkerAgent(
        name="Worker",
        description="Background worker for complex tasks.",
        tools=tools,
        llm=llm,
        system_prompt=WorkerAgent.get_system_prompt(
            extras=extras, output_dir=output_dir
        ),
        streaming=False,
        verbose=False,
    )
