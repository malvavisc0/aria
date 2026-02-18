"""Server management module for the Aria application.

This module provides:
- ``ServerManager``: controls the Chainlit webserver lifecycle (start, stop, restart, status)
- ``LlamaCppServerManager``: manages the three llama-server inference processes
  (chat, vision/language, embeddings)

Example:
    ```python
    from aria.server import ServerManager, LlamaCppServerManager

    llama = LlamaCppServerManager(context_size=8192)
    llama.start_all()

    manager = ServerManager()
    manager.run()  # blocking

    llama.stop_all()
    ```
"""

from aria.server.llama import LlamaCppServerManager
from aria.server.manager import ServerManager, ServerStatus

__all__ = [
    "ServerManager",
    "ServerStatus",
    "LlamaCppServerManager",
]
