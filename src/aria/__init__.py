"""aria2 - ai assistant"""

import asyncio
import datetime
import json
import os
import uuid
from typing import Annotated, Optional, Union

import typer
from llama_index.core.agent.workflow import (
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult,
)
from llama_index.core.workflow import StopEvent
from llama_index.llms.openai import OpenAI
from loguru import logger
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from aria.agents import (
    DeepReasoningAgent,
    FileEditorAgent,
    MarketAnalystAgent,
    PromptEnhancerAgent,
    PythonDeveloperAgent,
    WebResearcherAgent,
    get_file_editor_agent,
    get_market_analyst_agent,
    get_prompt_enhancer_agent,
    get_python_developer_agent,
    get_reasoning_agent,
    get_web_researcher_agent,
)
from aria.db.auth import hash_password, verify_password
from aria.db.models import Base, User

# Configure loguru to not interfere with Rich console output
# Remove default handler and add one that writes to a file
log_path = os.path.expanduser(".files/debug.log")
logger.add(
    log_path,
    rotation="10 MB",
    level="DEBUG",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
)

app = typer.Typer()
console = Console()
error_console = Console(stderr=True, style="bold red")


timestamp = datetime.datetime.now()
CURRENT_DATE = (
    f"- **Current date**: {timestamp.strftime('%B %dth')} "
    + f"- **Current time**: {timestamp.strftime('%H:%M')} "
    + f"- **Timezone**: {timestamp.astimezone().tzinfo}"
)


def generate_agent_id(agent_name: str) -> str:
    """Generate unique agent ID for session isolation."""
    return f"{agent_name}_{uuid.uuid4().hex[:8]}"


logger.debug("Initializing AriaLLM for llamacpp server")
AriaLLM = OpenAI(
    api_base="http://skynet.tago.lan:7070/v1",
    api_key="sk-dummy",  # llamacpp doesn't need real key but OpenAI client requires one
)
logger.debug(f"AriaLLM initialized: api_base={AriaLLM.api_base}")


async def _run_agent_with_streaming(
    agent: Union[
        FileEditorAgent,
        PythonDeveloperAgent,
        DeepReasoningAgent,
        MarketAnalystAgent,
        WebResearcherAgent,
    ],
    query: str,
) -> None:
    """
    Run agent with streaming output and verbose tool execution display.

    Executes the agent's workflow asynchronously and streams the output
    in real time. Displays tool calls, tool results, and LLM responses
    using Rich formatting for clear visibility of all agent actions.

    Args:
        agent: The agent instance to run (FileEditorAgent,
               PythonDeveloperAgent, DeepReasoningAgent, etc.)
        query: The user's input message to pass to the agent.

    Returns:
        None: Displays output live to the console.

    Raises:
        Exception: Any exceptions during agent execution are caught,
                   printed to stderr, and re-raised.
    """
    try:
        handler = agent.run(user_msg=query)

        accumulated = ""
        with Live(
            Markdown(""),
            refresh_per_second=10,
            console=console,
            vertical_overflow="visible",
            transient=False,
        ) as live:
            async for event in handler.stream_events():

                if isinstance(event, ToolCall):
                    # Display tool call with parameters
                    kwargs_str = json.dumps(event.tool_kwargs, indent=2)
                    console.print(
                        Panel(
                            (
                                f"[yellow]Tool:[/yellow] "
                                f"[bold]{event.tool_name}[/bold]\n"
                                f"[dim]Parameters:[/dim]\n{kwargs_str}"
                            ),
                            title="🔧 Tool Call",
                            border_style="yellow",
                            expand=False,
                        )
                    )

                elif isinstance(event, ToolCallResult):
                    # Display tool result
                    try:
                        # Try to parse as JSON for pretty printing
                        if hasattr(event.tool_output, "content"):
                            content = event.tool_output.content
                            if isinstance(content, str):
                                output_data = json.loads(content)
                                output_str = json.dumps(output_data, indent=2)
                            else:
                                output_str = str(content)
                        else:
                            output_str = str(event.tool_output)

                        # Truncate if too long
                        if len(output_str) > 800:
                            output_str = output_str[:800] + "\n... (truncated)"
                    except (json.JSONDecodeError, AttributeError):
                        output_str = str(event.tool_output)[:800]

                    # Check for errors
                    is_error = getattr(event.tool_output, "is_error", False)
                    style = "red" if is_error else "green"
                    icon = "❌" if is_error else "✅"

                    console.print(
                        Panel(
                            (
                                f"[{style}]Tool:[/{style}] "
                                f"[bold]{event.tool_name}[/bold]\n"
                                f"[dim]Result:[/dim]\n{output_str}"
                            ),
                            title=f"{icon} Tool Result",
                            border_style=style,
                            expand=False,
                        )
                    )

                elif isinstance(event, AgentStream):
                    # Stream LLM response as markdown
                    delta = event.delta or ""
                    accumulated += delta
                    live.update(Markdown(accumulated))

                elif isinstance(event, AgentOutput):
                    # Show completion message with timing if available
                    if (
                        hasattr(event, "raw")
                        and event.raw
                        and isinstance(event.raw, dict)
                    ):
                        timings = event.raw.get("timings", {})
                        if timings:
                            predicted_n = timings.get("predicted_n", 0)
                            predicted_ms = timings.get("predicted_ms", 0)
                            console.print(
                                f"[bold green]✨ Response complete"
                                f"[/bold green] "
                                f"[dim]({predicted_n} tokens in "
                                f"{predicted_ms/1000:.1f}s)[/dim]"
                            )
                        else:
                            console.print(
                                "[bold green]✨ Response complete"
                                "[/bold green]"
                            )
                    else:
                        console.print(
                            "[bold green]✨ Response complete[/bold green]"
                        )

                elif isinstance(event, StopEvent):
                    # Silent - workflow ended
                    pass
    except Exception as e:
        error_console.print(f"Error: {e}")
        raise


@app.command()
def editor(query: str = typer.Option(..., prompt=">")):
    """Run the file editor agent."""
    agent = get_file_editor_agent(llm=AriaLLM, extras=CURRENT_DATE)
    asyncio.run(_run_agent_with_streaming(agent, query))


@app.command()
def developer(query: Annotated[str, typer.Option(prompt=">")]):
    """Run the Python Developer agent"""
    agent = get_python_developer_agent(llm=AriaLLM, extras=CURRENT_DATE)
    asyncio.run(_run_agent_with_streaming(agent, query))


@app.command()
def socrates(query: Annotated[str, typer.Option(prompt=">")]):
    """Run the Deep Reasoning agent"""
    agent_id = generate_agent_id("socrates")
    extras = f"{CURRENT_DATE}\n- **Agent ID**: {agent_id}"
    agent = get_reasoning_agent(llm=AriaLLM, extras=extras)
    asyncio.run(_run_agent_with_streaming(agent, query))


@app.command()
def investor(query: Annotated[str, typer.Option(prompt=">")]):
    """Run the Market Analyst agent"""
    agent = get_market_analyst_agent(llm=AriaLLM, extras=CURRENT_DATE)
    asyncio.run(_run_agent_with_streaming(agent, query))


@app.command()
def researcher(query: Annotated[str, typer.Option(prompt=">")]):
    """Run the Web Researcher agent"""
    agent = get_web_researcher_agent(llm=AriaLLM, extras=CURRENT_DATE)
    asyncio.run(_run_agent_with_streaming(agent, query))


@app.command()
def enhancer(query: Annotated[str, typer.Option(prompt=">")]):
    """Run the Prompt Enhancer agent"""

    async def run_agent(
        agent: PromptEnhancerAgent,
        query: str,
    ) -> None:
        """
        Run the Prompt Enhancer agent asynchronously and display the structured response.

        This function takes a PromptEnhancerAgent instance and a user query,
        executes the agent's workflow asynchronously, and prints the structured
        response using Rich's console for formatted output.

        Args:
            agent: The PromptEnhancerAgent instance to run.
            query: The user's input message to pass to the agent.

        Returns:
            None: The function does not return a value but prints the response.

        Raises:
            Exception: Any exceptions raised during the agent execution are caught,
                       printed to stderr with Rich, and re-raised.
        """
        try:
            response = await agent.run(user_msg=query)
            console.print(response.structured_response)
        except Exception as e:
            error_console.print(f"Error: {e}")
            raise

    agent = get_prompt_enhancer_agent(llm=AriaLLM, extras=CURRENT_DATE)
    asyncio.run(run_agent(agent, query))


def _get_db_session() -> Session:
    """Get a database session for user management commands."""
    os.makedirs("data", exist_ok=True)
    sync_url = "sqlite:///./data/chainlit.db"
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    return Session(engine)


@app.command()
def add_user(
    identifier: Annotated[str, typer.Option(prompt="User identifier (email)")],
    password: Annotated[
        str, typer.Option(prompt="Password", hide_input=True)
    ] = "",
    role: Annotated[str, typer.Option()] = "user",
):
    """Add a new user to the database."""
    session = _get_db_session()

    try:
        # Check if user already exists
        existing = session.execute(
            select(User).where(User.identifier == identifier)
        ).scalar_one_or_none()

        if existing:
            error_console.print(f"User '{identifier}' already exists!")
            raise typer.Exit(1)

        # Create new user
        user_id = str(uuid.uuid4())
        metadata = {
            "role": role,
            "created_by": "cli",
        }

        user = User(
            id=user_id,
            identifier=identifier,
            metadata_=json.dumps(metadata),
            password=hash_password(password) if password else None,
            createdAt=datetime.datetime.now().isoformat() + "Z",
        )

        session.add(user)
        session.commit()

        console.print(
            f"[green]✓[/green] User '{identifier}' created successfully!"
        )
        console.print(f"  ID: {user_id}")
        console.print(f"  Role: {role}")

    except Exception as e:
        session.rollback()
        error_console.print(f"Error creating user: {e}")
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def reset_password(
    identifier: Annotated[str, typer.Option(prompt="User identifier (email)")],
    password: Annotated[
        str, typer.Option(prompt="New password", hide_input=True)
    ],
):
    """Reset a user's password."""
    session = _get_db_session()

    try:
        # Find user
        user = session.execute(
            select(User).where(User.identifier == identifier)
        ).scalar_one_or_none()

        if not user:
            error_console.print(f"User '{identifier}' not found!")
            raise typer.Exit(1)

        # Update password field
        user.password = hash_password(password)

        # Update metadata with timestamp for audit trail
        metadata = json.loads(user.metadata_)
        metadata["password_updated_at"] = datetime.datetime.now().isoformat()
        user.metadata_ = json.dumps(metadata)

        session.commit()

        console.print(
            f"[green]✓[/green] Password reset for '{identifier}' successfully!"
        )

    except Exception as e:
        session.rollback()
        error_console.print(f"Error resetting password: {e}")
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def update_user(
    identifier: Annotated[str, typer.Option(prompt="User identifier (email)")],
    role: Annotated[Optional[str], typer.Option()] = None,
    metadata_json: Annotated[
        Optional[str], typer.Option(help="JSON string of metadata to merge")
    ] = None,
):
    """Update user metadata."""
    session = _get_db_session()

    try:
        # DEBUG: Log what we're searching for
        logger.debug(f"update_user: searching for identifier='{identifier}'")

        # Find user
        user = session.execute(
            select(User).where(User.identifier == identifier)
        ).scalar_one_or_none()

        # DEBUG: Log query result
        logger.debug(f"update_user: user found = {user is not None}")

        # DEBUG: If not found, try to list all users to see what's in the DB
        if not user:
            all_users = session.execute(select(User)).scalars().all()
            logger.debug(f"update_user: total users in DB = {len(all_users)}")
            for u in all_users:
                logger.debug(f"  - id={u.id}, identifier={u.identifier}")
            error_console.print(f"User '{identifier}' not found!")
            raise typer.Exit(1)

        # Update metadata
        metadata = json.loads(user.metadata_)

        if role:
            metadata["role"] = role

        if metadata_json:
            try:
                new_metadata = json.loads(metadata_json)
                metadata.update(new_metadata)
            except json.JSONDecodeError as e:
                error_console.print(f"Invalid JSON: {e}")
                raise typer.Exit(1)

        metadata["updated_at"] = datetime.datetime.now().isoformat()

        user.metadata_ = json.dumps(metadata)
        session.commit()

        console.print(
            f"[green]✓[/green] User '{identifier}' updated successfully!"
        )
        console.print(f"  Metadata: {json.dumps(metadata, indent=2)}")

    except Exception as e:
        session.rollback()
        error_console.print(f"Error updating user: {e}")
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def list_users():
    """List all users in the database."""
    session = _get_db_session()

    try:
        users = session.execute(select(User)).scalars().all()

        if not users:
            console.print("[yellow]No users found in database.[/yellow]")
            return

        table = Table(title="Users")
        table.add_column("ID", style="cyan")
        table.add_column("Identifier", style="green")
        table.add_column("Role", style="yellow")
        table.add_column("Created At", style="dim")

        for user in users:
            metadata = json.loads(user.metadata_)
            role = metadata.get("role", "unknown")
            table.add_row(
                str(user.id),
                str(user.identifier),
                role,
                str(user.createdAt or ""),
            )

        console.print(table)
        console.print(f"\n[dim]Total users: {len(users)}[/dim]")

    except Exception as e:
        error_console.print(f"Error listing users: {e}")
        raise typer.Exit(1)
    finally:
        session.close()


def main():
    """
    Docstring for main
    """
    app()


if __name__ == "__main__":
    app()
