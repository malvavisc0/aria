"""aria2 - ai assistant"""

import datetime
import json
import uuid
from typing import Annotated, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from aria.config import CHAT_HISTORY_DB_URL
from aria.db.auth import hash_password
from aria.db.models import Base, User

app = typer.Typer()
console = Console()
error_console = Console(stderr=True, style="bold red")


def _get_db_session() -> Session:
    """Get a database session for user management commands."""
    engine = create_engine(CHAT_HISTORY_DB_URL)
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
