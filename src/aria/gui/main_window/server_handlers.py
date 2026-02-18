"""Server management handlers for the MainWindow.

This module provides a mixin class with server control functionality
for the Aria GUI application.
"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import QTimer

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

    def on_start_server(self):
        """Handle Start button click.

        Starts the webserver in the background and updates the status display.
        """
        self._server_manager.start()
        self._update_server_status()

    def on_stop_server(self):
        """Handle Stop button click.

        Stops the webserver and updates the status display.
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
        - Update PID, URL, start time, and uptime labels
        - Enable/disable buttons based on server running state
        """
        status = self._server_manager.get_status()

        # Update PID label
        self.ui.label_ServicePID.setText(str(status.pid) if status.pid else "-")

        # Update URL label
        self.ui.label_ServiceURL.setText(f"http://{status.host}:{status.port}")

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
