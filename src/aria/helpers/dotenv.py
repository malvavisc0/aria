"""Read and write .env files while preserving comments and ordering."""

from __future__ import annotations

import re
from pathlib import Path

_LINE_RE = re.compile(
    r"^(?P<key>[A-Z_][A-Z0-9_]*)\s*=\s*(?P<value>[^#]*?)"
    r"(?:\s*#\s*(?P<comment>.*))?$"
)


def parse_dotenv(path: Path) -> tuple[dict[str, str], list[str]]:
    """Parse a .env file into ``(values, raw_lines)``.

    ``raw_lines`` preserves comments/blank lines for round-trip writes.
    """
    if not path.exists():
        return {}, []

    values: dict[str, str] = {}
    raw_lines: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        raw_lines.append(line)
        match = _LINE_RE.match(line)
        if match:
            values[match.group("key")] = match.group("value").strip()

    return values, raw_lines


def write_dotenv(
    path: Path, values: dict[str, str], raw_lines: list[str]
) -> None:
    """Write updated values into a .env while preserving structure.

    Existing key lines are updated in-place (comments stay), unknown lines are
    untouched, and missing keys from ``values`` are appended at the end.
    """
    out: list[str] = []
    seen_keys: set[str] = set()

    for line in raw_lines:
        match = _LINE_RE.match(line)
        if not match:
            out.append(line)
            continue

        key = match.group("key")
        if key not in values:
            out.append(line)
            continue

        seen_keys.add(key)
        new_value = values[key]
        comment = match.group("comment")
        if comment:
            out.append(f"{key} = {new_value}  # {comment}")
        else:
            out.append(f"{key} = {new_value}")

    missing_keys = [key for key in values if key not in seen_keys]
    if missing_keys:
        if out and out[-1].strip():
            out.append("")
        for key in missing_keys:
            out.append(f"{key} = {values[key]}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
