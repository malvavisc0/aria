"""Server management handlers for the MainWindow.

This module provides a mixin class with server control functionality
for the Aria GUI application.
"""

from __future__ import annotations

import time
import webbrowser

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

from aria.config.service import Server
from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.server import ServerManager


class _StopWorker(QObject):
    """Background worker that calls ServerManager.stop() off the GUI thread."""

    finished = Signal()
    failed = Signal(str)

    def __init__(self, server_manager):
        super().__init__()
        self._server_manager = server_manager

    def run(self):
        try:
            self._server_manager.stop()
            self.finished.emit()
        except Exception as exc:  # pragma: no cover - defensive UI path
            self.failed.emit(str(exc))


class _PreflightWorker(QObject):
    """Background worker that runs preflight checks off the GUI thread."""

    finished = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            from aria.preflight import run_preflight_checks

            self.finished.emit(run_preflight_checks())
        except Exception as exc:  # pragma: no cover - defensive UI path
            self.failed.emit(str(exc))


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
        self._preflight_running = False
        self._is_stopping = False  # Track stopping state for UI feedback
        self._stopping_since: float = 0.0  # Timestamp for timeout
        self._was_healthy = False  # Track crash detection
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
        if self._preflight_running:
            return

        self._preflight_running = True
        self.statusBar().showMessage("Running preflight checks…")
        self._preflight_thread = QThread()
        self._preflight_worker = _PreflightWorker()
        self._preflight_worker.moveToThread(self._preflight_thread)
        self._preflight_thread.started.connect(self._preflight_worker.run)
        self._preflight_worker.finished.connect(self._on_preflight_finished)
        self._preflight_worker.failed.connect(self._on_preflight_failed)
        self._preflight_worker.finished.connect(self._preflight_thread.quit)
        self._preflight_worker.failed.connect(self._preflight_thread.quit)
        self._preflight_worker.finished.connect(
            self._preflight_worker.deleteLater
        )
        self._preflight_worker.failed.connect(
            self._preflight_worker.deleteLater
        )
        self._preflight_thread.finished.connect(
            self._preflight_thread.deleteLater
        )
        self._preflight_thread.start()

    def _on_preflight_finished(self, result) -> None:
        """Persist completed preflight results and refresh the UI."""
        self._preflight_result = result
        self._preflight_running = False

        # Handle settings-specific status messages
        if getattr(self, "_settings_just_saved", False):
            self._settings_just_saved = False
            if result.passed:
                self.statusBar().showMessage(
                    "Settings saved — all checks passed. " "Restart to apply.",
                    5000,
                )
            else:
                failure_count = len(result.failures)
                self.statusBar().showMessage(
                    f"Settings saved — {failure_count} check(s) failed. "
                    "Restart to apply.",
                    10000,
                )
                failures = "\n".join(
                    f"  • {c.name}: {c.error}" for c in result.failures
                )
                self.ui.pushButton_SettingsSave.setToolTip(
                    f"Preflight checks failed:\n{failures}"
                )
            self._update_server_status()
            return

        if getattr(self, "_settings_just_loaded", False):
            self._settings_just_loaded = False
            if result.passed:
                self.statusBar().showMessage(
                    "Settings loaded — all checks passed. "
                    "Server can be started.",
                    5000,
                )
            else:
                failure_count = len(result.failures)
                self.statusBar().showMessage(
                    f"Settings loaded — {failure_count} preflight check(s) "
                    "failed. Fix issues before starting the server.",
                    10000,
                )
                failures = "\n".join(
                    f"  • {c.name}: {c.error}" for c in result.failures
                )
                self.ui.pushButton_SettingsSave.setToolTip(
                    f"Preflight checks failed:\n{failures}"
                )
            self._update_server_status()
            return

        self._update_server_status()

    def _on_preflight_failed(self, error: str) -> None:
        """Recover UI state when background preflight execution fails."""
        self._preflight_running = False
        self.statusBar().showMessage(f"Preflight failed: {error}")
        QMessageBox.warning(
            self,
            "Preflight Failed",
            f"Preflight checks failed unexpectedly:\n{error}",
        )
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

        Stops the Chainlit webserver off the GUI thread to avoid blocking.
        The llama-server inference processes are stopped automatically by
        the web UI via the Chainlit ``on_app_shutdown`` lifecycle hook.
        """
        # Confirm before stopping a healthy server
        status = self._server_manager.get_status()
        if status.healthy:
            reply = QMessageBox.question(
                self,
                "Confirm Stop",
                "Are you sure you want to stop the server?\n"
                "Active chat sessions will be disconnected.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Disable both buttons immediately to prevent double-clicks
        self.ui.pushButton_ServiceStop.setEnabled(False)
        self.ui.pushButton_ServiceStart.setEnabled(False)
        self._is_stopping = True
        self._stopping_since = time.monotonic()
        self.statusBar().showMessage("Stopping Aria server\u2026")

        self._stop_thread = QThread()
        self._stop_worker = _StopWorker(self._server_manager)
        self._stop_worker.moveToThread(self._stop_thread)
        self._stop_thread.started.connect(self._stop_worker.run)
        self._stop_worker.finished.connect(self._stop_thread.quit)
        self._stop_worker.failed.connect(self._stop_thread.quit)
        self._stop_worker.finished.connect(self._stop_worker.deleteLater)
        self._stop_worker.failed.connect(self._stop_worker.deleteLater)
        self._stop_thread.finished.connect(self._stop_thread.deleteLater)
        self._stop_thread.finished.connect(self._on_stop_finished)
        self._stop_worker.failed.connect(self._on_stop_failed)
        self._stop_thread.start()

    def _on_stop_finished(self):
        """Called when the stop worker thread finishes."""
        self._is_stopping = False
        self._stopping_since = 0.0
        self._update_server_status()

    def _on_stop_failed(self, error: str) -> None:
        """Called when the stop worker encounters an error."""
        self._is_stopping = False
        self._stopping_since = 0.0
        self.statusBar().showMessage(f"Stop failed: {error}")
        QMessageBox.warning(
            self,
            "Stop Failed",
            f"Failed to stop the server:\n{error}",
        )
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

        Four distinct states are shown:
        - Stopped (red): process is not running
        - Starting\u2026 (orange): process is alive but /health not yet responding
        - Stopping\u2026 (orange): process is alive during shutdown
        - Running (green): process is alive and /health returns HTTP 200
        """
        status = self._server_manager.get_status()

        _BADGE_BASE = "color: white; font-size: 13pt; padding: 4px 14px; border-radius: 6px;"
        if status.healthy:
            self._was_healthy = True
            self.ui.label_ServiceStatus.setText("Running")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #2e7d32; {_BADGE_BASE} }}"
            )
            self.statusBar().clearMessage()
        elif status.running:
            # Check if we're in stopping state to show appropriate message
            if self._is_stopping:
                self.ui.label_ServiceStatus.setText("Stopping\u2026")
                self.ui.label_ServiceStatus.setStyleSheet(
                    f"QLabel {{ background-color: #e65100; {_BADGE_BASE} }}"
                )
                self.statusBar().showMessage("Stopping Aria server\u2026")
            else:
                self.ui.label_ServiceStatus.setText("Starting\u2026")
                self.ui.label_ServiceStatus.setStyleSheet(
                    f"QLabel {{ background-color: #e65100; {_BADGE_BASE} }}"
                )
                self.statusBar().showMessage(
                    "Starting Aria server\u2026 this may take a few minutes."
                )
        else:
            # Auto-reset stopping state when server is confirmed stopped
            if self._is_stopping:
                self._is_stopping = False
                self._stopping_since = 0.0
            crashed = self._was_healthy
            self._was_healthy = False
            self.ui.label_ServiceStatus.setText("Stopped")
            self.ui.label_ServiceStatus.setStyleSheet(
                f"QLabel {{ background-color: #c62828; {_BADGE_BASE} }}"
            )
            if crashed:
                # Crash message takes priority
                self.statusBar().showMessage(
                    "Server stopped unexpectedly. " "Check logs for details.",
                    10000,
                )
            elif (
                self._preflight_result is not None
                and not self._preflight_result.passed
            ):
                n = len(self._preflight_result.failures)
                self.statusBar().showMessage(
                    f"Cannot start: {n} preflight check(s) failed. "
                    "Hover over Start button for details."
                )
            else:
                self.statusBar().clearMessage()

        self.ui.label_ServicePID.setText(
            str(status.pid) if status.pid else "-"
        )

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
            self.ui.label_ServiceUptime.setText(
                f"{hours}h {minutes}m {seconds}s"
            )
        else:
            self.ui.label_ServiceUptime.setText("-")

        preflight_ok = (
            self._preflight_result is not None
            and self._preflight_result.passed
        )
        can_start = not status.running and preflight_ok
        # Safety timeout: reset stopping state after 30 seconds
        if self._is_stopping and time.monotonic() - self._stopping_since > 30:
            self._is_stopping = False
            self._stopping_since = 0.0
        if self._is_stopping:
            self.ui.pushButton_ServiceStart.setEnabled(False)
            self.ui.pushButton_ServiceStop.setEnabled(False)
        else:
            self.ui.pushButton_ServiceStart.setEnabled(
                can_start and not self._preflight_running
            )
            self.ui.pushButton_ServiceStop.setEnabled(status.running)
        self.ui.pushButton_ServiceOpen.setEnabled(status.healthy)

        if self._preflight_running:
            self.ui.pushButton_ServiceStart.setToolTip(
                "Preflight checks are running…"
            )
        elif not status.running and not preflight_ok:
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

        # Keep tray icon in sync
        tray = getattr(self, "_tray_icon", None)
        if tray is not None:
            tray.update_status(running=status.running, healthy=status.healthy)
