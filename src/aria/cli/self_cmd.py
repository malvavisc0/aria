"""Self-awareness CLI — test-tools.

Provides introspection commands that Aria can run on herself
to verify tool availability.
"""

import json

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
