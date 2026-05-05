"""Rerank micro-server using sentence-transformers CrossEncoder.

Provides a lightweight FastAPI server that exposes a ``/rerank`` endpoint
compatible with the OpenAI rerank API format. Runs on port 9093 by default.

This module is designed to be invoked as a subprocess by
:class:`aria.server.vllm.VllmServerManager`.

Example:
    ```bash
    # Start the rerank server directly
    python -m aria.server.rerank --model BAAI/bge-reranker-v2-m3 --port 9093

    # Or let VllmServerManager handle it via .env config
    ```
"""

import argparse
import sys

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


def create_app(model_name: str) -> FastAPI:
    """Create and configure the FastAPI rerank application.

    Args:
        model_name: HuggingFace model ID for the CrossEncoder.

    Returns:
        Configured FastAPI application instance.
    """
    from sentence_transformers import CrossEncoder

    app = FastAPI(title="Aria Rerank Server")
    # Force CPU to avoid competing with the vLLM chat model for GPU VRAM.
    # Reranking is lightweight and latency-insensitive — CPU is fine.
    app.state.model = CrossEncoder(model_name, max_length=512, device="cpu")

    class RerankRequest(BaseModel):
        model: str = Field(default="", description="Model name (ignored)")
        query: str = Field(..., description="Search query")
        documents: list[str] = Field(..., description="Documents to rerank")
        top_n: int | None = Field(default=None, description="Top N results")

    class RerankResult(BaseModel):
        index: int
        relevance_score: float
        document: dict | None = None

    class RerankResponse(BaseModel):
        results: list[RerankResult]
        model: str

    @app.post("/rerank")
    async def rerank(request: RerankRequest):
        """Rerank documents by relevance to the query."""
        try:
            model = app.state.model
            pairs = [(request.query, doc) for doc in request.documents]
            scores = model.predict(pairs)

            results = [
                RerankResult(
                    index=i,
                    relevance_score=float(score),
                    document={"text": doc},
                )
                for i, (score, doc) in enumerate(
                    zip(scores, request.documents)
                )
            ]

            # Sort by relevance (descending)
            results.sort(key=lambda r: r.relevance_score, reverse=True)

            # Apply top_n if specified
            if request.top_n is not None:
                results = results[: request.top_n]

            return RerankResponse(
                results=results,
                model=model_name,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "model": model_name}

    return app


def main():
    """Entry point for the rerank server."""
    parser = argparse.ArgumentParser(description="Aria Rerank Server")
    parser.add_argument(
        "--model",
        required=True,
        help="HuggingFace model ID for the CrossEncoder",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9093,
        help="Port to listen on (default: 9093)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    app = create_app(args.model)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
