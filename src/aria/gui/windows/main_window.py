"""Main window for the Aria application."""

import stat
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QIcon, QPalette, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aria.config.database import ChromaDB, SQLite
from aria.config.folders import Debug
from aria.config.models import Chat
from aria.gui.dialogs import AboutDialog
from aria.gui.tray import TrayIcon
from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.gui.windows.server_handlers import ServerHandlersMixin
from aria.gui.windows.settings_handlers import SettingsHandlersMixin
from aria.gui.windows.setup_handlers import SetupHandlersMixin
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
    SetupHandlersMixin,
    SettingsHandlersMixin,
    QMainWindow,
):
    """Main application window with user management and logs."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._connect_menu_signals()
        self._connect_tab_signals()
        self._connect_user_management_signals()

        self._init_server_manager()
        self._connect_server_signals()

        self._connect_setup_signals()
        self._connect_settings_signals()

        self.load_overview()
        self.load_setup()
        self._run_preflight()

        self._tray_icon = TrayIcon(self)
        self._force_quit = False

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
            self.ui.pushButton_AutoRefresh.setText("Pause Auto-Refresh")
            self.ui.pushButton_AutoRefresh.setIcon(
                QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause))
            )
        else:
            self.ui.pushButton_AutoRefresh.setText("Resume Auto-Refresh")
            self.ui.pushButton_AutoRefresh.setIcon(
                QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
            )

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
        """Return the default text color from the application palette.

        This ensures log text is readable on both light and dark system
        themes instead of using a hardcoded color like ``#333333`` that
        becomes invisible on dark backgrounds.
        """
        palette = QApplication.palette()
        return palette.color(QPalette.ColorRole.WindowText)

    def _log_muted_color(self) -> QColor:
        """Return a muted version of the palette text color for INFO lines.

        Blends the palette's text and window (background) colors at 55%
        opacity so the result is always legible regardless of theme.
        """
        palette = QApplication.palette()
        fg = palette.color(QPalette.ColorRole.WindowText)
        bg = palette.color(QPalette.ColorRole.Window)
        ratio = 0.55
        return QColor(
            int(fg.red() * ratio + bg.red() * (1 - ratio)),
            int(fg.green() * ratio + bg.green() * (1 - ratio)),
            int(fg.blue() * ratio + bg.blue() * (1 - ratio)),
        )

    def _format_log_line(self, stripped: str):
        """Return (level, color) for a log line."""
        if " ERROR " in stripped or stripped.startswith("ERROR"):
            return "ERROR", QColor("#c62828")
        if " WARNING " in stripped or stripped.startswith("WARNING"):
            return "WARNING", QColor("#e65100")
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
        self.ui.label_DebugLogsPath.setText(str(Debug.logs_path.absolute()))

        self.ui.label_DatabaseLocation.setText(str(SQLite.file_path.absolute()))
        db_exists = SQLite.file_path.exists()
        if db_exists:
            self.ui.label_DatabaseFileExists.setText("Yes")
            self.ui.label_DatabaseSize.setText(human_size(SQLite.file_path))
            permissions = "+".join(friendly_permissions(SQLite.file_path)["Owner"])
            self.ui.label_DatabasePermissions.setText(permissions)
        else:
            self.ui.label_DatabaseFileExists.setText("No")
            self.ui.label_DatabaseSize.setText("-")
            self.ui.label_DatabasePermissions.setText("-")

        self.ui.label_LLMChatAPIURL.setText(
            f'<a href="{Chat.api_url}">{Chat.api_url}</a>'
        )
        self.ui.label_VectorDB.setText(str(ChromaDB.db_path.absolute()))

    def on_tab_changed(self, index: int):
        """Handle tab changes - load content when tabs are selected."""
        match self.ui.tabWidget.widget(index):
            case self.ui.tab_overview:
                self._logs_timer.stop()
                self.statusBar().clearMessage()
                self.load_overview()
                self._run_preflight()
            case self.ui.tab_setup:
                self._logs_timer.stop()
                self.statusBar().clearMessage()
                self.load_setup()
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
            case self.ui.tab_settings:
                self._logs_timer.stop()
                self.statusBar().clearMessage()
                self.load_settings()
            case _:
                self._logs_timer.stop()
                self.statusBar().clearMessage()

    def _setup_responsive_layouts(self) -> None:
        """Wrap the Setup tab in a QScrollArea for small screens.

        The Overview and Users tabs use dynamic direction switching
        handled in ``resizeEvent``, which is sufficient for responsive
        behaviour without scroll areas.
        """
        # --- Setup tab: wrap in QScrollArea (Responsive #4) ---
        tab_setup = self.ui.tab_setup
        old_layout = tab_setup.layout()
        assert old_layout is not None  # guaranteed by Qt

        scroll = QScrollArea(tab_setup)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(8)

        while old_layout.count():
            item = old_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                inner_layout.addWidget(w)
            else:
                child_layout = item.layout()
                if child_layout is not None:
                    inner_layout.addLayout(child_layout)
                else:
                    inner_layout.addItem(item)

        scroll.setWidget(container)

        # Reuse the emptied layout — Qt won't accept a new layout when
        # the old one still exists on the widget.
        old_layout.setContentsMargins(0, 0, 0, 0)
        old_layout.addWidget(scroll)

        # Initial responsive check
        self._narrow_mode = self.width() < 900
        self._apply_layout_direction()

    def _apply_layout_direction(self) -> None:
        """Switch side-by-side layouts to vertical on narrow windows."""
        direction = (
            QBoxLayout.Direction.TopToBottom
            if self._narrow_mode
            else QBoxLayout.Direction.LeftToRight
        )
        self.ui.horizontalLayout_overview_bottom.setDirection(direction)
        self.ui.horizontalLayout_users.setDirection(direction)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Switch layouts when the window crosses the 900 px threshold."""
        super().resizeEvent(event)
        narrow = self.width() < 900
        if narrow != self._narrow_mode:
            self._narrow_mode = narrow
            self._apply_layout_direction()

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

        if hasattr(self, "_server_timer"):
            self._server_timer.stop()

        if hasattr(self, "_llama_dl_thread"):
            self._cleanup_llama_dl_thread()
        if hasattr(self, "_model_dl_thread"):
            self._cleanup_model_dl_thread()
        if hasattr(self, "_lightpanda_dl_thread"):
            self._cleanup_lightpanda_dl_thread()

        super().closeEvent(event)
