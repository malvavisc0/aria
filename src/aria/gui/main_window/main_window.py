"""Main window for the Aria application."""

from collections import deque

from PySide6.QtWidgets import QMainWindow

from aria.config.folders import Debug
from aria.gui.dialogs import AboutDialog
from aria.gui.main_window.user_handlers import UserHandlersMixin
from aria.gui.ui.mainwindow import Ui_MainWindow


class MainWindow(UserHandlersMixin, QMainWindow):
    """Main application window with user management and logs."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._connect_menu_signals()
        self._connect_tab_signals()
        self._connect_user_management_signals()

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
        self.ui.pushButton_CreateUser.clicked.connect(self.on_create_user_clicked)
        self.ui.pushButton_EditUser.clicked.connect(self.on_edit_user_clicked)
        self.ui.pushButton_DeleteUser.clicked.connect(self.on_delete_user_clicked)

        # Enable/disable Create User button based on field content
        self.ui.pushButton_CreateUser.setEnabled(False)
        self.ui.lineEdit_UserName.textChanged.connect(self.validate_create_fields)
        self.ui.lineEdit_UserEmail.textChanged.connect(self.validate_create_fields)
        self.ui.lineEdit_UserPassword.textChanged.connect(self.validate_create_fields)

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

    def on_tab_changed(self, index: int):
        """Handle tab changes - load content when tabs are selected."""
        match self.ui.tabWidget.widget(index):
            case self.ui.tab_users:
                self.load_users()
            case self.ui.tab_logs:
                self.load_logs()
            case _:
                pass

    def show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
