"""Server management module for the Aria application.

This module provides the ServerManager class for controlling the
Chainlit webserver lifecycle (start, stop, restart, status).

Example:
    ```python
    from aria.server import ServerManager, ServerStatus

    manager = ServerManager()
    manager.start()  # Start in background
    status = manager.get_status()
    manager.stop()   # Stop the server
    ```
"""

from aria.server.manager import ServerManager, ServerStatus

__all__ = ["ServerManager", "ServerStatus"]
