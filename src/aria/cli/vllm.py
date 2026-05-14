"""vLLM engine management commands for the Aria CLI.

This module provides commands to install, inspect, start, and stop the
vLLM inference engine. vLLM is installed as a Python package — no
separate binaries are needed.

Commands:
    install: Install vLLM with the appropriate hardware target
    status: Check vLLM installation status and version
    info: Show vLLM configuration details
    start: Start the vLLM inference server
    stop: Stop the vLLM inference server

Example:
    ```bash
    # Install vLLM with auto-detected hardware target
    aria vllm install

    # Check installation status
    aria vllm status

    # Show configuration
    aria vllm info

    # Start the vLLM server
    aria vllm start

    # Stop the vLLM server
    aria vllm stop
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

    Displays the current vLLM engine configuration from .env,
    organized by category.

    Example:
        ```bash
        aria vllm info
        ```
    """
    from aria.config.api import Vllm as VllmConfig

    # --- Engine ---
    engine = Table(show_header=True, header_style="bold cyan")
    engine.add_column("Setting", style="cyan", width=28)
    engine.add_column("Value", style="green")

    engine.add_row("Chat Context Size", str(VllmConfig.chat_context_size))
    engine.add_row("Max Output Tokens", str(VllmConfig.max_tokens))
    engine.add_row(
        "GPU Memory Utilization",
        (
            str(VllmConfig.gpu_memory_utilization)
            if VllmConfig.gpu_memory_utilization is not None
            else "[dim]auto[/dim]"
        ),
    )
    engine.add_row(
        "Quantization",
        VllmConfig.quantization or "[dim]none[/dim]",
    )
    engine.add_row("Dtype", VllmConfig.dtype)
    engine.add_row("KV Cache Dtype", VllmConfig.kv_cache_dtype)
    engine.add_row("Tensor Parallel Size", str(VllmConfig.tensor_parallel_size))
    engine.add_row("Data Parallel Size", str(VllmConfig.data_parallel_size))
    engine.add_row(
        "Expert Parallel",
        "[green]✓[/green]" if VllmConfig.expert_parallel else "[dim]off[/dim]",
    )
    engine.add_row(
        "Prefix Caching",
        "[green]✓[/green]" if VllmConfig.prefix_caching else "[dim]off[/dim]",
    )
    engine.add_row(
        "Vision Enabled",
        "[green]✓[/green]" if VllmConfig.vision_enabled else "[dim]off[/dim]",
    )
    engine.add_row(
        "Tool Call Parser",
        VllmConfig.tool_call_parser or "[dim]none[/dim]",
    )
    engine.add_row(
        "Reasoning Parser",
        VllmConfig.reasoning_parser or "[dim]none[/dim]",
    )
    engine.add_row(
        "Chat Template",
        str(VllmConfig.chat_template_file) or "[dim]default[/dim]",
    )
    engine.add_row(
        "Chat Template Kwargs",
        VllmConfig.chat_template_kwargs or "[dim]none[/dim]",
    )

    console.print("[bold]Engine[/bold]\n")
    console.print(engine)

    # --- KV Cache Offloading ---
    offload = Table(show_header=True, header_style="bold cyan")
    offload.add_column("Setting", style="cyan", width=28)
    offload.add_column("Value", style="green")

    offload.add_row("Offload Mode", VllmConfig.kv_offload_mode)
    offload.add_row(
        "Offload Size (GiB)",
        (
            str(VllmConfig.kv_offloading_size_gb)
            if VllmConfig.kv_offloading_size_gb is not None
            else "[dim]auto[/dim]"
        ),
    )
    offload.add_row("Offload Backend", VllmConfig.kv_offloading_backend)

    console.print("\n[bold]KV Cache Offloading[/bold]\n")
    console.print(offload)

    # --- Sampling ---
    sampling = Table(show_header=True, header_style="bold cyan")
    sampling.add_column("Setting", style="cyan", width=28)
    sampling.add_column("Value", style="green")

    sampling.add_row("Temperature", str(VllmConfig.temperature))
    sampling.add_row("Top P", str(VllmConfig.top_p))
    sampling.add_row("Top K", str(VllmConfig.top_k))
    sampling.add_row("Min P", str(VllmConfig.min_p))
    sampling.add_row("Repetition Penalty", str(VllmConfig.repetition_penalty))
    sampling.add_row("Seed", str(VllmConfig.seed))

    console.print("\n[bold]Sampling[/bold]\n")
    console.print(sampling)


@app.command("start")
def start_command():
    """Start the vLLM inference server.

    Ensures required directories exist, then starts the vLLM server
    and waits for it to become healthy.

    Example:
        ```bash
        aria vllm start
        ```
    """
    from urllib.error import URLError
    from urllib.request import urlopen

    from aria.config.folders import Debug as DebugConfig
    from aria.config.models import Chat
    from aria.server.vllm import VllmServerManager

    # Ensure log directory exists
    DebugConfig.path.mkdir(parents=True, exist_ok=True)

    # Check if already running
    port = Chat.get_port()
    try:
        with urlopen(f"http://localhost:{port}/health", timeout=3) as resp:
            if resp.status == 200:
                console.print(
                    f"[yellow]vLLM server is already running[/yellow] (port {port})"
                )
                return
    except (URLError, OSError):
        pass

    console.print("[dim]Starting vLLM server...[/dim]")
    try:
        vllm = VllmServerManager()
        vllm.start_all()
        console.print(f"[green]✓[/green] vLLM server started on port {port}")
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to start vLLM: {e}")
        raise typer.Exit(1)


@app.command("stop")
def stop_command():
    """Stop the vLLM inference server.

    Gracefully stops all running vLLM server processes, including
    orphaned processes not tracked by the PID file.

    Example:
        ```bash
        aria vllm stop
        ```
    """
    from aria.server.vllm import VllmServerManager

    vllm = VllmServerManager()

    if not vllm._pids:
        # Double-check for orphaned processes
        orphans = VllmServerManager._find_orphan_pids()
        if not orphans:
            console.print("[yellow]vLLM server is not running[/yellow]")
            return

    console.print("[dim]Stopping vLLM server...[/dim]")
    try:
        vllm.stop_all()
        console.print("[green]✓[/green] vLLM server stopped")
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to stop vLLM: {e}")
        raise typer.Exit(1)
