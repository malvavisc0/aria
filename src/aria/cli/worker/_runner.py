"""Subprocess entry point for worker agent execution.

This module is invoked as ``python -m aria.cli.worker._runner`` by the
``aria worker spawn`` CLI command. It initializes an LLM client, creates
a WorkerAgent, runs the prompt autonomously, and writes results to disk.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger


def _update_audit(worker_id: str, updates: dict):
    from aria.config.folders import Data
    from aria.server.process_utils import load_state, save_state

    path = Data.path / "workers" / f"{worker_id}.json"
    audit = load_state(path)
    audit.update(updates)
    save_state(path, audit)


async def _run(args):
    from llama_index.core.agent.workflow import (
        AgentOutput,
        AgentWorkflow,
        ToolCall,
    )
    from llama_index.core.memory import Memory

    from aria.agents.worker import get_worker_agent
    from aria.config.models import Chat as ChatConfig
    from aria.llm import get_chat_llm, get_instructions_extras

    worker_id = args.worker_id
    output_dir = Path(args.output_dir)

    log_file = output_dir / "worker.log"
    logger.add(str(log_file), rotation="10 MB", level="DEBUG")
    logger.info(f"Worker {worker_id} starting (PID {os.getpid()})")

    _update_audit(
        worker_id, {"started_at": datetime.now(timezone.utc).isoformat()}
    )

    try:
        llm = get_chat_llm(api_base=ChatConfig.api_url)
        extras = get_instructions_extras(agent_name="worker")
        agent = get_worker_agent(
            llm=llm, extras=extras, output_dir=str(output_dir)
        )

        memory = Memory.from_defaults(session_id=worker_id, token_limit=8192)

        prompt = args.prompt
        if args.instructions:
            prompt += f"\n\nAdditional instructions: {args.instructions}"

        workflow = AgentWorkflow(agents=[agent], root_agent=agent.name)
        handler = workflow.run(
            user_msg=prompt,
            memory=memory,
            max_iterations=ChatConfig.max_iteration,
        )

        tool_calls = []
        result_text = ""

        async for event in handler.stream_events():
            if isinstance(event, ToolCall):
                tool_calls.append(
                    {
                        "tool": event.tool_name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            elif isinstance(event, AgentOutput) and event.response:
                content = getattr(event.response, "content", "")
                if content:
                    result_text = content

        final = await handler
        if hasattr(final, "response") and final.response:
            content = getattr(final.response, "content", "")
            if content:
                result_text = content

        # Save result
        result_file = output_dir / "result.md"
        result_file.write_text(result_text)

        _update_audit(
            worker_id,
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": result_text[:2000],
                "result_file": str(result_file),
                "tool_calls": tool_calls,
            },
        )
        logger.info(f"Worker {worker_id} completed")

    except Exception as e:
        logger.exception(f"Worker {worker_id} failed: {e}")
        _update_audit(
            worker_id,
            {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            },
        )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--instructions", default=None)
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
