"""Main window for the Aria application."""

import stat
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import QApplication, QMainWindow

from aria.config.folders import Debug
from aria.config.models import Chat
from aria.gui.dialogs import AboutDialog
from aria.gui.tray import TrayIcon
from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.gui.windows.server_handlers import ServerHandlersMixin
from aria.gui.windows.user_handlers import UserHandlersMixin


def human_size(path: Path) -> str:
    """Convert file size to human-readable format.

    Args:
        path: Path to the file

    Returns:
        Human-readable size string (e.g., "1.5 MiB") or empty string
        if the file doesn't exist.
    """
    if not path.exists():
        return ""
    size_bytes = path.stat().st_size
    size = float(size_bytes)
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi"]:
        if size < 1024:
            return f"{size:.1f} {unit}B"
        size /= 1024
    return f"{size:.1f} EiB"


def friendly_permissions(path: Path) -> dict[str, list[str]]:
    """
    Returns a dict like:
    {
        "Owner":  ["Read", "Write", "Execute"],
        "Group":  ["Read"],
        "Others": ["Read"]
    }
    or with empty list if no permissions
    """
    if not path.exists():
        return {"Owner": [], "Group": [], "Others": []}

    try:
        mode = path.stat().st_mode

        def get_perms(r: int, w: int, x: int) -> list[str]:
            perms = []
            if mode & r:
                perms.append("Read")
            if mode & w:
                perms.append("Write")
            if mode & x:
                perms.append("Execute")
            return perms

        return {
            "Owner": get_perms(stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR),
            "Group": get_perms(stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP),
            "Others": get_perms(stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH),
        }

    except Exception:
        return {"Owner": [], "Group": [], "Others": []}


class MainWindow(
    UserHandlersMixin,
    ServerHandlersMixin,
    QMainWindow,
):
    """Main application window with user management and logs."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Hide redundant title label (window title bar shows "Aria")
        self.ui.label_title.hide()

        # Increase minimum height so content is readable
        self.setMinimumSize(600, 650)

        # Make form fields expand to fill available width
        from PySide6.QtWidgets import QFormLayout

        self.ui.formLayout_remote.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        # Set button properties per design system
        self.ui.pushButton_CreateUser.setProperty("primary", True)
        self.ui.pushButton_ServiceStart.setProperty("primary", True)
        self.ui.pushButton_DeleteUser.setProperty("danger", True)
        self.ui.pushButton_ServiceStop.setProperty("warning", True)

        self._connect_menu_signals()
        self._connect_tab_signals()
        self._connect_user_management_signals()

        self._init_server_manager()
        self._connect_server_signals()
        self.ui.pushButton_SaveSettings.clicked.connect(self._save_remote_settings)

        self.load_overview()
        self._run_preflight()

        # Initialize connection mode based on platform
        self._init_connection_mode()

        self._tray_icon = TrayIcon(self)
        self._force_quit = False
        self._wizard: object = None

        # Incremental log reading state
        self._log_file_offset: int = 0
        self._log_filter_active: bool = False

        # Responsive layout state
        self._narrow_mode: bool = False
        self._setup_responsive_layouts()

    def _connect_menu_signals(self):
        """Connect menu action signals."""
        self.ui.actionQuit.triggered.connect(self._force_close)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)

    def _force_close(self):
        """Set force-quit flag and close the window."""
        self._force_quit = True
        self.close()

    def _connect_tab_signals(self):
        """Connect tab-related signals."""
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.ui.pushButton_RefreshLogs.clicked.connect(self.load_logs)
        self.ui.pushButton_AutoRefresh.clicked.connect(self.toggle_auto_refresh)
        self.ui.lineEdit_LogSearch.textChanged.connect(self.load_logs)
        self.ui.comboBox_LogFilter.currentTextChanged.connect(self.load_logs)

        self._logs_timer = QTimer()
        self._logs_timer.timeout.connect(self.load_logs)

    def _connect_user_management_signals(self):
        """Connect user management button signals."""
        self.ui.pushButton_CreateUser.clicked.connect(self.on_create_user_clicked)
        self.ui.pushButton_EditUser.clicked.connect(self.on_edit_user_clicked)
        self.ui.pushButton_DeleteUser.clicked.connect(self.on_delete_user_clicked)

        self.ui.pushButton_CreateUser.setEnabled(False)
        self.ui.lineEdit_UserName.textChanged.connect(self.validate_create_fields)
        self.ui.lineEdit_UserEmail.textChanged.connect(self.validate_create_fields)
        self.ui.lineEdit_UserPassword.textChanged.connect(self.validate_create_fields)
        self.ui.lineEdit_UserPassword.textChanged.connect(
            self._update_password_strength
        )
        self.ui.lineEdit_UserConfirmPassword.textChanged.connect(
            self.validate_create_fields
        )

        self.ui.pushButton_EditUser.setEnabled(False)
        self.ui.pushButton_DeleteUser.setEnabled(False)
        self.ui.listWidget_CurrentUsers.itemSelectionChanged.connect(
            self.validate_user_selection
        )

    def _set_auto_refresh_running(self, running: bool):
        """Update the Auto-Refresh button to reflect the current timer state.

        Args:
            running: True if auto-refresh is active, False if paused.
        """
        if running:
            self.ui.pushButton_AutoRefresh.setText("Pause")
        else:
            self.ui.pushButton_AutoRefresh.setText("Resume")

    def toggle_auto_refresh(self):
        """Toggle the auto-refresh timer on or off."""
        if self._logs_timer.isActive():
            self._logs_timer.stop()
            self._set_auto_refresh_running(False)
        else:
            self.load_logs()
            self._logs_timer.start(5000)
            self._set_auto_refresh_running(True)

    @staticmethod
    def _tail_file(path: Path, max_lines: int = 500) -> list[str]:
        """Read the last *max_lines* lines from *path* efficiently.

        Instead of reading the entire file (which can be very large for a log
        that grows continuously), we seek to the end and read backwards in
        blocks until we have collected enough newline characters.

        Returns:
            A list of at most *max_lines* lines (without trailing newlines).
            An empty list if the file does not exist or cannot be read.
        """
        try:
            with open(path, "rb") as f:
                f.seek(0, 2)  # jump to end
                file_size = f.tell()
                if file_size == 0:
                    return []

                block_size = 8192
                blocks: list[bytes] = []
                remaining = file_size
                newline_count = 0

                while remaining > 0:
                    read_size = min(block_size, remaining)
                    remaining -= read_size
                    f.seek(remaining)
                    block = f.read(read_size)
                    blocks.append(block)
                    newline_count += block.count(b"\n")
                    # +1 because the last line may not end with \n
                    if newline_count >= max_lines + 1:
                        break

                content = b"".join(reversed(blocks))
                lines = content.decode("utf-8", errors="replace").splitlines()
                return lines[-max_lines:]
        except (FileNotFoundError, OSError):
            return []

    def _log_text_color(self) -> QColor:
        """Return the default log text color for the styled light log view."""
        return QColor("#111318")

    def _log_muted_color(self) -> QColor:
        """Return a muted but readable color for INFO lines."""
        return QColor("#62666B")

    def _format_log_line(self, stripped: str):
        """Return (level, color) for a log line."""
        if " ERROR " in stripped or stripped.startswith("ERROR"):
            return "ERROR", QColor("#DC2626")  # --error
        if " WARNING " in stripped or stripped.startswith("WARNING"):
            return "WARNING", QColor("#D97706")  # --warning
        if " INFO " in stripped or stripped.startswith("INFO"):
            return "INFO", self._log_muted_color()
        return "", self._log_text_color()

    def _line_matches_filter(
        self, stripped: str, level: str, search: str, level_filter: str
    ) -> bool:
        """Return True if *stripped* passes both filters."""
        if level_filter == "ERROR" and level != "ERROR":
            return False
        if level_filter == "WARNING" and level not in ("ERROR", "WARNING"):
            return False
        if level_filter == "INFO" and level not in (
            "ERROR",
            "WARNING",
            "INFO",
        ):
            return False
        if search and search not in stripped.lower():
            return False
        return True

    def _append_log_lines(self, lines: list[str]) -> None:
        """Append filtered, color-coded lines to the log viewer."""
        search_text = self.ui.lineEdit_LogSearch.text().lower()
        level_filter = self.ui.comboBox_LogFilter.currentText()

        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                continue
            level, color = self._format_log_line(stripped)
            if not self._line_matches_filter(
                stripped, level, search_text, level_filter
            ):
                continue
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor = self.ui.textEdit_Logs.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(stripped + "\n", fmt)

        self.ui.textEdit_Logs.verticalScrollBar().setValue(
            self.ui.textEdit_Logs.verticalScrollBar().maximum()
        )

    def load_logs(self):
        """Load logs with color coding, search, and level filter.

        On first call or when a search/filter is active, reads the last
        500 lines.  During auto-refresh (no active filter), only new bytes
        since the last read are appended — avoiding a full re-read of
        potentially large log files.
        """
        if not Debug.logs_path.exists():
            self.ui.textEdit_Logs.setPlainText("Log file not found.")
            self._log_file_offset = 0
            return

        search_text = self.ui.lineEdit_LogSearch.text().lower()
        level_filter = self.ui.comboBox_LogFilter.currentText()
        has_filter = bool(search_text) or level_filter != "All"
        filter_changed = has_filter != self._log_filter_active

        if has_filter or filter_changed or self._log_file_offset == 0:
            # Full reload: tail the file and reset offset
            lines = self._tail_file(Debug.logs_path)
            self.ui.textEdit_Logs.clear()
            self._append_log_lines(lines)
            # Track where we are in the file
            try:
                self._log_file_offset = Debug.logs_path.stat().st_size
            except OSError:
                self._log_file_offset = 0
        else:
            # Incremental: read only new bytes
            try:
                file_size = Debug.logs_path.stat().st_size
            except OSError:
                return

            if file_size < self._log_file_offset:
                # File was truncated/rotated — full reload
                self._log_file_offset = 0
                self.load_logs()
                return

            if file_size == self._log_file_offset:
                return  # No new data

            new_lines: list[str] = []
            try:
                with open(Debug.logs_path, "rb") as f:
                    f.seek(self._log_file_offset)
                    new_data = f.read()
                    self._log_file_offset = file_size
                if new_data:
                    text = new_data.decode("utf-8", errors="replace")
                    new_lines = text.splitlines()
            except OSError:
                return

            if new_lines:
                self._append_log_lines(new_lines)

        self._log_filter_active = has_filter

    def load_overview(self):
        """Load overview tab content - local status."""
        from aria.config.api import Vllm

        # Update local status
        self.ui.label_LocalEndpointValue.setText(Chat.api_url)

        # Populate remote settings from config
        self.ui.lineEdit_EndpointUrl.setText(Chat.api_url)
        self.ui.lineEdit_ApiKey.setText(Vllm.api_key)
        self.ui.lineEdit_Model.setText(Chat.model)
        # Select matching context size in combo box
        try:
            idx = self._CONTEXT_VALUES.index(Vllm.chat_context_size)
        except ValueError:
            idx = 1  # default to 32K
        self.ui.comboBox_ContextSize.setCurrentIndex(idx)

    # Ordered list matching comboBox_ContextSize item indices
    _CONTEXT_VALUES: list[int] = [
        24576,
        32768,
        49152,
        65536,
        131072,
        262144,
        393216,
        524288,
        786432,
        1048576,
    ]

    # Context size → recommended TOKEN_LIMIT_RATIO
    _RATIO_TABLE: dict[int, float] = {
        24576: 0.85,
        32768: 0.80,
        49152: 0.75,
        65536: 0.70,
        131072: 0.60,
        262144: 0.50,
        393216: 0.45,
        524288: 0.40,
        786432: 0.35,
        1048576: 0.30,
    }

    def _save_remote_settings(self):
        """Save remote settings from the UI back to the .env file."""
        from pathlib import Path

        from aria.config import reload_env
        from aria.helpers.dotenv import parse_dotenv, write_dotenv

        env_path = Path.home() / ".aria" / ".env"
        values, raw_lines = parse_dotenv(env_path)

        ctx_size = self._CONTEXT_VALUES[self.ui.comboBox_ContextSize.currentIndex()]

        values["CHAT_OPENAI_API"] = self.ui.lineEdit_EndpointUrl.text()
        values["ARIA_VLLM_API_KEY"] = self.ui.lineEdit_ApiKey.text()
        values["CHAT_MODEL"] = self.ui.lineEdit_Model.text()
        values["CHAT_CONTEXT_SIZE"] = str(ctx_size)

        ratio = self._RATIO_TABLE.get(ctx_size, 0.80)
        values["TOKEN_LIMIT_RATIO"] = f"{ratio:.2f}"

        write_dotenv(env_path, values, raw_lines)
        reload_env()

        self.statusBar().showMessage("Settings saved.", 5000)

    def _init_connection_mode(self):
        """Detect platform and set appropriate default connection mode.

        On macOS, vLLM is not supported, so default to Remote API mode.
        Connects radio button signals for runtime toggling.
        """
        import sys

        # Connect radio button signals
        self.ui.radioButton_RemoteMode.toggled.connect(self._on_connection_mode_toggled)

        if sys.platform == "darwin":
            self.ui.radioButton_RemoteMode.setChecked(True)
            self.ui.radioButton_LocalMode.setEnabled(False)
            self.ui.radioButton_LocalMode.setToolTip("vLLM is not supported on macOS.")
        else:
            self.ui.radioButton_LocalMode.setChecked(True)

    def _on_connection_mode_toggled(self, checked: bool):
        """Handle connection mode radio button toggle.

        The Remote radio emits toggled(True) when selected.
        """
        if not checked:
            return  # Ignore unchecked signal from the other radio
        remote = self.ui.radioButton_RemoteMode.isChecked()
        self.ui.frame_RemoteSettings.setVisible(remote)
        self.ui.frame_LocalStatus.setVisible(not remote)

    def on_tab_changed(self, index: int):
        """Handle tab changes - load content when tabs are selected."""
        match self.ui.tabWidget.widget(index):
            case self.ui.tab_home:
                self._logs_timer.stop()
                self.statusBar().clearMessage()
                self.load_overview()
                self._run_preflight()
            case self.ui.tab_users:
                self._logs_timer.stop()
                self.statusBar().clearMessage()
                self.load_users()
            case self.ui.tab_logs:
                self.load_logs()
                self._logs_timer.start(5000)
                self._set_auto_refresh_running(True)
                self.statusBar().showMessage(str(Debug.logs_path))
            case _:
                self._logs_timer.stop()
                self.statusBar().clearMessage()

    def _setup_responsive_layouts(self) -> None:
        """Initialize responsive layout settings.

        The Home tab uses dynamic direction switching handled in resizeEvent.
        """
        pass

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Handle window resize events."""
        super().resizeEvent(event)

    def show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Minimize to tray or clean up on forced quit.

        When the user closes the window, it is hidden and continues
        running in the system tray.  A forced quit (via tray menu or
        Ctrl+Q) sets ``_force_quit`` to True to skip this behaviour.
        """
        if not getattr(self, "_force_quit", False):
            event.ignore()
            self.hide()
            return

        # Close wizard if open (it runs a nested event loop)
        wizard = getattr(self, "_wizard", None)
        if wizard is not None:
            wizard.reject()

        # Stop server before closing
        if hasattr(self, "_server_manager"):
            self._server_manager.stop()

        if hasattr(self, "_server_timer"):
            self._server_timer.stop()

        # Hide tray icon so QApplication can exit
        if hasattr(self, "_tray_icon"):
            self._tray_icon._tray.hide()

        super().closeEvent(event)
        QApplication.quit()
