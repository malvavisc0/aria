"""Tool output compression for context budget management.

When tool outputs accumulate across many iterations within a single agent
turn, they can consume the entire context window.  This module provides
a compression step that runs *after* each tool call returns but *before*
the output is injected into the agent's context.

The full output is still available for logging and diagnostics — only the
version injected into the LLM context is compressed.

Strategy
--------
* **Small outputs** (< threshold_min): pass through unchanged.
* **Medium outputs** (threshold_min–threshold_max): keep head + tail + notice.
* **Large outputs** (> threshold_max): aggressive head + tail + notice.

All thresholds are computed as **fractions of the context window** so they
scale correctly across hardware profiles (32K, 131K, 262K, etc.).

The notice tells the agent the output was compressed so it can request
smaller chunks via ``offset``/``length`` or ``max_results``.

JSON-aware cutting
------------------
When the output looks like JSON, cut points are adjusted to the nearest
structural boundary (newline, `},`, `]`) so the LLM receives parseable
fragments rather than garbled mid-key splits.
"""

from __future__ import annotations

import os
import re

from loguru import logger


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, ""))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Ratio-based thresholds (fractions of context window in chars)
# ---------------------------------------------------------------------------

# Approximate chars per token (English text average).
_CHARS_PER_TOKEN = 4

# Below this fraction of context: no compression.
COMPRESS_MIN_RATIO = _env_float("ARIA_COMPRESS_MIN_RATIO", 0.005)  # 0.5%

# Above this fraction of context: aggressive compression.
COMPRESS_MAX_RATIO = _env_float("ARIA_COMPRESS_MAX_RATIO", 0.025)  # 2.5%

# Head size as fraction of context (medium compression).
COMPRESS_HEAD_RATIO = _env_float("ARIA_COMPRESS_HEAD_RATIO", 0.005)  # 0.5%

# Tail size as fraction of context (medium compression).
COMPRESS_TAIL_RATIO = _env_float("ARIA_COMPRESS_TAIL_RATIO", 0.002)  # 0.2%

# Aggressive head as fraction of context.
COMPRESS_AGGRESSIVE_HEAD_RATIO = _env_float(
    "ARIA_COMPRESS_AGGRESSIVE_HEAD_RATIO",
    0.002,  # 0.2%
)

# Aggressive tail as fraction of context.
COMPRESS_AGGRESSIVE_TAIL_RATIO = _env_float(
    "ARIA_COMPRESS_AGGRESSIVE_TAIL_RATIO",
    0.001,  # 0.1%
)

# Per-turn scratchpad pressure threshold (fraction of context_size).
# When exceeded, old tool results in the conversation get compressed.
SCRATCHPAD_PRESSURE_THRESHOLD = _env_float("ARIA_SCRATCHPAD_PRESSURE_THRESHOLD", 0.40)


def _get_context_size() -> int:
    """Read the configured context window size in tokens.

    Checks ``CHAT_CONTEXT_SIZE`` env var first (allows override/testing),
    then falls back to ``VllmConfig.chat_context_size`` (the application
    default), and finally to 32768 as a last resort.
    """
    raw = os.environ.get("CHAT_CONTEXT_SIZE", "")
    if raw:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    try:
        from aria.config.api import Vllm as VllmConfig

        return VllmConfig.chat_context_size
    except Exception:
        return 32768


def _compute_thresholds(context_size: int) -> dict[str, int]:
    """Compute absolute char thresholds from context-size ratios.

    Parameters
    ----------
    context_size:
        Context window size in **tokens**.  Converted to chars using
        ``_CHARS_PER_TOKEN``.

    Returns
    -------
    dict
        Dictionary with keys: min_chars, max_chars, head_chars,
        tail_chars, aggressive_head, aggressive_tail.
    """
    ctx_chars = context_size * _CHARS_PER_TOKEN

    thresholds = {
        "min_chars": int(ctx_chars * COMPRESS_MIN_RATIO),
        "max_chars": int(ctx_chars * COMPRESS_MAX_RATIO),
        "head_chars": int(ctx_chars * COMPRESS_HEAD_RATIO),
        "tail_chars": int(ctx_chars * COMPRESS_TAIL_RATIO),
        "aggressive_head": int(ctx_chars * COMPRESS_AGGRESSIVE_HEAD_RATIO),
        "aggressive_tail": int(ctx_chars * COMPRESS_AGGRESSIVE_TAIL_RATIO),
    }

    # Absolute overrides take precedence — read at runtime so env changes
    # (e.g. from monkeypatch) are respected without module reload.
    _overrides = {
        "min_chars": "ARIA_COMPRESS_MIN_CHARS",
        "max_chars": "ARIA_COMPRESS_MAX_CHARS",
        "head_chars": "ARIA_COMPRESS_HEAD_CHARS",
        "tail_chars": "ARIA_COMPRESS_TAIL_CHARS",
        "aggressive_head": "ARIA_COMPRESS_AGGRESSIVE_HEAD",
        "aggressive_tail": "ARIA_COMPRESS_AGGRESSIVE_TAIL",
    }
    for key, env_var in _overrides.items():
        raw = os.environ.get(env_var, "")
        if raw:
            thresholds[key] = int(raw)

    return thresholds


def _get_thresholds() -> dict[str, int]:
    """Get or compute thresholds for the current context size.

    Uses a cached result so the thresholds are computed once per process.
    """
    if not hasattr(_get_thresholds, "_cache"):
        _get_thresholds._cache = {}  # type: ignore[attr-defined]

    ctx = _get_context_size()
    if ctx not in _get_thresholds._cache:  # type: ignore[attr-defined]
        _get_thresholds._cache[ctx] = _compute_thresholds(ctx)  # type: ignore[attr-defined]

    return _get_thresholds._cache[ctx]  # type: ignore[attr-defined]


def _reset_threshold_cache() -> None:
    """Clear the threshold cache (for testing)."""
    _get_thresholds._cache = {}  # type: ignore[attr-defined]


# Regex for JSON structural boundaries suitable as cut points.
_JSON_BOUNDARY = re.compile(r"[}\]],?\s*\n|\n")


def _find_head_cut(output: str, budget: int) -> int:
    """Find the best head cut point ≤ budget for JSON-like content.

    Scans backwards from *budget* for a structural JSON boundary
    (closing brace/bracket followed by comma and newline). Falls back
    to the last newline, then raw budget if nothing is found.
    """
    if budget >= len(output):
        return budget
    # Search in the last 20% of the budget window for a boundary.
    search_start = max(0, budget - budget // 5)
    region = output[search_start:budget]
    # Find last boundary in region.
    match = None
    for m in _JSON_BOUNDARY.finditer(region):
        match = m
    if match:
        return search_start + match.end()
    # Fallback: last newline in budget range.
    nl = output.rfind("\n", 0, budget)
    if nl > budget // 2:
        return nl + 1
    return budget


def _find_tail_cut(output: str, start: int) -> int:
    """Find the best tail start point ≥ start for JSON-like content.

    Scans forward from *start* for a structural boundary (opening
    brace/bracket or newline). Falls back to raw start.
    """
    if start <= 0:
        return 0
    # Search in the first 20% of the tail window for a boundary.
    search_end = min(len(output), start + (len(output) - start) // 5)
    region = output[start:search_end]
    # Find first newline or opening struct in region.
    match = re.search(r'\n\s*[{\["a-zA-Z]', region)
    if match:
        return start + match.start() + 1  # after the newline
    nl = output.find("\n", start)
    if nl != -1 and nl < search_end:
        return nl + 1
    return start


def _is_json_like(output: str) -> bool:
    """Heuristic: output looks like JSON or pretty-printed structured data."""
    stripped = output.lstrip()
    return stripped[:1] in ("{", "[") or stripped[:2] == '{"'


def compress_tool_output(output: str, tool_name: str = "") -> str:
    """Compress a tool output to fit within the context budget.

    This is a *deterministic, lossy* compression — no LLM call needed.
    It keeps the beginning and end of large outputs with a notice so the
    agent knows data was dropped and can request smaller chunks.

    For JSON-structured outputs, cut points are adjusted to structural
    boundaries (closing braces, newlines) so the LLM receives parseable
    fragments rather than garbled mid-key splits.

    Parameters
    ----------
    output:
        Raw tool output string.
    tool_name:
        Name of the tool (for logging).

    Returns
    -------
    str
        Compressed output (or unchanged if already small enough).
    """
    if not output:
        return output

    t = _get_thresholds()
    length = len(output)

    if length <= t["min_chars"]:
        return output

    json_like = _is_json_like(output)

    # --- Medium compression (head + tail) ---
    if length <= t["max_chars"]:
        head_budget = t["head_chars"]
        tail_budget = t["tail_chars"]

        if json_like:
            head_end = _find_head_cut(output, head_budget)
            tail_start = _find_tail_cut(output, length - tail_budget)
        else:
            head_end = head_budget
            tail_start = length - tail_budget

        head = output[:head_end]
        tail = output[tail_start:]
        dropped = length - len(head) - len(tail)

        # Guard: if compressed result would be longer than original,
        # skip compression entirely.
        notice_len = 130
        if len(head) + notice_len + len(tail) >= length:
            return output

        notice = (
            f"\n\n[...compressed — dropped {dropped:,} chars from middle. "
            f"Original: {length:,} chars. "
            f"Use offset/length or max_results for smaller chunks.]"
        )
        result = head + notice + tail
        logger.debug(
            f"Compressed {tool_name} output: {length:,} → {len(result):,} chars"
        )
        return result

    # --- Aggressive compression (large outputs) ---
    head_budget = t["aggressive_head"]
    tail_budget = t["aggressive_tail"]

    if json_like:
        head_end = _find_head_cut(output, head_budget)
        tail_start = _find_tail_cut(output, length - tail_budget)
    else:
        head_end = head_budget
        tail_start = length - tail_budget

    head = output[:head_end]
    tail = output[tail_start:]
    dropped = length - len(head) - len(tail)

    # Guard: same check for aggressive thresholds.
    notice_len = 140
    if len(head) + notice_len + len(tail) >= length:
        return output

    notice = (
        f"\n\n[...heavily compressed — dropped {dropped:,} chars. "
        f"Original: {length:,} chars. "
        f"Use offset/length or max_results for smaller chunks.]"
    )
    result = head + notice + tail
    logger.debug(
        f"Aggressively compressed {tool_name} output: "
        f"{length:,} → {len(result):,} chars"
    )
    return result
