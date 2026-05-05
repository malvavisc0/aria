"""Server management module for the Aria application.

This module provides:
- ``ServerManager``: controls the Chainlit webserver lifecycle (start, stop, restart, status)
- ``VllmServerManager``: manages the vLLM inference processes
  (chat, embeddings, rerank)

Example:
    ```python
    from aria.server import ServerManager, VllmServerManager

    vllm = VllmServerManager()
    vllm.start_all()

    manager = ServerManager()
    manager.run()  # blocking

    vllm.stop_all()
    ```
"""

from aria.server.manager import ServerManager, ServerStatus
from aria.server.vllm import VllmServerManager

__all__ = [
    "ServerManager",
    "ServerStatus",
    "VllmServerManager",
]
