"""User management commands for the Aria CLI.

This module provides commands to manage users in the Aria database,
including listing, creating, and modifying user accounts.

Commands:
    list: Display all users in a formatted table
    add: Create a new user with email and password
    reset: Reset a user's password
    edit: Modify user metadata and role

Example:
    ```bash
    # List all users
    aria users list

    # Add a new user
    aria users add --identifier user@example.com --role admin

    # Reset password
    aria users reset --identifier user@example.com

    # Edit user role
    aria users edit --identifier user@example.com --role admin
    ```
"""

import json
import uuid
from datetime import datetime
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import select

from aria.cli import get_db_session
from aria.db.auth import hash_password
from aria.db.models import User

app = typer.Typer(
    name="users",
    help="User management commands for the Aria application.",
)


console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("list")
def list_users():
    """List all users in the database.

    Displays a formatted table with user information including:
    - User ID (UUID)
    - Identifier (email)
    - Role (from metadata)
    - Creation timestamp

    Shows total count of users at the bottom of the table.

    Example:
        ```bash
        aria users list
        ```
    """
    with get_db_session() as session:
        try:
            users = session.execute(select(User)).scalars().all()

            if not users:
                console.print(
                    Panel(
                        "[yellow]No users found in database.[/yellow]",
                        title="[bold]Users[/bold]",
                        border_style="yellow",
                    )
                )
                return

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("ID", style="dim", width=36)
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

            console.print(
                Panel(
                    table,
                    title=f"[bold]Users[/bold] ({len(users)} total)",
                    border_style="cyan",
                )
            )

        except Exception as e:
            error_console.print(
                Panel(
                    f"[red]Error listing users: {e}[/red]",
                    title="[bold]Error[/bold]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
        finally:
            session.close()


@app.command("add")
def add_user(
    identifier: Annotated[
        str,
        typer.Option(
            prompt="User identifier (email)", help="User email address"
        ),
    ],
    role: Annotated[
        str, typer.Option(help="User role (user, admin, etc.)")
    ] = "user",
):
    """Create a new user account.

    Creates a new user with the specified email and role. The password
    will be prompted securely (hidden input with confirmation).

    Args:
        identifier: User email address (used for login)
        role: User role for access control (default: "user")

    Example:
        ```bash
        # Create admin user
        aria users add --identifier admin@example.com --role admin

        # Create regular user (default role)
        aria users add --identifier user@example.com
        ```
    """
    with get_db_session() as session:
        try:
            user = session.execute(
                select(User).where(User.identifier == identifier)
            ).scalar_one_or_none()

            if user:
                error_console.print(
                    Panel(
                        f"[red]User '{identifier}' already exists![/red]",
                        title="[bold]Error[/bold]",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)

            password = typer.prompt(
                text="Password",
                confirmation_prompt=True,
                type=str,
                hide_input=True,
            )

            user = User(
                id=str(uuid.uuid4()),
                identifier=identifier,
                metadata_=json.dumps(
                    {
                        "role": role,
                        "created_by": "cli",
                    }
                ),
                password=hash_password(password),
                createdAt=datetime.now().isoformat() + "Z",
            )

            session.add(user)

            console.print(
                Panel(
                    f"[green]✓[/green] User '[cyan]{identifier}[/cyan]' created successfully!\n"
                    f"[dim]Role: {role}[/dim]",
                    title="[bold]User Created[/bold]",
                    border_style="green",
                )
            )

        except typer.Exit:
            raise
        except Exception as e:
            error_console.print(
                Panel(
                    f"[red]Error creating user: {e}[/red]",
                    title="[bold]Error[/bold]",
                    border_style="red",
                )
            )


@app.command("reset")
def reset_password(
    identifier: Annotated[
        str,
        typer.Option(
            prompt="User identifier (email)", help="User email address"
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            prompt="New password", hide_input=True, help="New password"
        ),
    ],
):
    """Reset a user's password.

    Updates the password for an existing user. The password is prompted
    securely and the metadata is updated with a timestamp for audit trail.

    Args:
        identifier: User email address
        password: New password (prompted securely)

    Example:
        ```bash
        aria users reset --identifier user@example.com
        ```
    """
    with get_db_session() as session:
        try:
            # Find user
            user = session.execute(
                select(User).where(User.identifier == identifier)
            ).scalar_one_or_none()

            if not user:
                error_console.print(
                    Panel(
                        f"[red]User '{identifier}' not found![/red]",
                        title="[bold]Error[/bold]",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)

            # Update password field
            user.password = hash_password(password)

            # Update metadata with timestamp for audit trail
            metadata = json.loads(user.metadata_)
            metadata["password_updated_at"] = datetime.now().isoformat()
            user.metadata_ = json.dumps(metadata)

            console.print(
                Panel(
                    f"[green]✓[/green] Password reset for '[cyan]{identifier}[/cyan]' successfully!",
                    title="[bold]Password Reset[/bold]",
                    border_style="green",
                )
            )

        except typer.Exit:
            raise
        except Exception as e:
            error_console.print(
                Panel(
                    f"[red]Error resetting password: {e}[/red]",
                    title="[bold]Error[/bold]",
                    border_style="red",
                )
            )


@app.command("edit")
def update_user(
    identifier: Annotated[
        str,
        typer.Option(
            prompt="User identifier (email)", help="User email address"
        ),
    ],
    role: Annotated[
        Optional[str], typer.Option(help="New role for the user")
    ] = None,
    metadata_json: Annotated[
        Optional[str], typer.Option(help="JSON string of metadata to merge")
    ] = None,
):
    """Modify user metadata and role.

    Updates user metadata by merging the provided values. At least one
    of --role or --metadata-json must be provided.

    Args:
        identifier: User email address
        role: New role to assign (optional)
        metadata_json: JSON object to merge into existing metadata (optional)

    Example:
        ```bash
        # Change user role
        aria users edit --identifier user@example.com --role admin

        # Update metadata
        aria users edit --identifier user@example.com --metadata-json '{"department": "engineering"}'

        # Update both
        aria users edit --identifier user@example.com --role admin --metadata-json '{"department": "engineering"}'
        ```
    """
    with get_db_session() as session:
        try:
            # Find user
            user = session.execute(
                select(User).where(User.identifier == identifier)
            ).scalar_one_or_none()

            if not user:
                error_console.print(
                    Panel(
                        f"[red]User '{identifier}' not found![/red]",
                        title="[bold]Error[/bold]",
                        border_style="red",
                    )
                )
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
                    error_console.print(
                        Panel(
                            f"[red]Invalid JSON: {e}[/red]",
                            title="[bold]Error[/bold]",
                            border_style="red",
                        )
                    )
                    raise typer.Exit(1)

            metadata["updated_at"] = datetime.now().isoformat()

            user.metadata_ = json.dumps(metadata)

            console.print(
                Panel(
                    f"[green]✓[/green] User '[cyan]{identifier}[/cyan]' updated successfully!\n\n"
                    f"[dim]Metadata:[/dim]\n{json.dumps(metadata, indent=2)}",
                    title="[bold]User Updated[/bold]",
                    border_style="green",
                )
            )

        except typer.Exit:
            raise
        except Exception as e:
            error_console.print(
                Panel(
                    f"[red]Error updating user: {e}[/red]",
                    title="[bold]Error[/bold]",
                    border_style="red",
                )
            )


if __name__ == "__main__":
    app()
