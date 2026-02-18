"""Main window for the Aria application."""

import stat
from collections import deque
from pathlib import Path
from typing import Dict, List

from PySide6.QtWidgets import QMainWindow

from aria.config.database import SQLite
from aria.config.folders import Debug
from aria.config.models import Chat, Embeddings, Vision
from aria.config.service import Server
from aria.gui.dialogs import AboutDialog
from aria.gui.main_window.user_handlers import UserHandlersMixin
from aria.gui.ui.mainwindow import Ui_MainWindow


def human_size(path: Path) -> str:
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


class MainWindow(UserHandlersMixin, QMainWindow):
    """Main application window with user management and logs."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._connect_menu_signals()
        self._connect_tab_signals()
        self._connect_user_management_signals()

        self.load_overview()

    def _connect_menu_signals(self):
        """Connect menu action signals."""
        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)

    def _connect_tab_signals(self):
        """Connect tab-related signals."""
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.ui.pushButton_RefreshLogs.clicked.connect(self.load_logs)

    def _connect_user_management_signals(self):
        """Connect user management button signals."""
        # Button click handlers
        self.ui.pushButton_CreateUser.clicked.connect(
            self.on_create_user_clicked
        )
        self.ui.pushButton_EditUser.clicked.connect(self.on_edit_user_clicked)
        self.ui.pushButton_DeleteUser.clicked.connect(
            self.on_delete_user_clicked
        )

        # Enable/disable Create User button based on field content
        self.ui.pushButton_CreateUser.setEnabled(False)
        self.ui.lineEdit_UserName.textChanged.connect(
            self.validate_create_fields
        )
        self.ui.lineEdit_UserEmail.textChanged.connect(
            self.validate_create_fields
        )
        self.ui.lineEdit_UserPassword.textChanged.connect(
            self.validate_create_fields
        )

        # Enable/disable Edit and Delete buttons based on user selection
        self.ui.pushButton_EditUser.setEnabled(False)
        self.ui.pushButton_DeleteUser.setEnabled(False)
        self.ui.listWidget_CurrentUsers.itemSelectionChanged.connect(
            self.validate_user_selection
        )

    def load_logs(self):
        """Load logs content into the plainTextEdit_Logs widget."""
        try:
            content = ""
            with open(Debug.logs_path, "r") as file:
                # Use deque with maxlen to efficiently keep only the last N lines
                last_lines = deque(file, maxlen=500)
                content = "".join(last_lines)
            self.ui.plainTextEdit_Logs.setPlainText(content)
        except FileNotFoundError:
            self.ui.plainTextEdit_Logs.setPlainText("Log file not found.")
        except Exception as e:
            self.ui.plainTextEdit_Logs.setPlainText(f"Error loading logs: {e}")

    def load_overview(self):
        self.ui.label_ServiceURL.setText(Server.base_url)

        self.ui.label_DatabaseLocation.setText(
            str(SQLite.file_path.absolute())
        )
        db_exists = SQLite.file_path.exists()
        if db_exists:
            self.ui.label_DatabaseFileExists.setText("Yes")
            self.ui.label_DatabaseSize.setText(human_size(SQLite.file_path))
            permissions = "+".join(
                friendly_permissions(SQLite.file_path)["Owner"]
            )
            self.ui.label_DatabasePermissions.setText(permissions)
        else:
            self.ui.label_DatabaseFileExists.setText("No")

        self.ui.label_LLMChatAPIURL.setText(Chat.api_url)
        self.ui.label_LLMVisionAPIURL.setText(Vision.api_url)
        self.ui.label_LLMEmbeddingsAPIURL.setText(Embeddings.api_url)

    def on_tab_changed(self, index: int):
        """Handle tab changes - load content when tabs are selected."""
        match self.ui.tabWidget.widget(index):
            case self.ui.tab_overview:
                self.load_overview()
            case self.ui.tab_users:
                self.load_users()
            case self.ui.tab_logs:
                self.load_logs()
            case _:
                return

    def show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
