"""Finetune and quantize CLI commands.

Commands:
    recommend — suggest QLoRA parameters based on hardware + model
    run       — full pipeline: QLoRA SFT → merge → GPTQ Int4
    quantize  — quantization only (for an already-merged model)
    push      — publish a quantized model to HuggingFace Hub

Example:
    ```bash
    aria finetune recommend --model OrionLLM/GRM-2.6-Plus

    aria finetune run \\
        --model OrionLLM/GRM-2.6-Plus \\
        --dataset teknium/OpenHermes-2.5 \\
        --run-name my-run

    aria finetune quantize \\
        --model data/models/my-run/merged \\
        --output data/models/my-run/gptq-int4

    aria finetune push \\
        --model data/models/my-run/gptq-int4 \\
        --repo-id myorg/my-model-gptq-int4
    ```
"""

import platform
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

app = typer.Typer(
    name="finetune",
    help="Finetune and quantize models for instruction following.",
    no_args_is_help=True,
)
console = Console(width=200)


@app.command("recommend")
def recommend_cmd(
    model: Annotated[
        str, typer.Option("--model", help="HF repo ID of the model.")
    ],
    token: Annotated[
        Optional[str],
        typer.Option(
            "--token", help="HF API token. Falls back to HUGGINGFACE_TOKEN."
        ),
    ] = None,
) -> None:
    """Suggest QLoRA fine-tuning parameters for your hardware and model.

    Detects GPU VRAM, system RAM, and BF16 support, fetches model metadata
    from HuggingFace Hub, and prints recommended hyper-parameters with a
    ready-to-copy ``aria finetune run`` command.

    Example:
        ```bash
        aria finetune recommend --model OrionLLM/GRM-2.6-Plus
        aria finetune recommend --model meta-llama/Llama-3.3-70B-Instruct
        ```
    """
    import logging

    import torch

    for _name in ("httpcore", "httpx", "huggingface_hub", "urllib3"):
        logging.getLogger(_name).setLevel(logging.WARNING)

    from aria.helpers.memory import detect_system_ram
    from aria.helpers.nvidia import (
        check_nvidia_smi_available,
        detect_gpus_with_details,
        get_total_vram_mb,
    )
    from aria.scripts.finetune import fetch_model_info, recommend

    # ── Detect hardware ────────────────────────────────────────────────
    gpus = detect_gpus_with_details() if check_nvidia_smi_available() else []
    total_vram_mib = get_total_vram_mb() if gpus else 0
    total_ram_mb, _ = detect_system_ram()
    bf16 = (
        torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False
    )

    # ── Hardware table ─────────────────────────────────────────────────
    hw_table = Table(
        title="Hardware", show_header=False, title_style="bold cyan"
    )
    hw_table.add_column("Property", style="cyan", width=10)
    hw_table.add_column("Value", style="green")

    if gpus:
        gpu = gpus[0]
        hw_table.add_row(
            "GPU", f"{gpu.name} ({gpu.total_memory / 1024:.1f} GiB)"
        )
        if len(gpus) > 1:
            hw_table.add_row("GPUs", str(len(gpus)))
    else:
        hw_table.add_row("GPU", "[red]None detected[/red]")

    hw_table.add_row("RAM", f"{total_ram_mb / 1024:.1f} GiB")
    hw_table.add_row("BF16", "✓" if bf16 else "✗")
    hw_table.add_row("OS", platform.system())
    console.print(hw_table)
    console.print()

    if not gpus:
        console.print(
            "[red]No NVIDIA GPU detected. QLoRA fine-tuning requires a CUDA GPU.[/red]"
        )
        raise typer.Exit(1)

    # ── Fetch model info ───────────────────────────────────────────────
    console.print(f"[cyan]Fetching model info: {model}[/cyan]")
    try:
        model_info = fetch_model_info(model, token=token)
    except Exception as exc:
        console.print(f"[red]Failed to fetch model info: {exc}[/red]")
        raise typer.Exit(1)

    model_table = Table(
        title=f"Model: {model}", show_header=False, title_style="bold cyan"
    )
    model_table.add_column("Property", style="cyan", width=14)
    model_table.add_column("Value", style="green")
    model_table.add_row("Parameters", f"{model_info.params_b:.1f}B")
    model_table.add_row(
        "Architecture", ", ".join(model_info.architectures) or "unknown"
    )
    model_table.add_row("Type", model_info.model_type)
    if model_info.hidden_size:
        model_table.add_row("Hidden size", str(model_info.hidden_size))
    if model_info.num_layers:
        model_table.add_row("Layers", str(model_info.num_layers))
    console.print(model_table)
    console.print()

    # ── Compute recommendation ─────────────────────────────────────────
    rec = recommend(
        model_info=model_info,
        vram_mib=total_vram_mib,
        ram_mib=total_ram_mb,
        bf16_supported=bf16,
    )

    # ── Recommendation table ───────────────────────────────────────────
    rec_table = Table(
        title="Recommended Parameters",
        show_header=False,
        title_style="bold cyan",
    )
    rec_table.add_column("Parameter", style="cyan", width=30)
    rec_table.add_column("Value", style="bold green")
    rec_table.add_row("lora_rank", str(rec.lora_rank))
    rec_table.add_row("lora_alpha", str(rec.lora_alpha))
    rec_table.add_row("max_seq_len", str(rec.max_seq_len))
    rec_table.add_row("batch_size", str(rec.batch_size))
    rec_table.add_row(
        "gradient_accumulation", str(rec.gradient_accumulation_steps)
    )
    rec_table.add_row("learning_rate", f"{rec.learning_rate:.0e}")
    rec_table.add_row("epochs", str(rec.epochs))
    if rec.max_memory:
        mem_str = ", ".join(f"{k}: {v}" for k, v in rec.max_memory.items())
        rec_table.add_row("max_memory", mem_str)
    else:
        rec_table.add_row("max_memory", "auto")
    console.print(rec_table)
    console.print()

    # ── Reasoning ──────────────────────────────────────────────────────
    console.print("[bold]  Reasoning:[/bold]")
    for reason in rec.reasoning:
        console.print(f"  • {reason}")
    console.print()

    # ── Copy-paste command ─────────────────────────────────────────────
    cmd_lines = [
        "aria finetune run \\",
        f"  --model {model} \\",
        "  --dataset <DATASET> \\",
        "  --run-name <RUN_NAME> \\",
        f"  --lora-rank {rec.lora_rank} \\",
        f"  --max-seq-len {rec.max_seq_len} \\",
        f"  --epochs {rec.epochs} \\",
        f"  --batch-size {rec.batch_size} \\",
        f"  --grad-accum {rec.gradient_accumulation_steps} \\",
        f"  --learning-rate {rec.learning_rate:.0e}",
    ]
    console.print("[bold]Copy-paste command:[/bold]")
    for line in cmd_lines:
        console.print(f"  {line}", style="dim")


@app.command("run")
def run(
    model: Annotated[
        str, typer.Option("--model", help="Base model HF repo ID.")
    ],
    dataset: Annotated[
        str,
        typer.Option(
            "--dataset",
            help="HF dataset repo ID(s), comma-separated for multiple.",
        ),
    ],
    run_name: Annotated[
        str,
        typer.Option(
            "--run-name",
            help="Run name; used as output subdirectory under data/models/.",
        ),
    ],
    lora_rank: Annotated[int, typer.Option(help="LoRA rank.")] = 32,
    lora_alpha: Annotated[
        Optional[int],
        typer.Option(help="LoRA alpha. Defaults to 2x lora_rank."),
    ] = None,
    max_seq_len: Annotated[
        int, typer.Option(help="Max training sequence length in tokens.")
    ] = 2048,
    epochs: Annotated[int, typer.Option(help="Training epochs.")] = 1,
    batch_size: Annotated[
        int, typer.Option(help="Per-device batch size.")
    ] = 2,
    grad_accum: Annotated[
        int, typer.Option(help="Gradient accumulation steps.")
    ] = 8,
    learning_rate: Annotated[
        float, typer.Option(help="Learning rate.")
    ] = 2e-4,
    max_samples: Annotated[
        Optional[int],
        typer.Option(help="Limit dataset samples (None = full dataset)."),
    ] = None,
    clean: Annotated[
        bool,
        typer.Option("--clean", help="Enable dataset cleaning pipeline."),
    ] = False,
    dedup: Annotated[
        bool,
        typer.Option("--dedup", help="Remove exact duplicate texts."),
    ] = False,
    min_tokens: Annotated[
        int,
        typer.Option("--min-tokens", help="Min token count per sample."),
    ] = 10,
    max_tokens: Annotated[
        Optional[int],
        typer.Option("--max-tokens", help="Max token count per sample."),
    ] = None,
    languages: Annotated[
        Optional[str],
        typer.Option(
            "--languages",
            help="Comma-separated language codes to keep (e.g. 'en').",
        ),
    ] = None,
    max_special_ratio: Annotated[
        float,
        typer.Option(
            "--max-special-ratio", help="Max special character ratio (0-1)."
        ),
    ] = 0.3,
    skip_finetune: Annotated[
        bool,
        typer.Option(
            "--skip-finetune",
            help="Skip SFT, go straight to merge + quantize.",
        ),
    ] = False,
    skip_quantize: Annotated[
        bool,
        typer.Option(
            "--skip-quantize", help="Stop after merge, skip quantization."
        ),
    ] = False,
    gptq_bits: Annotated[
        int, typer.Option(help="GPTQ quantization bits.")
    ] = 4,
    gptq_group_size: Annotated[
        int, typer.Option(help="GPTQ group size.")
    ] = 128,
    calibration: Annotated[
        str,
        typer.Option(
            help="Calibration dataset: 'wikitext2' or path to JSONL."
        ),
    ] = "wikitext2",
) -> None:
    """Full pipeline: QLoRA SFT → merge LoRA → GPTQ quantize.

    Outputs are written to DATA_FOLDER/models/<run-name>/:
      adapter/   — LoRA adapter weights
      merged/    — fp16 merged model
      gptq-int4/ — GPTQ Int4 quantized model (vLLM-ready)
    """
    from aria.config.folders import Data
    from aria.scripts.finetune import (
        QuantizeConfig,
        TrainConfig,
        merge_adapter,
        quantize,
        train,
    )

    # Parse comma-separated dataset IDs
    dataset_ids = [d.strip() for d in dataset.split(",") if d.strip()]
    lang_list = (
        [l.strip() for l in languages.split(",") if l.strip()]
        if languages
        else None
    )

    base_dir = Data.path / "models" / run_name
    adapter_dir = base_dir / "adapter"
    merged_dir = base_dir / "merged"
    gptq_dir = base_dir / f"gptq-int{gptq_bits}"

    # ── Phase 1: QLoRA SFT ──────────────────────────────────────────────
    if not skip_finetune:
        cfg = TrainConfig(
            base_model=model,
            datasets=dataset_ids,
            run_name=run_name,
            output_dir=base_dir,
            lora_rank=lora_rank,
            lora_alpha=lora_alpha if lora_alpha is not None else lora_rank * 2,
            max_seq_len=max_seq_len,
            num_epochs=epochs,
            per_device_batch_size=batch_size,
            gradient_accumulation_steps=grad_accum,
            learning_rate=learning_rate,
            max_samples=max_samples,
            clean=clean,
            dedup=dedup,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            languages=lang_list,
            max_special_ratio=max_special_ratio,
        )
        train(cfg)
    else:
        if not adapter_dir.exists():
            console.print(
                f"[red]--skip-finetune set but adapter not found: {adapter_dir}[/red]"
            )
            raise typer.Exit(1)
        console.print(
            f"[yellow]Skipping SFT — using existing adapter: {adapter_dir}[/yellow]"
        )

    # ── Phase 2: Merge ──────────────────────────────────────────────────
    merge_adapter(model, adapter_dir, merged_dir)

    if skip_quantize:
        console.print(
            f"[yellow]Skipping quantization. Merged model: {merged_dir}[/yellow]"
        )
        return

    # ── Phase 3: GPTQ Int4 ──────────────────────────────────────────────
    quantize(
        merged_dir,
        gptq_dir,
        QuantizeConfig(
            bits=gptq_bits,
            group_size=gptq_group_size,
            calibration_dataset=calibration,
        ),
    )

    console.print("\n[bold green]Pipeline complete.[/bold green]")
    console.print(f"  Adapter     : {adapter_dir}")
    console.print(f"  Merged      : {merged_dir}")
    console.print(f"  GPTQ Int{gptq_bits}  : {gptq_dir}")
    console.print(
        f"\n[dim]To use:[/dim]\n"
        f"  CHAT_MODEL_PATH = {gptq_dir}\n"
        f"  ARIA_VLLM_QUANT = gptq_marlin"
    )


@app.command("quantize")
def quantize_cmd(
    merged_model: Annotated[
        Path,
        typer.Option("--model", help="Path to merged fp16 model directory."),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output", help="Output directory for the quantized model."
        ),
    ],
    bits: Annotated[int, typer.Option(help="Quantization bits.")] = 4,
    group_size: Annotated[int, typer.Option(help="GPTQ group size.")] = 128,
    calibration: Annotated[
        str, typer.Option(help="'wikitext2' or path to JSONL.")
    ] = "wikitext2",
    n_calibration_samples: Annotated[
        int, typer.Option(help="Number of calibration samples.")
    ] = 128,
) -> None:
    """Quantize an already-merged model to GPTQ Int4."""
    from aria.scripts.finetune import QuantizeConfig, quantize

    cfg = QuantizeConfig(
        bits=bits,
        group_size=group_size,
        calibration_dataset=calibration,
        n_calibration_samples=n_calibration_samples,
    )
    quantize(merged_model, output, cfg)
    console.print(
        f"\n[dim]Set in .env:[/dim]\n  CHAT_MODEL_PATH = {output}\n  ARIA_VLLM_QUANT = gptq_marlin"
    )


@app.command("push")
def push(
    model: Annotated[
        Path,
        typer.Option(
            "--model", help="Local path to the quantized model directory."
        ),
    ],
    repo_id: Annotated[
        str,
        typer.Option(
            "--repo-id",
            help="HuggingFace repo ID (e.g. 'myorg/my-model-gptq-int4').",
        ),
    ],
    private: Annotated[
        bool, typer.Option("--private", help="Create repo as private.")
    ] = False,
    token: Annotated[
        Optional[str],
        typer.Option(
            "--token",
            help="HF API token. Falls back to HUGGINGFACE_API_KEY env var.",
        ),
    ] = None,
    message: Annotated[
        str, typer.Option("--message", help="Commit message.")
    ] = "Upload GPTQ quantized model",
) -> None:
    """Publish a quantized model to HuggingFace Hub.

    Creates the repository if it does not exist, then uploads the full
    model directory (safetensors + tokenizer + config).

    Example:
        ```bash
        aria finetune push \\
            --model data/models/my-run/gptq-int4 \\
            --repo-id myorg/my-model-gptq-int4
        ```
    """
    from aria.scripts.finetune import push_to_hub

    if not model.exists():
        console.print(f"[red]Model directory not found: {model}[/red]")
        raise typer.Exit(1)

    url = push_to_hub(
        model_path=model,
        repo_id=repo_id,
        private=private,
        token=token,
        commit_message=message,
    )
    console.print(f"\n[bold]Model available at:[/bold] {url}")
