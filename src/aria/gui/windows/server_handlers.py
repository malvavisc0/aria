"""Server management handlers for the MainWindow.

This module provides a mixin class with server control functionality
for the Aria GUI application.
"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from aria.config.service import Server
from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.server import ServerManager


class ServerHandlersMixin:
    """Mixin class providing server management handlers for MainWindow.

    This mixin expects to be combined with a QMainWindow that has a ``ui``
    attribute of type ``Ui_MainWindow``. It provides:

    - Server start/stop/open button handlers
    - Periodic status updates via QTimer
    - Button state management based on server running state

    Attributes:
        _server_manager: ServerManager instance for controlling the webserver.
        _server_timer: QTimer for periodic status updates.
    """

    ui: Ui_MainWindow

    def _init_server_manager(self):
        """Initialize the server manager and status update timer.

        This method should be called in the MainWindow __init__ method
        after the UI is set up.
        """
        self._server_manager = ServerManager()
        self._preflight_result = None
        self._server_timer = QTimer()
        self._server_timer.timeout.connect(self._update_server_status)
        self._server_timer.start(1000)

    def _connect_server_signals(self):
        """Connect server control button signals.

        This method should be called in the MainWindow __init__ method
        to connect the Start, Stop, and Open buttons.
        """
        self.ui.pushButton_ServiceStart.clicked.connect(self.on_start_server)
        self.ui.pushButton_ServiceStop.clicked.connect(self.on_stop_server)
        self.ui.pushButton_ServiceOpen.clicked.connect(self.on_open_server)

    def _run_preflight(self) -> None:
        """Run preflight checks and cache the result.

        Calls ``run_preflight_checks()`` (which may invoke nvidia-smi and
        other subprocess calls) and stores the result in
        ``self._preflight_result``.  Triggers a status-bar refresh so the
        Start button state is updated immediately.

        Call this on startup and whenever the environment may have changed
        (e.g. after a binary or model download completes, or when the user
        switches to the Overview / Setup tab).
        """
        from aria.preflight import run_preflight_checks

        self._preflight_result = run_preflight_checks()
        self._update_server_status()

    def on_start_server(self):
        """Handle Start button click.

        Starts the Chainlit webserver as a background subprocess.
        The llama-server inference processes are started automatically
        by the web UI via the Chainlit ``on_app_startup`` lifecycle hook.
        """
        self.ui.pushButton_ServiceStart.setEnabled(False)
        self.statusBar().showMessage("Starting Aria server\u2026")

        started = self._server_manager.start()
        if not started:
            QMessageBox.warning(
                self,
                "Already Running",
                "The server is already running.",
            )

        self._update_server_status()

    def on_stop_server(self):
        """Handle Stop button click.

        Stops the Chainlit webserver. The llama-server inference processes
        are stopped automatically by the web UI via the Chainlit
        ``on_app_shutdown`` lifecycle hook.
        """
        self._server_manager.stop()
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

        Three distinct states are shown:
        - Stopped (red): process is not running
        - Starting\u2026 (orange): process is alive but /health not yet responding
        - Running (green): process is alive and /health returns HTTP 200
        """
        status = self._server_manager.get_status()

        _BADGE_BASE = (
            "color: white; font-size: 13pt; padding: 4px 14px; border-radius: 6px;"
        )
        if status.healthy:
            self.ui.label_ServiceStatus.setText("Running")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #2e7d32; {_BADGE_BASE} }}"
            )
            self.statusBar().clearMessage()
        elif status.running:
            self.ui.label_ServiceStatus.setText("Starting\u2026")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #e65100; {_BADGE_BASE} }}"
            )
            self.statusBar().showMessage(
                "Starting Aria server\u2026 this may take a few minutes."
            )
        else:
            self.ui.label_ServiceStatus.setText("Stopped")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #c62828; {_BADGE_BASE} }}"
            )

        self.ui.label_ServicePID.setText(str(status.pid) if status.pid else "-")

        url = f"http://{status.host}:{status.port}"
        self.ui.label_ServiceURL.setText(f'<a href="{url}">{url}</a>')
        self.ui.label_ServiceURL.setOpenExternalLinks(True)

        if status.started_at:
            self.ui.label_ServiceStarted.setText(
                status.started_at.strftime("%Y-%m-%d %H:%M:%S")
            )
        else:
            self.ui.label_ServiceStarted.setText("-")

        if status.uptime_seconds is not None:
            hours, remainder = divmod(int(status.uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.ui.label_ServiceUptime.setText(f"{hours}h {minutes}m {seconds}s")
        else:
            self.ui.label_ServiceUptime.setText("-")

        preflight_ok = (
            self._preflight_result is not None and self._preflight_result.passed
        )
        can_start = not status.running and preflight_ok
        self.ui.pushButton_ServiceStart.setEnabled(can_start)
        self.ui.pushButton_ServiceStop.setEnabled(status.running)
        self.ui.pushButton_ServiceOpen.setEnabled(status.healthy)

        if not status.running and not preflight_ok:
            if self._preflight_result is not None:
                failures = "\n".join(
                    f"  \u2022 {c.name}: {c.error}"
                    for c in self._preflight_result.failures
                )
                self.ui.pushButton_ServiceStart.setToolTip(
                    f"Cannot start \u2014 fix these issues first:\n{failures}"
                )
            else:
                self.ui.pushButton_ServiceStart.setToolTip(
                    "Cannot start \u2014 preflight checks have not run yet"
                )
        else:
            self.ui.pushButton_ServiceStart.setToolTip("")
