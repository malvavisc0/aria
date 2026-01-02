from pathlib import Path

import typer
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.llama_cpp import LlamaCpp
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.memory import MemoryTools
from agno.tools.wikipedia import WikipediaTools
from enhancedtoolkits.calculators import ArithmeticCalculatorTools
from enhancedtoolkits.files import FilesTools
from enhancedtoolkits.finance import YFinanceTools
from enhancedtoolkits.reasoning import ReasoningTools
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.prompt import Prompt

from .instructions import AGENT_INSTRUCTIONS, MEMORY_TOOL_INSTRUCTIONS

app = typer.Typer(help="Aria: Your powerful self-hosted AI assistant.")


@app.command()
def chat():
    """Start an interactive chat session."""

    console = Console()

    agent = Agent(
        user_id="human",
        instructions=AGENT_INSTRUCTIONS,
        model=LlamaCpp(
            id="unsloth/Ministral-3-14B-Instruct-2512-GGUF",
            base_url="http://localhost:8080/v1",
        ),
        tools=[
            ReasoningTools(),
            DuckDuckGoTools(),
            YFinanceTools(),
            MemoryTools(
                db=SqliteDb(db_file="/tmp/aria_memory.db"),
                instructions=MEMORY_TOOL_INSTRUCTIONS,
            ),
            WikipediaTools(),
            ArithmeticCalculatorTools(),
            ArxivTools(),
            FilesTools(base_dir=Path("./outputs")),
        ],
        add_datetime_to_context=True,
        # NOTE: enabling stream_events may cause the SDK to emit a final full-content event
        # after streaming deltas, which can lead to repeated output in the UI loop below.
        stream_events=False,
        markdown=True,
        debug_mode=False,
    )

    while True:
        user_input = Prompt.ask(prompt=">", console=console)
        if user_input.lower() in ["/quit"]:
            raise typer.Abort()
        full_response = ""
        with Live(Markdown(""), auto_refresh=True) as live:
            for chunk in agent.run(input=user_input, stream=True):
                if not chunk.content:
                    continue

                chunk_str = str(chunk.content)

                # Some backends emit a final "full response" chunk after streaming deltas.
                # If we already accumulated that exact content, skip to avoid duplication.
                if chunk_str == full_response:
                    continue

                full_response += chunk_str
                live.update(Markdown(full_response))


if __name__ == "__main__":
    app()
