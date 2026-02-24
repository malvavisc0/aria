"""Server management handlers for the MainWindow.

This module provides a mixin class with server control functionality
for the Aria GUI application.
"""

from __future__ import annotations

import webbrowser
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from aria.config.service import Server
from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.server import LlamaCppServerManager, ServerManager


class _LlamaStartWorker(QObject):
    """Worker that starts llama-server processes in a background thread.

    Emits ``finished`` when all servers are ready, or ``error`` if any fail.
    """

    finished = Signal()
    error = Signal(str)

    def __init__(self, llama_manager: LlamaCppServerManager):
        super().__init__()
        self._llama_manager = llama_manager

    def run(self) -> None:
        """Start all llama-server processes (runs in a QThread)."""
        try:
            self._llama_manager.start_all()
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class ServerHandlersMixin:
    """Mixin class providing server management handlers for MainWindow.

    This mixin expects to be combined with a QMainWindow that has a ``ui``
    attribute of type ``Ui_MainWindow``. It provides:

    - Server start/stop/open button handlers
    - Periodic status updates via QTimer
    - Button state management based on server running state
    - LlamaCPP inference server lifecycle management (via QThread)

    Attributes:
        _server_manager: ServerManager instance for controlling the webserver.
        _llama_manager: LlamaCppServerManager instance for inference servers.
        _server_timer: QTimer for periodic status updates.
    """

    ui: Ui_MainWindow

    def _init_server_manager(self):
        """Initialize the server manager and status update timer.

        This method should be called in the MainWindow __init__ method
        after the UI is set up.
        """
        self._server_manager = ServerManager()
        self._llama_manager: Optional[LlamaCppServerManager] = None
        self._llama_thread: Optional[QThread] = None
        self._server_timer = QTimer()
        self._server_timer.timeout.connect(self._update_server_status)
        self._server_timer.start(1000)  # Update every second

    def _connect_server_signals(self):
        """Connect server control button signals.

        This method should be called in the MainWindow __init__ method
        to connect the Start, Stop, and Open buttons.
        """
        self.ui.pushButton_ServiceStart.clicked.connect(self.on_start_server)
        self.ui.pushButton_ServiceStop.clicked.connect(self.on_stop_server)
        self.ui.pushButton_ServiceOpen.clicked.connect(self.on_open_server)

    def _cleanup_llama_thread(self):
        """Clean up the llama server thread if it exists.

        This method safely stops and cleans up any existing QThread
        to prevent memory leaks and crashes.
        """
        if self._llama_thread is not None:
            if self._llama_thread.isRunning():
                self._llama_thread.quit()
                # Wait up to 5 seconds for graceful shutdown
                if not self._llama_thread.wait(5000):
                    # Force terminate if graceful shutdown fails
                    self._llama_thread.terminate()
                    self._llama_thread.wait()
            self._llama_thread = None

    def on_start_server(self):
        """Handle Start button click.

        Starts the llama-server inference processes in a background QThread
        (to avoid blocking the UI during the health-check wait), then starts
        the Chainlit webserver once all inference servers are ready.
        """
        # Clean up any previous thread
        self._cleanup_llama_thread()

        # Disable the start button while starting
        self.ui.pushButton_ServiceStart.setEnabled(False)

        # Create a new LlamaCppServerManager
        self._llama_manager = LlamaCppServerManager()

        # Run start_all() in a background thread
        self._llama_thread = QThread()
        worker = _LlamaStartWorker(self._llama_manager)
        worker.moveToThread(self._llama_thread)

        self._llama_thread.started.connect(worker.run)
        worker.finished.connect(self._on_llama_started)
        worker.error.connect(self._on_llama_error)
        worker.finished.connect(self._llama_thread.quit)
        worker.error.connect(self._llama_thread.quit)
        self._llama_thread.finished.connect(worker.deleteLater)

        self._llama_thread.start()

    def _on_llama_started(self):
        """Called when all llama-server processes are ready.

        Starts the Chainlit webserver.
        """
        self._server_manager.start()
        self._update_server_status()

    def _on_llama_error(self, error_message: str):
        """Called when llama-server startup fails.

        Re-enables the start button and logs the error.
        """
        from loguru import logger

        logger.error(f"Failed to start inference servers: {error_message}")
        self.ui.pushButton_ServiceStart.setEnabled(True)
        self._update_server_status()

    def on_stop_server(self):
        """Handle Stop button click.

        Stops the Chainlit webserver and all llama-server inference processes.
        """
        self._server_manager.stop()

        if self._llama_manager is not None:
            self._llama_manager.stop_all()
            self._llama_manager = None

        # Clean up the thread
        self._cleanup_llama_thread()

        self._update_server_status()

    def on_open_server(self):
        """Handle Open button click.

        Opens the system web browser to the server URL.
        """
        webbrowser.open(Server.get_base_url())

    def _update_server_status(self):
        """Update server status display and button states.

        This method is called every second by the server timer to:
        - Update status indicator, PID, URL, start time, and uptime labels
        - Enable/disable buttons based on server running state
        """
        status = self._server_manager.get_status()

        # Update status indicator label (pill badge)
        _BADGE_BASE = (
            "color: white; font-size: 13pt;" " padding: 4px 14px; border-radius: 6px;"
        )
        if status.running:
            self.ui.label_ServiceStatus.setText("Running")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #2e7d32; {_BADGE_BASE} }}"
            )
        else:
            self.ui.label_ServiceStatus.setText("Stopped")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #c62828; {_BADGE_BASE} }}"
            )

        # Update PID label
        self.ui.label_ServicePID.setText(str(status.pid) if status.pid else "-")

        # Update URL label as a clickable hyperlink
        url = f"http://{status.host}:{status.port}"
        self.ui.label_ServiceURL.setText(f'<a href="{url}">{url}</a>')
        self.ui.label_ServiceURL.setOpenExternalLinks(True)

        # Update start time label
        if status.started_at:
            self.ui.label_ServiceStarted.setText(
                status.started_at.strftime("%Y-%m-%d %H:%M:%S")
            )
        else:
            self.ui.label_ServiceStarted.setText("-")

        # Update uptime label
        if status.uptime_seconds is not None:
            hours, remainder = divmod(int(status.uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.ui.label_ServiceUptime.setText(f"{hours}h {minutes}m {seconds}s")
        else:
            self.ui.label_ServiceUptime.setText("-")

        # Update button states
        self.ui.pushButton_ServiceStart.setEnabled(not status.running)
        self.ui.pushButton_ServiceStop.setEnabled(status.running)
        self.ui.pushButton_ServiceOpen.setEnabled(status.running)
