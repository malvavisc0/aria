import asyncio

from agno.playground.playground import Playground
from agno.playground.serve import serve_playground_app

from assistant.agents.builder import build_group

types = [
    "chatter",
    "scientist",
    "finance",
    "youtube",
    "researcher",
    "medic",
    "wikipedia",
    "reasoning",
]

agents = build_group(types=types, thread_id="playground", has_images=False)

app = Playground(agents=agents).get_app()

if __name__ == "__main__":
    serve_playground_app(
        "playground:app", host="0.0.0.0", port=7777, reload=True
    )
