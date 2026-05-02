"""Self-awareness CLI — introspection commands.

Provides introspection commands that Aria can run on herself
to verify tool availability and locate her own code.
"""

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(
    help="Introspection and self-diagnostic commands.",
)


@app.command("test-tools")
def test_tools():
    """Smoke-test all registered tool categories. Returns JSON report."""
    from aria.tools.registry import (
        ALL_CATEGORIES,
        CORE,
        FILES,
        get_tools,
    )

    results = {}

    # Test core + files (always loaded)
    for category in [CORE, FILES]:
        try:
            tools = get_tools([category])
            results[category] = {
                "status": "ok",
                "count": len(tools),
                "tools": [t.metadata.name for t in tools],
            }
        except Exception as e:
            results[category] = {"status": "error", "error": str(e)}

    # Test on-demand categories (may fail if dependencies missing)
    on_demand = [c for c in ALL_CATEGORIES if c not in (CORE, FILES)]
    for category in on_demand:
        try:
            tools = get_tools([category])
            results[category] = {
                "status": "ok",
                "count": len(tools),
                "tools": [t.metadata.name for t in tools],
            }
        except Exception as e:
            results[category] = {
                "status": "unavailable",
                "error": str(e),
            }

    # Summary
    total_ok = sum(1 for v in results.values() if v["status"] == "ok")
    total_tools = sum(
        v.get("count", 0) for v in results.values() if v["status"] == "ok"
    )

    typer.echo(
        json.dumps(
            {
                "categories_ok": total_ok,
                "categories_total": len(results),
                "tools_available": total_tools,
                "details": results,
            },
            indent=2,
        )
    )


@app.command("path")
def show_path():
    """Show the filesystem paths of Aria's code and Python runtime.

    Returns JSON with the aria package directory and the Python
    interpreter currently running her code.

    Example:
        ```bash
        aria self path
        ```
    """
    import aria

    package_dir = str(Path(aria.__file__).resolve().parent)
    python_bin = sys.executable

    typer.echo(
        json.dumps(
            {
                "package_dir": package_dir,
                "python_bin": python_bin,
            },
            indent=2,
        )
    )
