"""Vision CLI commands.

Provides PDF parsing and image analysis via the vision-language model.
The VL server is started on-demand if not already running. If the VL
model is not installed, commands return a helpful error with the
install command.
"""

import asyncio
import json
import sys

import typer

app = typer.Typer(
    help="PDF extraction and image analysis via the vision-language model.",
)


def _is_vision_model_available() -> bool:
    """Check if the VL model is available (configured and downloaded)."""
    try:
        from aria.config.models import Vision as VisionConfig

        if not VisionConfig.model_path:
            return False

        from pathlib import Path

        path = Path(VisionConfig.model_path)
        if path.is_absolute():
            return path.exists() and path.is_dir()

        # For HF repo IDs, check cache
        from huggingface_hub import try_to_load_from_cache

        cached = try_to_load_from_cache(VisionConfig.model_path, "config.json")
        return cached is not None and cached != "None"
    except Exception:
        return False


def _is_vl_server_running() -> bool:
    """Check if the VL server is responding."""
    try:
        import httpx

        from aria.config.models import Vision as VisionConfig

        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{VisionConfig.api_url}/models")
            return resp.status_code == 200
    except Exception:
        return False


def _start_vl_server() -> bool:
    """Start the VL server on-demand by launching vLLM directly."""
    try:
        import subprocess

        from aria.config.api import Vllm as VllmConfig
        from aria.config.models import Vision as VisionConfig

        if not VisionConfig.model_path:
            return False

        cmd = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            VisionConfig.model_path,
            "--port",
            str(VisionConfig.get_port()),
            "--host",
            "0.0.0.0",
            "--dtype",
            VllmConfig.dtype,
            "--gpu-memory-utilization",
            str(VllmConfig.gpu_memory_utilization),
            "--api-key",
            "sk-aria",
        ]

        if VllmConfig.quantization:
            cmd.extend(["--quantization", VllmConfig.quantization])

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for the server to become ready
        import time
        from urllib.error import URLError
        from urllib.request import urlopen

        deadline = time.time() + 300  # 5 min timeout for model loading
        while time.time() < deadline:
            try:
                url = f"http://0.0.0.0:{VisionConfig.get_port()}/health"
                with urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except (URLError, OSError):
                pass
            time.sleep(1.0)

        return False
    except Exception:
        return False


def _ensure_vl_ready() -> str | None:
    """Ensure VL model and server are ready. Returns error JSON or None."""
    if not _is_vision_model_available():
        from aria.config.models import Vision as VisionConfig

        return json.dumps(
            {
                "error": "vision_not_installed",
                "message": (
                    "Vision model not installed. "
                    "Download with the command below."
                ),
                "install_command": (f"aria models download --model vl"),
            }
        )

    if not _is_vl_server_running():
        if not _start_vl_server():
            return json.dumps(
                {
                    "error": "vision_server_failed",
                    "message": "Could not start the VL server.",
                }
            )

    return None


@app.command("pdf")
def pdf_cmd(
    file: str = typer.Argument(..., help="Path to the PDF file"),
    prompt: str = typer.Option(
        "", "--prompt", "-p", help="Custom extraction prompt"
    ),
):
    """Extract content from a PDF using the vision-language model.

    Starts the VL server on-demand if needed. If the model is not
    installed, returns the download command.
    """
    error = _ensure_vl_ready()
    if error:
        typer.echo(error)
        raise typer.Exit(1)

    from aria.config.models import Vision as VisionConfig
    from aria.tools.vision.functions import make_parse_pdf

    parse_pdf = make_parse_pdf(
        api_base=VisionConfig.api_url, model=VisionConfig.model
    )
    result = asyncio.run(
        parse_pdf(reason="CLI PDF extraction", file_path=file, prompt=prompt)
    )
    typer.echo(result)


@app.command("image")
def image_cmd(
    file: str = typer.Argument(..., help="Path to the image file"),
    prompt: str = typer.Option(
        "", "--prompt", "-p", help="Custom analysis prompt"
    ),
):
    """Analyze an image using the vision-language model.

    Starts the VL server on-demand if needed. If the model is not
    installed, returns the download command.
    """
    error = _ensure_vl_ready()
    if error:
        typer.echo(error)
        raise typer.Exit(1)

    from aria.config.models import Vision as VisionConfig
    from aria.tools.vision.functions import make_analyze_image

    analyze_image = make_analyze_image(
        api_base=VisionConfig.api_url, model=VisionConfig.model
    )
    result = asyncio.run(
        analyze_image(
            reason="CLI image analysis", file_path=file, prompt=prompt
        )
    )
    typer.echo(result)
