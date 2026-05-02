"""Configuration display and optimization commands for the Aria CLI.

This module provides commands to display, inspect, and optimize the
configuration settings for the Aria application.

Commands:
    show: Display all configuration settings (paths + database + api)
    paths: Show all configured file system paths
    database: Show database connection configuration
    api: Show API endpoint configuration
    optimize: Optimize .env settings based on current hardware

Example:
    ```bash
    # Show all configuration
    aria config show

    # Show only paths
    aria config paths

    # Show database configuration
    aria config database

    # Show API configuration
    aria config api

    # Optimize .env for current hardware
    aria config optimize

    # Dry-run (show changes without writing)
    aria config optimize --dry-run
    ```
"""

import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from aria.config.database import ChromaDB, SQLite
from aria.config.folders import Data, Debug, Storage
from aria.config.models import Chat, Embeddings, Vision

app = typer.Typer(
    name="config",
    help="Configuration display commands.",
)

console = Console()


@app.command("show")
def show_config():
    """Display all configuration settings.

    Runs paths, database, and api sub-commands in sequence.

    Example:
        ```bash
        aria config show
        ```
    """
    show_paths()
    console.print()
    show_database()
    console.print()
    show_api()


@app.command("paths")
def show_paths():
    """Show all configured file system paths.

    Displays a table of all file system paths used by the application:
    - Data folder
    - Storage location
    - Debug logs
    - Database files

    Example:
        ```bash
        aria config paths
        ```
    """
    console.print("[bold]File System Paths[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Path", style="green")
    table.add_column("Exists", style="yellow", width=8)

    paths = [
        ("Data Folder", Data.path),
        ("Storage Path", Storage.path),
        ("Debug Logs", Debug.logs_path),
        ("Database File", SQLite.file_path),
        ("ChromaDB Path", ChromaDB.db_path),
    ]

    for name, path in paths:
        exists = "[green]✓[/green]" if path.exists() else "[red]✗[/red]"
        table.add_row(name, str(path), exists)

    console.print(table)


@app.command("database")
def show_database():
    """Show database connection configuration.

    Displays database connection details including:
    - SQLite file path
    - Connection URLs (sync and async)
    - ChromaDB path

    Example:
        ```bash
        aria config database
        ```
    """
    console.print("[bold]Database Configuration[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("SQLite File", str(SQLite.file_path))
    table.add_row("Sync URL", SQLite.db_url)
    table.add_row("Async URL", SQLite.conn_info)
    table.add_row("ChromaDB Path", str(ChromaDB.db_path))

    # Check if database exists
    db_exists = SQLite.file_path.exists()
    table.add_row(
        "Database Exists",
        "[green]✓ Yes[/green]" if db_exists else "[red]✗ No[/red]",
    )

    console.print(table)


@app.command("api")
def show_api():
    """Show API configuration.

    Displays API endpoint configuration including:
    - Chat API URL
    - Embeddings API URL and model
    - Token limits

    Example:
        ```bash
        aria config api
        ```
    """
    console.print("[bold]API Configuration[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Chat API URL", Chat.api_url)
    table.add_row("Max Iterations", str(Chat.max_iteration))
    table.add_row("Embeddings API", Embeddings.api_url)
    table.add_row("Embeddings Model", Embeddings.model)
    table.add_row("Token Limit", str(Embeddings.token_limit))

    console.print(table)


def _read_env_file(env_path: Path) -> dict[str, str]:
    """Read .env file and return key-value pairs.

    Preserves ordering and comments. Returns a dict of KEY=VALUE.
    """
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            # Strip inline comments (value # comment)
            if " #" in value:
                value = value[: value.index(" #")]
            # Strip quotes from value
            value = value.strip()
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ('"', "'")
            ):
                value = value[1:-1]
            env_vars[key.strip()] = value
    return env_vars


def _update_env_file(env_path: Path, updates: dict[str, str]) -> list[str]:
    """Update values in .env file. Returns list of keys that were changed.

    If a key doesn't exist, it is appended at the end.
    """
    if not env_path.exists():
        return list(updates.keys())

    content = env_path.read_text()
    changed = []

    for key, new_value in updates.items():
        # Match existing KEY=VALUE (with optional quotes)
        pattern = re.compile(
            rf"^(export\s+)?{re.escape(key)}=(.*?)(\s*#.*)?$", re.MULTILINE
        )
        match = pattern.search(content)
        if match:
            old_value = match.group(2).strip()
            # Strip quotes for comparison
            if (
                len(old_value) >= 2
                and old_value[0] == old_value[-1]
                and old_value[0] in ('"', "'")
            ):
                old_compare = old_value[1:-1]
            else:
                old_compare = old_value
            if old_compare != new_value:
                # Preserve comment if present
                comment = match.group(3) or ""
                prefix = match.group(1) or ""
                replacement = f"{prefix}{key}={new_value}{comment}"
                content = (
                    content[: match.start()]
                    + replacement
                    + content[match.end() :]
                )
                changed.append(key)
        else:
            # Key doesn't exist, append it
            content = content.rstrip() + f"\n{key}={new_value}\n"
            changed.append(key)

    env_path.write_text(content)
    return changed


@app.command("optimize")
def optimize_config(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show changes without writing to .env"),
    ] = False,
):
    """Optimize .env configuration based on current hardware.

    Detects GPU VRAM, system RAM, and downloaded models, then calculates
    the optimal context sizes, KV cache placement, and token limits.

    Example:
        ```bash
        # Optimize and write to .env
        aria config optimize

        # Preview changes without writing
        aria config optimize --dry-run
        ```
    """
    from aria.helpers.memory import (
        detect_system_ram,
        get_model_file_size,
    )
    from aria.helpers.nvidia import (
        calculate_max_safe_context,
        detect_gpu_count,
        detect_gpus_with_details,
        detect_nvlink,
        get_free_vram_per_gpu,
        get_total_vram_mb,
    )
    from aria.scripts.gguf import get_model_path

    # ── 1. Detect Hardware ─────────────────────────────────────
    gpus = detect_gpus_with_details()
    total_vram = get_total_vram_mb()
    free_vram_list = get_free_vram_per_gpu()
    total_ram_mb, avail_ram_mb = detect_system_ram()
    gpu_count = detect_gpu_count()
    has_nvlink, _ = detect_nvlink()

    # ── 2. Display Hardware ────────────────────────────────────
    console.print("[bold]Hardware Detected[/bold]\n")

    hw_table = Table(show_header=True, header_style="bold cyan")
    hw_table.add_column("Component", style="cyan", width=16)
    hw_table.add_column("Details", style="green")

    if gpus:
        for i, gpu in enumerate(gpus):
            free_mb = free_vram_list[i] if i < len(free_vram_list) else 0
            hw_table.add_row(
                f"GPU {i}",
                f"{gpu.name} — {gpu.total_memory} MB total, "
                f"{free_mb} MB free",
            )
    else:
        hw_table.add_row("GPU", "[yellow]No NVIDIA GPU detected[/yellow]")

    hw_table.add_row("GPU Count", str(gpu_count))

    hw_table.add_row(
        "Total VRAM",
        (
            f"{total_vram} MiB ({total_vram / 1024:.1f} GiB)"
            if total_vram > 0
            else "N/A"
        ),
    )
    hw_table.add_row("NVLink", "✓ Available" if has_nvlink else "✗ No")
    hw_table.add_row(
        "System RAM",
        (
            f"{total_ram_mb} MiB ({total_ram_mb / 1024:.1f} GiB)"
            if total_ram_mb > 0
            else "N/A"
        ),
    )
    hw_table.add_row("Available RAM", f"{avail_ram_mb} MiB")

    console.print(hw_table)

    # ── 3. Get Model Sizes ─────────────────────────────────────
    from aria.config.api import LlamaCpp as LlamaCppConfig

    models_dir = LlamaCppConfig.models_path

    model_files = {
        "chat": Chat.filename,
        "vl": Vision.filename,
        "embeddings": Embeddings.filename,
    }

    model_sizes_mb: dict[str, int] = {}
    for alias, filename in model_files.items():
        if filename:
            path = get_model_path(filename, models_dir)
            model_sizes_mb[alias] = get_model_file_size(path) if path else 0
        else:
            model_sizes_mb[alias] = 0

    # ── 4. Calculate Optimal Values ────────────────────────────
    # Use max free VRAM across GPUs for context calculation
    max_free_vram = max(free_vram_list) if free_vram_list else 0

    # Chat context: calculate based on free VRAM and chat model size
    chat_ctx = calculate_max_safe_context(
        free_vram_mb=max_free_vram,
        model_size_mb=model_sizes_mb.get("chat", 0),
        is_embedding_model=False,
    )
    # Fallback to default if no GPU detected
    if chat_ctx == 0:
        chat_ctx = 65536

    # VL context: conservative (runs alongside chat in some setups)
    vl_ctx = calculate_max_safe_context(
        free_vram_mb=max_free_vram,
        model_size_mb=model_sizes_mb.get("vl", 0),
        is_embedding_model=False,
    )
    if vl_ctx == 0:
        vl_ctx = 8192
    # Cap VL context at 16384 — vision models don't need huge context
    vl_ctx = min(vl_ctx, 16384)

    # Embeddings context: use embedding tiers
    embed_ctx = calculate_max_safe_context(
        free_vram_mb=max_free_vram,
        model_size_mb=model_sizes_mb.get("embeddings", 0),
        is_embedding_model=True,
    )
    if embed_ctx == 0:
        embed_ctx = 8192

    # KV cache offload: offload to RAM if VRAM is tight
    kv_offload = "true" if total_vram < 12288 else "false"

    # Token limit: ~1/4 of chat context, clamped to reasonable range
    token_limit = max(8192, min(chat_ctx // 4, 65536))

    # Force context: always true so our calculated values are used
    force_context = "true"

    optimized = {
        "CHAT_CONTEXT_SIZE": str(chat_ctx),
        "VL_CONTEXT_SIZE": str(vl_ctx),
        "EMBEDDINGS_CONTEXT_SIZE": str(embed_ctx),
        "KV_CACHE_OFFLOAD": kv_offload,
        "TOKEN_LIMIT": str(token_limit),
        "FORCE_CONTEXT": force_context,
    }

    # ── 5. Read Current Values ─────────────────────────────────
    env_path = Path(".env")
    current = _read_env_file(env_path)

    # ── 6. Display Comparison ──────────────────────────────────
    console.print("\n[bold]Optimized Configuration[/bold]\n")

    opt_table = Table(show_header=True, header_style="bold cyan")
    opt_table.add_column("Setting", style="cyan", width=24)
    opt_table.add_column("Current", style="white", width=12)
    opt_table.add_column("Optimized", style="green", width=12)
    opt_table.add_column("Reason", style="dim")

    # Reasons for each setting
    reasons = {
        "CHAT_CONTEXT_SIZE": (
            f"based on {max_free_vram} MB free VRAM"
            if max_free_vram > 0
            else "default (no GPU)"
        ),
        "VL_CONTEXT_SIZE": (
            "conservative for vision model"
            if max_free_vram > 0
            else "default (no GPU)"
        ),
        "EMBEDDINGS_CONTEXT_SIZE": (
            f"embedding tier for {max_free_vram} MB VRAM"
            if max_free_vram > 0
            else "default (no GPU)"
        ),
        "KV_CACHE_OFFLOAD": (
            "offload to RAM (VRAM < 12 GB)"
            if total_vram < 12288
            else "keep on GPU (VRAM ≥ 12 GB)"
        ),
        "TOKEN_LIMIT": f"~1/4 of chat context ({chat_ctx})",
        "FORCE_CONTEXT": "use calculated values exactly",
    }

    for key, new_val in optimized.items():
        old_val = current.get(key, "[dim]not set[/dim]")
        changed = old_val != new_val
        opt_table.add_row(
            key,
            str(old_val),
            f"[bold green]{new_val}[/bold green]" if changed else str(new_val),
            reasons.get(key, ""),
        )

    console.print(opt_table)

    # ── 7. Write or Report ─────────────────────────────────────
    if dry_run:
        console.print(
            "\n[yellow]Dry run — no changes written. "
            "Run without --dry-run to apply.[/yellow]"
        )
        return

    changed_keys = _update_env_file(env_path, optimized)

    if changed_keys:
        console.print(
            f"\n[green]✓ .env updated with {len(changed_keys)} "
            f"optimized value(s): {', '.join(changed_keys)}[/green]"
        )
    else:
        console.print(
            "\n[dim]✓ .env is already optimal — no changes needed.[/dim]"
        )
