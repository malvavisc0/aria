"""Fine-tuning and GPTQ quantization pipeline for instruction-following models.

Three-phase pipeline:
    1. QLoRA SFT  — fine-tune a 4-bit quantized base model with LoRA adapters
    2. Merge      — merge LoRA weights into base model (fp16 safetensors)
    3. Quantize   — compress merged model to GPTQ Int4 via GPTQModel

Optionally publish the quantized model to HuggingFace Hub.

All outputs default to ``DATA_FOLDER/models/``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import torch
from loguru import logger
from rich.console import Console

console = Console(width=200)


# ── Configuration ─────────────────────────────────────────────────────────


@dataclass
class TrainConfig:
    """QLoRA SFT phase configuration.

    Core fields (``base_model``, ``datasets``, ``run_name``) are required;
    training hyper-parameters have sensible defaults.
    """

    base_model: str  # HF repo ID of the base model
    datasets: list[str] = field(
        default_factory=list
    )  # one or more HF dataset IDs
    run_name: str = ""  # output subdirectory name under data/models/
    output_dir: Optional[Path] = (
        None  # defaults to Data.path/models/<run_name>
    )
    lora_rank: int = 32
    lora_alpha: int = 64
    lora_dropout: float = 0.05
    max_seq_len: int = 2048
    num_epochs: int = 1
    per_device_batch_size: int = 2
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.03
    max_samples: Optional[int] = None  # None = full dataset
    max_memory: Optional[dict] = None  # e.g. {0: "29GiB", "cpu": "64GiB"}
    # Dataset cleaning
    clean: bool = False  # enable cleaning pipeline
    dedup: bool = False  # remove exact duplicate texts
    min_tokens: int = 10  # drop samples shorter than this
    max_tokens: Optional[int] = (
        None  # drop samples longer (defaults to max_seq_len)
    )
    languages: Optional[list[str]] = None  # e.g. ["en"] — requires langdetect
    max_special_ratio: float = 0.3  # drop if special chars exceed this ratio


@dataclass
class QuantizeConfig:
    """GPTQ quantization phase configuration."""

    bits: int = 4
    group_size: int = 128
    desc_act: bool = False
    calibration_dataset: str = (
        "wikitext2"  # or path to local JSONL {"text": "..."}
    )
    n_calibration_samples: int = 128
    calibration_seq_len: int = 2048


# ── Phase 1: QLoRA SFT ────────────────────────────────────────────────────


def _silence_debug_loggers() -> None:
    """Suppress noisy DEBUG logs from HF/HTTP libraries."""
    for name in (
        "httpcore",
        "httpx",
        "datasets",
        "torchao",
        "filelock",
        "fsspec",
        "huggingface_hub",
        "bitsandbytes",
        "urllib3",
        "gptqmodel",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


def clean_dataset(
    dataset,
    tokenizer,
    dedup: bool = False,
    min_tokens: int = 10,
    max_tokens: int = 2048,
    languages: Optional[list[str]] = None,
    max_special_ratio: float = 0.3,
):
    """Apply cleaning steps to a HuggingFace dataset.

    Steps are applied in order: whitespace cleanup → special char filter →
    length filter → language filter → deduplication.

    Args:
        dataset: A HF ``Dataset`` with a ``text`` column.
        tokenizer: Model tokenizer for token-count filtering.
        dedup: Remove exact duplicate texts.
        min_tokens: Minimum token count (shorter samples dropped).
        max_tokens: Maximum token count (longer samples dropped).
        languages: If set, keep only samples in these language codes.
        max_special_ratio: Drop samples where non-alphanumeric characters
            exceed this fraction of total length.

    Returns:
        Cleaned dataset.
    """
    import re

    n_start = len(dataset)

    # ── 1. Whitespace normalization ────────────────────────────────────
    def _clean_whitespace(example: dict) -> dict:
        text = example["text"]
        # collapse 3+ consecutive newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # strip trailing whitespace per line
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        # strip leading/trailing whitespace overall
        text = text.strip()
        return {"text": text}

    dataset = dataset.map(_clean_whitespace)

    # ── 2. Special character ratio filter ──────────────────────────────
    def _special_char_ok(example: dict) -> bool:
        text = example["text"]
        if not text:
            return False
        alpha = sum(1 for c in text if c.isalnum() or c.isspace())
        ratio = 1.0 - (alpha / len(text))
        return ratio <= max_special_ratio

    n_before = len(dataset)
    dataset = dataset.filter(_special_char_ok)
    if len(dataset) != n_before:
        logger.debug(
            "Cleaning: dropped {} samples with high special-char ratio",
            n_before - len(dataset),
        )

    # ── 3. Token length filter ─────────────────────────────────────────
    def _token_length_ok(example: dict) -> bool:
        ids = tokenizer(example["text"], return_length=True)
        length = (
            ids["length"][0]
            if isinstance(ids["length"], list)
            else ids["length"]
        )
        return min_tokens <= length <= max_tokens

    n_before = len(dataset)
    dataset = dataset.filter(_token_length_ok)
    if len(dataset) != n_before:
        logger.debug(
            "Cleaning: dropped {} samples outside token range [{}, {}]",
            n_before - len(dataset),
            min_tokens,
            max_tokens,
        )

    # ── 4. Language filter (optional) ──────────────────────────────────
    if languages:
        try:
            from langdetect import detect as detect_lang

            def _lang_ok(example: dict) -> bool:
                try:
                    return detect_lang(example["text"]) in languages
                except Exception:
                    return False

            n_before = len(dataset)
            dataset = dataset.filter(_lang_ok)
            if len(dataset) != n_before:
                logger.debug(
                    "Cleaning: dropped {} non-{} samples",
                    n_before - len(dataset),
                    ",".join(languages),
                )
        except ImportError:
            console.print(
                "[yellow]⚠ langdetect not installed — skipping language filter[/yellow]"
            )

    # ── 5. Deduplication ──────────────────────────────────────────────
    if dedup:
        seen: set[int] = set()

        def _not_dup(example: dict) -> bool:
            h = hash(example["text"])
            if h in seen:
                return False
            seen.add(h)
            return True

        n_before = len(dataset)
        dataset = dataset.filter(_not_dup)
        if len(dataset) != n_before:
            logger.debug(
                "Cleaning: dropped {} duplicate samples",
                n_before - len(dataset),
            )

    n_end = len(dataset)
    if n_start != n_end:
        console.print(
            f"[cyan]Cleaning: {n_start} → {n_end} samples "
            f"({n_start - n_end} removed)[/cyan]"
        )
    else:
        console.print("[cyan]Cleaning: no samples removed[/cyan]")

    return dataset


def train(config: TrainConfig) -> Path:
    """Run QLoRA supervised fine-tuning.

    Loads the base model in 4-bit (NF4), applies LoRA adapters targeting all
    attention + MLP projection layers, trains with SFTTrainer, and saves
    the adapter weights.

    Returns:
        Path to the saved LoRA adapter directory.
    """
    import datasets as hf_datasets
    from peft import (
        LoraConfig,
        get_peft_model,
        prepare_model_for_kbit_training,
    )
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from trl import SFTConfig, SFTTrainer

    _silence_debug_loggers()

    from aria.config.folders import Data
    from aria.config.huggingface import HuggingFace

    hf_token = HuggingFace.token
    out = config.output_dir or (Data.path / "models" / config.run_name)
    adapter_dir = out / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Loading tokenizer: {config.base_model}[/cyan]")
    tokenizer = AutoTokenizer.from_pretrained(
        config.base_model, trust_remote_code=True, token=hf_token
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    console.print("[cyan]Loading base model in 4-bit NF4 (QLoRA)...[/cyan]")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model_kwargs: dict = dict(
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
        token=hf_token,
    )
    if config.max_memory is not None:
        model_kwargs["max_memory"] = config.max_memory
    model = AutoModelForCausalLM.from_pretrained(
        config.base_model, **model_kwargs
    )
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=False  # handled by SFTConfig
    )

    lora_cfg = LoraConfig(
        r=config.lora_rank,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    # ── Load and format datasets ───────────────────────────────────────
    def _format(example: dict) -> dict:
        """Convert sharegpt or xlam format to chat-templated text."""
        convs = example.get("conversations") or []
        if convs:
            messages = [
                {
                    "role": (
                        "user"
                        if turn["from"] in ("human", "user")
                        else "assistant"
                    ),
                    "content": turn["value"],
                }
                for turn in convs
            ]
        elif "messages" in example and example["messages"]:
            # Qwen3 / OpenAI messages format (role + content dicts) — pass through directly
            messages = example["messages"]
        elif "query" in example:
            user_content = example["query"]
            if example.get("tools"):
                user_content = f"Tools: {example['tools']}\n\n{user_content}"
            messages = [{"role": "user", "content": user_content}]
            if example.get("answers"):
                messages.append(
                    {"role": "assistant", "content": str(example["answers"])}
                )
        else:
            messages = []

        if not messages:
            return {"text": ""}

        return {
            "text": tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        }

    formatted_parts: list = []
    for ds_id in config.datasets:
        console.print(f"[cyan]Loading dataset: {ds_id}[/cyan]")
        raw = hf_datasets.load_dataset(ds_id, split="train", token=hf_token)
        formatted = raw.map(_format, remove_columns=raw.column_names)
        n_before = len(formatted)
        formatted = formatted.filter(lambda x: len(x["text"]) > 0)
        n_after = len(formatted)
        if n_before != n_after:
            logger.debug(
                "{}: dropped {} empty examples",
                ds_id,
                n_before - n_after,
            )
        formatted_parts.append(formatted)
        console.print(f"  [green]✓[/green] {ds_id}: {len(formatted)} samples")

    if len(formatted_parts) == 1:
        dataset = formatted_parts[0]
    else:
        from datasets import concatenate_datasets

        dataset = concatenate_datasets(formatted_parts)
        dataset = dataset.shuffle(seed=42)
        console.print(
            f"[cyan]Concatenated {len(formatted_parts)} datasets → "
            f"{len(dataset)} total samples[/cyan]"
        )

    if config.max_samples:
        dataset = dataset.select(range(min(config.max_samples, len(dataset))))

    # ── Dataset cleaning ───────────────────────────────────────────────
    if config.clean:
        dataset = clean_dataset(
            dataset,
            tokenizer=tokenizer,
            dedup=config.dedup,
            min_tokens=config.min_tokens,
            max_tokens=config.max_tokens or config.max_seq_len,
            languages=config.languages,
            max_special_ratio=config.max_special_ratio,
        )

    _total_steps = max(
        1,
        len(dataset)
        * config.num_epochs
        // (config.per_device_batch_size * config.gradient_accumulation_steps),
    )
    _warmup_steps = max(1, int(_total_steps * config.warmup_ratio))

    args = SFTConfig(
        output_dir=str(out / "checkpoints"),
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.per_device_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_steps=_warmup_steps,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,  # SFTConfig default; kept explicit
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
        run_name=config.run_name,
        train_sampling_strategy="group_by_length",
        dataloader_num_workers=4,
        dataset_text_field="text",
        max_length=config.max_seq_len,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=args,
    )

    console.print("[green]Training started...[/green]")
    trainer.train()
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    logger.info("Adapter saved to {}", adapter_dir)
    console.print(f"[green]✓ Adapter → {adapter_dir}[/green]")
    return adapter_dir


# ── Phase 2: Merge LoRA ───────────────────────────────────────────────────


def merge_adapter(base_model: str, adapter_path: Path, output: Path) -> Path:
    """Merge LoRA adapter into the base model as fp16 safetensors.

    Returns:
        Path to the merged model directory.
    """
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from aria.config.huggingface import HuggingFace

    hf_token = HuggingFace.token
    output.mkdir(parents=True, exist_ok=True)
    console.print(
        f"[cyan]Loading base model on CPU for merge: {base_model}[/cyan]"
    )
    tokenizer = AutoTokenizer.from_pretrained(
        str(adapter_path), trust_remote_code=True, token=hf_token
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
        token=hf_token,
    )
    console.print("[cyan]Merging LoRA weights...[/cyan]")
    model = PeftModel.from_pretrained(model, str(adapter_path))
    model = model.merge_and_unload()
    model.save_pretrained(str(output), safe_serialization=True)
    tokenizer.save_pretrained(str(output))
    logger.info("Merged model saved to {}", output)
    console.print(f"[green]✓ Merged → {output}[/green]")
    return output


# ── Phase 3: GPTQ Int4 Quantization ──────────────────────────────────────


def _get_calibration_data(
    tokenizer,
    dataset_name: str,
    n_samples: int,
    seq_len: int,
) -> list[dict]:
    """Build tokenized calibration samples for GPTQ quantization."""
    import datasets as hf_datasets

    if dataset_name == "wikitext2":
        data = hf_datasets.load_dataset(
            "wikitext", "wikitext-2-raw-v1", split="train"
        )
        texts = [row["text"] for row in data if len(row["text"]) > 50]
    else:
        p = Path(dataset_name)
        texts = [
            json.loads(line)["text"]
            for line in p.read_text().splitlines()
            if line.strip()
        ]

    samples = []
    for text in texts[:n_samples]:
        enc = tokenizer(
            text,
            return_tensors="pt",
            max_length=seq_len,
            truncation=True,
            padding=False,
        )
        samples.append({k: v.squeeze(0) for k, v in enc.items()})
    return samples


def quantize(model_path: Path, output: Path, config: QuantizeConfig) -> Path:
    """Quantize a merged fp16 model to GPTQ Int4 using GPTQModel.

    Returns:
        Path to the quantized model directory (vLLM-ready).
    """
    from gptqmodel import GPTQModel
    from gptqmodel import QuantizeConfig as GptqCfg
    from transformers import AutoTokenizer

    from aria.config.huggingface import HuggingFace

    _silence_debug_loggers()  # call after gptqmodel import to override its own logger setup

    hf_token = HuggingFace.token
    output.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_path), trust_remote_code=True, token=hf_token
    )

    console.print("[cyan]Building calibration dataset...[/cyan]")
    calibration = _get_calibration_data(
        tokenizer,
        config.calibration_dataset,
        config.n_calibration_samples,
        config.calibration_seq_len,
    )

    quant_cfg = GptqCfg(
        bits=config.bits,
        group_size=config.group_size,
        desc_act=config.desc_act,
    )
    console.print(f"[cyan]Loading model for quantization: {model_path}[/cyan]")
    model = GPTQModel.from_pretrained(
        str(model_path),
        quantize_config=quant_cfg,
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    console.print(
        f"[green]Quantizing → GPTQ Int{config.bits} (group_size={config.group_size})...[/green]"
    )
    model.quantize(calibration)
    model.save_quantized(str(output))
    tokenizer.save_pretrained(str(output))

    logger.info("GPTQ Int{} model saved to {}", config.bits, output)
    console.print(f"[green]✓ GPTQ Int{config.bits} → {output}[/green]")
    console.print(
        f"[dim]  vLLM: --model {output} --quantization gptq_marlin[/dim]"
    )
    return output


# ── Publish to HuggingFace Hub ────────────────────────────────────────────


def push_to_hub(
    model_path: Path,
    repo_id: str,
    private: bool = False,
    token: Optional[str] = None,
    commit_message: str = "Upload GPTQ quantized model",
) -> str:
    """Push a quantized model directory to HuggingFace Hub.

    Creates the repo if it does not exist, then uploads the full directory.

    Args:
        model_path: Local path to the quantized model directory.
        repo_id: Target HF repo (e.g. ``"myorg/my-model-gptq-int4"``).
        private: Create the repo as private if it does not exist yet.
        token: HF API token. Falls back to ``HUGGINGFACE_TOKEN`` env var.
        commit_message: Commit message for the upload.

    Returns:
        HTTPS URL of the published repository.
    """
    from huggingface_hub import HfApi

    from aria.config.huggingface import HuggingFace

    resolved_token = token or HuggingFace.token or None
    api = HfApi(token=resolved_token)

    console.print(f"[cyan]Creating/verifying repo: {repo_id}[/cyan]")
    api.create_repo(
        repo_id=repo_id, private=private, exist_ok=True, repo_type="model"
    )

    console.print(f"[cyan]Uploading {model_path} → {repo_id}...[/cyan]")
    api.upload_folder(
        folder_path=str(model_path),
        repo_id=repo_id,
        repo_type="model",
        commit_message=commit_message,
    )

    url = f"https://huggingface.co/{repo_id}"
    logger.info("Model published to {}", url)
    console.print(f"[bold green]✓ Published → {url}[/bold green]")
    return url


# ── Parameter Recommendation ─────────────────────────────────────────────


@dataclass
class ModelInfo:
    """Metadata fetched from HuggingFace Hub for a model."""

    repo_id: str
    params_b: float  # total parameters in billions
    model_type: str  # e.g. "qwen2", "llama", "mistral"
    architectures: list[str]
    hidden_size: Optional[int] = None
    num_layers: Optional[int] = None


@dataclass
class Recommendation:
    """Recommended QLoRA SFT hyper-parameters for a given hardware + model."""

    lora_rank: int
    lora_alpha: int
    max_seq_len: int
    batch_size: int
    gradient_accumulation_steps: int
    learning_rate: float
    epochs: int
    max_memory: Optional[dict]
    reasoning: list[str]


def fetch_model_info(repo_id: str, token: Optional[str] = None) -> ModelInfo:
    """Fetch model metadata from HuggingFace Hub.

    Uses the HF API to retrieve parameter count and architecture info.
    Falls back to reasonable defaults when metadata is incomplete.
    """
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=token)
    info = api.model_info(repo_id)

    # Parameter count from safetensors metadata
    params_b = 0.0
    if info.safetensors and info.safetensors.total:
        params_b = info.safetensors.total / 1e9

    architectures = info.config.get("architectures", []) if info.config else []
    model_type = (
        info.config.get("model_type", "unknown") if info.config else "unknown"
    )
    hidden_size = info.config.get("hidden_size") if info.config else None
    num_layers = info.config.get("num_hidden_layers") if info.config else None

    # If safetensors metadata missing, try config.json
    if params_b == 0.0:
        try:
            config_path = hf_hub_download(repo_id, "config.json", token=token)
            with open(config_path) as f:
                cfg = json.load(f)
            model_type = cfg.get("model_type", model_type)
            hidden_size = cfg.get("hidden_size", hidden_size)
            num_layers = cfg.get("num_hidden_layers", num_layers)
            architectures = cfg.get("architectures", architectures)
        except Exception:
            pass

    return ModelInfo(
        repo_id=repo_id,
        params_b=params_b,
        model_type=model_type,
        architectures=architectures,
        hidden_size=hidden_size,
        num_layers=num_layers,
    )


def recommend(
    model_info: ModelInfo,
    vram_mib: int,
    ram_mib: int,
    bf16_supported: bool,
) -> Recommendation:
    """Compute recommended QLoRA SFT parameters for the given hardware.

    Args:
        model_info: Model metadata from :func:`fetch_model_info`.
        vram_mib: Total GPU VRAM in MiB.
        ram_mib: Total system RAM in MiB.
        bf16_supported: Whether the GPU supports BF16.

    Returns:
        A :class:`Recommendation` with hyper-parameters and reasoning.
    """
    reasoning: list[str] = []
    params_b = model_info.params_b
    vram_gib = vram_mib / 1024
    ram_gib = ram_mib / 1024

    reasoning.append(
        f"Model ~{params_b:.1f}B params on {vram_gib:.1f} GiB VRAM"
    )

    # ── Size-based LoRA + LR heuristics ────────────────────────────────
    if params_b < 3:
        lora_rank, lr, epochs = 8, 2e-4, 3
        reasoning.append(
            f"Small model (<3B) → rank {lora_rank}, lr {lr}, {epochs} epochs"
        )
    elif params_b < 8:
        lora_rank, lr, epochs = 16, 2e-4, 2
        reasoning.append(
            f"Medium model (3-8B) → rank {lora_rank}, lr {lr}, {epochs} epochs"
        )
    elif params_b < 20:
        lora_rank, lr, epochs = 32, 1e-4, 2
        reasoning.append(
            f"Large model (8-20B) → rank {lora_rank}, lr {lr}, {epochs} epochs"
        )
    elif params_b < 70:
        lora_rank, lr, epochs = 64, 5e-5, 1
        reasoning.append(
            f"Very large model (20-70B) → rank {lora_rank}, lr {lr}, {epochs} epoch"
        )
    else:
        lora_rank, lr, epochs = 64, 2e-5, 1
        reasoning.append(
            f"Massive model (>70B) → rank {lora_rank}, lr {lr}, {epochs} epoch"
        )

    lora_alpha = lora_rank * 2

    # ── QLoRA 4-bit memory estimation ──────────────────────────────────
    # NF4 weights ≈ 0.55 bytes/param (4-bit + double quant overhead)
    base_weights_gib = params_b * 0.55
    # LoRA adapter weights are small relative to base
    # Optimizer states: 2 × fp32 momenta per trainable param
    # Activations depend on batch, seq_len, hidden_size, n_layers
    overhead_gib = 2.0  # CUDA kernels, fragmentation, buffers

    reasoning.append(f"QLoRA 4-bit base weights ≈ {base_weights_gib:.1f} GiB")

    # ── Seq len + batch size tuning ────────────────────────────────────
    available_gib = vram_gib * 0.85  # 15% headroom
    remaining_gib = available_gib - base_weights_gib - overhead_gib

    if remaining_gib < 1.0:
        # Very tight — minimal settings, recommend CPU offload
        max_seq_len = 512
        batch_size = 1
        max_memory = {
            "0": f"{int(vram_gib * 0.9)}GiB",
            "cpu": f"{int(ram_gib * 0.8)}GiB",
        }
        reasoning.append(
            f"⚠ VRAM very tight ({remaining_gib:.1f} GiB after weights) → "
            f"seq_len={max_seq_len}, batch=1, CPU offload enabled"
        )
    elif remaining_gib < 4.0:
        max_seq_len = 1024
        batch_size = 1
        max_memory = None
        reasoning.append(
            f"VRAM tight ({remaining_gib:.1f} GiB remaining) → "
            f"seq_len={max_seq_len}, batch={batch_size}"
        )
    elif remaining_gib < 10.0:
        max_seq_len = 2048
        batch_size = 1
        max_memory = None
        reasoning.append(
            f"VRAM moderate ({remaining_gib:.1f} GiB remaining) → "
            f"seq_len={max_seq_len}, batch={batch_size}"
        )
    else:
        max_seq_len = 2048
        batch_size = 2
        max_memory = None
        reasoning.append(
            f"VRAM comfortable ({remaining_gib:.1f} GiB remaining) → "
            f"seq_len={max_seq_len}, batch={batch_size}"
        )

    # ── Gradient accumulation → target effective batch ≈ 16 ────────────
    target_effective = 16
    grad_accum = max(1, target_effective // batch_size)
    reasoning.append(
        f"Effective batch size: {batch_size} × {grad_accum} = "
        f"{batch_size * grad_accum} (target ~{target_effective})"
    )

    if bf16_supported:
        reasoning.append("BF16 supported ✓ — will use bf16 compute")

    return Recommendation(
        lora_rank=lora_rank,
        lora_alpha=lora_alpha,
        max_seq_len=max_seq_len,
        batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        epochs=epochs,
        max_memory=max_memory,
        reasoning=reasoning,
    )
