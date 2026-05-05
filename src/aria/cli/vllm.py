"""vLLM engine management commands for the Aria CLI.

This module provides commands to install and inspect the vLLM inference
engine. vLLM is installed as a Python package — no separate binaries
are needed.

Commands:
    install: Install vLLM with the appropriate hardware target
    status: Check vLLM installation status and version
    info: Show vLLM configuration details

Example:
    ```bash
    # Install vLLM with auto-detected hardware target
    aria vllm install

    # Check installation status
    aria vllm status

    # Show configuration
    aria vllm info
    ```
"""

import typer
from rich.console import Console
from rich.table import Table

from aria.scripts.vllm import get_vllm_version, is_vllm_installed

app = typer.Typer(
    name="vllm",
    help="vLLM inference engine management commands.",
)

console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("install")
def install_command():
    """Install vLLM with the appropriate hardware target.

    Automatically detects CUDA, ROCm, or CPU and installs the
    matching vLLM package.

    Example:
        ```bash
        aria vllm install
        ```
    """
    from aria.scripts.vllm import install_vllm

    try:
        install_vllm()
    except Exception as e:
        error_console.print(f"[red]✗[/red] Installation failed: {e}")
        raise typer.Exit(1)


@app.command("status")
def check_status():
    """Check vLLM installation status and version.

    Displays whether vLLM is installed and the current version.

    Example:
        ```bash
        aria vllm status
        ```
    """
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    if is_vllm_installed():
        version = get_vllm_version()
        table.add_row("vLLM", "[green]✓ Installed[/green]")
        table.add_row("Version", version)
    else:
        table.add_row("vLLM", "[red]✗ Not installed[/red]")
        table.add_row("Install", "Run: aria vllm install")

    console.print(table)


@app.command("info")
def info_command():
    """Show vLLM configuration details.

    Displays the current vLLM engine configuration from .env.

    Example:
        ```bash
        aria vllm info
        ```
    """
    from aria.config.api import Vllm as VllmConfig

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan", width=28)
    table.add_column("Value", style="green")

    table.add_row(
        "GPU Memory Utilization",
        str(VllmConfig.gpu_memory_utilization),
    )
    table.add_row(
        "Max Model Length (chat)",
        str(VllmConfig.chat_context_size),
    )
    table.add_row(
        "Quantization",
        VllmConfig.quantization or "[dim]none[/dim]",
    )
    table.add_row(
        "Tensor Parallel Size",
        str(VllmConfig.tensor_parallel_size),
    )
    table.add_row("Dtype", VllmConfig.dtype)
    table.add_row(
        "Chat Context Size",
        str(VllmConfig.chat_context_size),
    )
    table.add_row(
        "VL Context Size",
        str(VllmConfig.vl_context_size),
    )
    table.add_row(
        "Chat Template",
        str(VllmConfig.chat_template_file) or "[dim]default[/dim]",
    )

    console.print("[bold]vLLM Configuration[/bold]\n")
    console.print(table)
