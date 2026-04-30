"""Vision CLI commands.

Provides PDF parsing and image analysis via the vision-language model.
The VL server is started on-demand if not already running. If the VL
model is not installed, commands return a helpful error with the
install command.
"""

import asyncio
import json
from pathlib import Path

import typer

app = typer.Typer(
    help="PDF extraction and image analysis via the vision-language model.",
)


def _is_vision_model_available() -> bool:
    """Check if the VL model files exist on disk."""
    try:
        from aria.config.models import Vision as VisionConfig

        if not VisionConfig.repo_id or not VisionConfig.filename:
            return False

        from aria.config.api import LlamaCpp
        from aria.config.folders import Data

        model_path = LlamaCpp.models_path / VisionConfig.filename
        return model_path.exists()
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
    """Start the VL server on-demand by launching the run-model script."""
    try:
        import subprocess

        from aria.config.api import LlamaCpp as LlamaCppConfig
        from aria.config.models import Vision as VisionConfig
        from aria.scripts.gguf import get_model_path

        model_path = get_model_path(
            VisionConfig.filename, LlamaCppConfig.models_path
        )
        if model_path is None:
            return False

        mmproj_path = None
        if VisionConfig.mmproj_filename:
            mmproj_path = get_model_path(
                VisionConfig.mmproj_filename, LlamaCppConfig.models_path
            )

        from aria.server.llama import LlamaCppServerManager

        manager = LlamaCppServerManager()
        cmd = manager._build_run_model_cmd(
            model_path=model_path,
            context_size=LlamaCppConfig.vl_context_size,
            port=VisionConfig.get_port(),
            role="vl",
            mmproj_path=mmproj_path,
        )
        env = manager._get_env_for_run_model()

        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for the server to become ready
        return manager._wait_for_ready(
            "0.0.0.0", VisionConfig.get_port(), timeout=60.0
        )
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
                "install_command": (
                    f"aria models download "
                    f"--repo {VisionConfig.repo_id} "
                    f"--filename {VisionConfig.filename}"
                ),
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
