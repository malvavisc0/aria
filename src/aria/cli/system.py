"""System information commands for the Aria CLI.

This module provides commands to display system information, particularly
focused on GPU resources using the NVIDIA helpers. These commands are
useful for diagnosing system capabilities and resource availability.

Commands:
    gpu: Display detailed GPU information
    vram: Show VRAM usage per GPU
    nvlink: Check NVLink connectivity status
    context: Calculate safe context size based on available VRAM

Example:
    ```bash
    # Show GPU details
    aria system gpu

    # Check VRAM usage
    aria system vram

    # Check NVLink status
    aria system nvlink

    # Calculate safe context size
    aria system context --model-size 4096
    ```
"""

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aria.helpers.nvidia import (
    calculate_max_safe_context,
    check_nvidia_smi_available,
    detect_gpu_count,
    detect_gpus_with_details,
    detect_nvlink,
    get_free_vram_per_gpu,
    get_nvidia_smi_version,
    get_total_vram_mb,
)

app = typer.Typer(
    name="system",
    help="System information and GPU status commands.",
)

console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("gpu")
def show_gpu_info():
    """Display detailed GPU information.

    Shows comprehensive information about all detected NVIDIA GPUs:
    - GPU index and name
    - UUID
    - Memory (total, used, free)
    - Memory utilization percentage
    - Power (limit and current draw)
    - Temperature
    - Fan speed
    - Driver version
    - Display and compute mode status

    Example:
        ```bash
        aria system gpu
        ```
    """
    if not check_nvidia_smi_available():
        error_console.print(
            Panel(
                "[red]nvidia-smi not available. Ensure NVIDIA drivers are installed.[/red]",
                title="[bold]Error[/bold]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    gpus = detect_gpus_with_details()

    if not gpus:
        console.print(
            Panel(
                "[yellow]No NVIDIA GPUs detected.[/yellow]",
                title="[bold]GPU Status[/bold]",
                border_style="yellow",
            )
        )
        return

    # Summary table
    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Property", style="cyan", width=20)
    summary_table.add_column("Value", style="green")

    summary_table.add_row("GPU Count", str(len(gpus)))
    summary_table.add_row("Driver Version", gpus[0].driver_version if gpus else "N/A")
    summary_table.add_row("nvidia-smi Version", get_nvidia_smi_version())

    console.print(
        Panel(
            summary_table,
            title="[bold]GPU Summary[/bold]",
            border_style="cyan",
        )
    )
    console.print()

    # Detailed GPU table
    detail_table = Table(show_header=True, header_style="bold cyan")
    detail_table.add_column("Index", style="cyan", width=6)
    detail_table.add_column("Name", style="green")
    detail_table.add_column("Memory (MiB)", style="yellow")
    detail_table.add_column("Util %", style="magenta", width=8)
    detail_table.add_column("Power (W)", style="blue", width=10)
    detail_table.add_column("Temp (°C)", style="red", width=10)
    detail_table.add_column("Fan %", style="dim", width=8)

    for gpu in gpus:
        detail_table.add_row(
            str(gpu.index),
            gpu.name,
            f"{gpu.used_memory}/{gpu.total_memory} ({gpu.free_memory} free)",
            f"{gpu.memory_utilization:.1f}%",
            f"{gpu.power_draw}/{gpu.power_limit}",
            str(gpu.temperature),
            str(gpu.fan_speed),
        )

    console.print(
        Panel(detail_table, title="[bold]GPU Details[/bold]", border_style="cyan")
    )


@app.command("vram")
def show_vram():
    """Show VRAM usage per GPU.

    Displays VRAM information for each GPU:
    - Total VRAM
    - Used VRAM
    - Free VRAM
    - Utilization percentage

    Example:
        ```bash
        aria system vram
        ```
    """
    if not check_nvidia_smi_available():
        error_console.print(
            Panel(
                "[red]nvidia-smi not available. Ensure NVIDIA drivers are installed.[/red]",
                title="[bold]Error[/bold]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    total_vram = get_total_vram_mb()
    free_vram_list = get_free_vram_per_gpu()
    gpu_count = detect_gpu_count()

    if gpu_count == 0:
        console.print(
            Panel(
                "[yellow]No NVIDIA GPUs detected.[/yellow]",
                title="[bold]VRAM Status[/bold]",
                border_style="yellow",
            )
        )
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("GPU Index", style="cyan", width=10)
    table.add_column("Free VRAM (MiB)", style="green")
    table.add_column("Free VRAM (GiB)", style="green")

    for i, free_vram in enumerate(free_vram_list):
        table.add_row(
            str(i),
            str(free_vram),
            f"{free_vram / 1024:.2f}",
        )

    console.print(Panel(table, title="[bold]VRAM Usage[/bold]", border_style="cyan"))
    console.print()
    console.print(
        f"[dim]Total VRAM: {total_vram} MiB ({total_vram / 1024:.2f} GiB)[/dim]"
    )


@app.command("nvlink")
def check_nvlink():
    """Check NVLink connectivity status.

    Detects NVLink connections between GPUs and reports bonding status.
    NVLink provides high-bandwidth GPU-to-GPU interconnect.

    Example:
        ```bash
        aria system nvlink
        ```
    """
    if not check_nvidia_smi_available():
        error_console.print(
            Panel(
                "[red]nvidia-smi not available. Ensure NVIDIA drivers are installed.[/red]",
                title="[bold]Error[/bold]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    has_nvlink, bond_type = detect_nvlink()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    if has_nvlink:
        table.add_row("NVLink Detected", "[green]✓ Yes[/green]")
        if bond_type:
            table.add_row("Bond Type", bond_type)
        else:
            table.add_row("Bond Type", "Not bonded")
    else:
        table.add_row("NVLink Detected", "[red]✗ No[/red]")

    console.print(Panel(table, title="[bold]NVLink Status[/bold]", border_style="cyan"))


@app.command("context")
def calculate_context(
    model_size: Annotated[
        int,
        typer.Option(help="Model size in MiB (default: 0 for no model loaded)"),
    ] = 0,
    embedding: Annotated[
        bool,
        typer.Option(help="Calculate for embedding model (more conservative)"),
    ] = False,
):
    """Calculate safe context size based on available VRAM.

    Uses the tiered context calculation to determine the maximum safe
    context size given the current free VRAM and optional model size.

    Args:
        model_size: Size of the model in MiB (subtracted from available VRAM)
        embedding: Use embedding model tiers (more conservative limits)

    Example:
        ```bash
        # Calculate for LLM with no model loaded
        aria system context

        # Calculate with 4GB model
        aria system context --model-size 4096

        # Calculate for embedding model
        aria system context --embedding
        ```
    """
    if not check_nvidia_smi_available():
        error_console.print(
            Panel(
                "[red]nvidia-smi not available. Ensure NVIDIA drivers are installed.[/red]",
                title="[bold]Error[/bold]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    free_vram_list = get_free_vram_per_gpu()

    if not free_vram_list:
        console.print(
            Panel(
                "[yellow]No GPUs detected.[/yellow]",
                title="[bold]Context Calculation[/bold]",
                border_style="yellow",
            )
        )
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("GPU Index", style="cyan", width=10)
    table.add_column("Free VRAM (MiB)", style="green")
    table.add_column("Max Context (tokens)", style="yellow")

    total_context = 0
    for i, free_vram in enumerate(free_vram_list):
        context = calculate_max_safe_context(
            free_vram_mb=free_vram,
            model_size_mb=model_size,
            is_embedding_model=embedding,
        )
        table.add_row(str(i), str(free_vram), f"{context:,}")
        total_context = max(total_context, context)  # Use max for multi-GPU

    model_type = "Embedding" if embedding else "LLM"
    console.print(
        Panel(
            table,
            title="[bold]Safe Context Size Calculation[/bold]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(f"[dim]Model type: {model_type}[/dim]")
    console.print(f"[dim]Model size: {model_size} MiB[/dim]")
    console.print(f"[cyan]Recommended max context: {total_context:,} tokens[/cyan]")


@app.command("info")
def system_overview():
    """Display system overview with GPU and driver information.

    Shows a quick summary of:
    - NVIDIA driver availability
    - GPU count
    - Total VRAM
    - NVLink status

    Example:
        ```bash
        aria system info
        ```
    """
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    if check_nvidia_smi_available():
        table.add_row("NVIDIA Driver", "[green]✓ Available[/green]")
        table.add_row("nvidia-smi Version", get_nvidia_smi_version())
        table.add_row("GPU Count", str(detect_gpu_count()))

        total_vram = get_total_vram_mb()
        table.add_row("Total VRAM", f"{total_vram} MiB ({total_vram / 1024:.2f} GiB)")

        has_nvlink, bond_type = detect_nvlink()
        if has_nvlink:
            nvlink_status = f"[green]✓ Available[/green] ({bond_type or 'unbonded'})"
        else:
            nvlink_status = "[red]✗ Not available[/red]"
        table.add_row("NVLink", nvlink_status)
    else:
        table.add_row("NVIDIA Driver", "[red]✗ Not available[/red]")
        table.add_row("GPU Count", "0")

    console.print(
        Panel(table, title="[bold]System Overview[/bold]", border_style="cyan")
    )


if __name__ == "__main__":
    app()
