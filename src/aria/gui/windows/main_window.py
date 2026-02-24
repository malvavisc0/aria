"""Main window for the Aria application."""

import stat
from collections import deque
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow

from aria.config.database import ChromaDB, SQLite
from aria.config.folders import Debug
from aria.config.models import Chat, Embeddings, Vision
from aria.gui.dialogs import AboutDialog
from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.gui.windows.server_handlers import ServerHandlersMixin
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


def friendly_permissions(path: Path) -> Dict[str, List[str]]:
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

        def get_perms(r: int, w: int, x: int) -> List[str]:
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
    UserHandlersMixin, ServerHandlersMixin, SetupHandlersMixin, QMainWindow
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

        self.load_overview()
        self.load_setup()
        self._run_preflight()

    def _connect_menu_signals(self):
        """Connect menu action signals."""
        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)

    def _connect_tab_signals(self):
        """Connect tab-related signals."""
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.ui.pushButton_RefreshLogs.clicked.connect(self.load_logs)
        self.ui.pushButton_AutoRefresh.clicked.connect(self.toggle_auto_refresh)

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

    def load_logs(self):
        """Load logs content into the plainTextEdit_Logs widget."""
        try:
            with open(Debug.logs_path, "r") as file:
                last_lines = deque(file, maxlen=500)
                content = "".join(last_lines)
            self.ui.plainTextEdit_Logs.setPlainText(content)
        except FileNotFoundError:
            self.ui.plainTextEdit_Logs.setPlainText("Log file not found.")
        except Exception as e:
            self.ui.plainTextEdit_Logs.setPlainText(f"Error loading logs: {e}")
        self.ui.plainTextEdit_Logs.verticalScrollBar().setValue(
            self.ui.plainTextEdit_Logs.verticalScrollBar().maximum()
        )

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

        self.ui.label_LLMChatAPIURL.setText(Chat.api_url)
        self.ui.label_LLMVisionAPIURL.setText(Vision.api_url)
        self.ui.label_LLMEmbeddingsAPIURL.setText(Embeddings.api_url)
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
            case _:
                self._logs_timer.stop()
                self.statusBar().clearMessage()

    def show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Clean up resources on window close.

        This method is called when the window is closed. It stops the
        server status timer and any active download threads.

        The Chainlit webserver and llama-server inference processes are
        intentionally left running so that the service continues to be
        available after the GUI is closed. Use the Stop button or
        ``aria server stop`` to shut them down explicitly.

        Args:
            event: The QCloseEvent from Qt.
        """
        if hasattr(self, "_server_timer"):
            self._server_timer.stop()

        if hasattr(self, "_llama_dl_thread"):
            self._cleanup_llama_dl_thread()
        if hasattr(self, "_model_dl_thread"):
            self._cleanup_model_dl_thread()

        super().closeEvent(event)
