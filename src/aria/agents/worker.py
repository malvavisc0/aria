"""Worker agent — runs headlessly in background with full tool set.

The WorkerAgent is a FunctionAgent configured with the full core + file
tool set (reasoning, plan, scratchpad, shell + all file tools) and
worker-specific instructions that mandate autonomous execution and
forbid sub-worker spawning.
"""

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from loguru import logger

from aria.agents.instructions import load_agent_instructions
from aria.tools.registry import get_tools


class WorkerAgent(FunctionAgent):
    """Background worker agent. Same tools as Aria, no sub-spawning."""

    @staticmethod
    def get_system_prompt(
        extras: str | None = None,
        output_dir: str | None = None,
    ) -> str:
        base = load_agent_instructions(
            agent_name="worker",
            extras=extras,
            base_sections=["core", "tools", "failure"],
        )
        if output_dir:
            base += (
                f"\n\n## Output Directory\nWrite all deliverables to: `{output_dir}`"
            )
        return base


def get_worker_agent(
    llm: LLM,
    extras: str | None = None,
    output_dir: str | None = None,
) -> WorkerAgent:
    """Create a WorkerAgent with full tool set (plan, scratchpad included)."""
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
