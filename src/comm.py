import asyncio
import json
from os import environ
from typing import Sequence

import chainlit

API_PORT = environ.get("API_PORT", 8000)
API_VALID_KEY = environ.get("API_VALID_KEY")
API_HEADERS = {"X-API-Key": API_VALID_KEY}
API_URL = f"http://api:{API_PORT}/v1"


@chainlit.step(name="Generate Search Queries")
async def generate_search_queries(session, topic: str) -> str:
    payload = {"input": topic}
    async with session.post(f"{API_URL}/jobs/queries", json=payload) as response:
        json = await response.json()
        return json["id"]


@chainlit.step(name="Obtain Search Queries")
async def get_search_queries(session, job_id: str) -> Sequence[str]:
    results = None
    while results is None:
        await asyncio.sleep(1)
        async with session.get(f"{API_URL}/jobs/{job_id}") as response:
            results = await response.json()
            if results["status"] in ("created", "running"):
                results = None
    if "results" in results["output"]:
        return json.loads(results["output"])
    raise Exception("No results found")


@chainlit.step(name="API Health Check")
async def health_check(session) -> bool:
    async with session.get(f"{API_URL}/check") as response:
        return response.status == 200
