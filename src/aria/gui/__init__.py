import json
import sys
import uuid
from collections import deque
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QMessageBox,
    QWidget,
)
from sqlalchemy import select

from aria.cli import get_db_session
from aria.config.folders import Debug
from aria.db.auth import hash_password
from aria.db.models import User
from aria.gui.ui.aboutwindow import Ui_AboutDialog
from aria.gui.ui.edituserdialog import Ui_EditUserDialog
from aria.gui.ui.mainwindow import Ui_MainWindow


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)

        self.ui.pushButton_Ok.clicked.connect(self.accept)


class EditUserDialog(QDialog):
    """Dialog for editing user information with optional password change."""

    def __init__(self, parent: QWidget, user: User):
        super().__init__(parent=parent)
        self.ui = Ui_EditUserDialog()
        self.ui.setupUi(self)
        self.user = user

        # Pre-populate fields with current user data
        self.ui.lineEdit_Name.setText(user.display_name)
        self.ui.lineEdit_Email.setText(user.identifier)

        # Connect buttons
        self.ui.pushButton_Save.clicked.connect(self.save_user)
        self.ui.pushButton_Cancel.clicked.connect(self.reject)

    def save_user(self):
        """Validate and save user changes."""
        name = self.ui.lineEdit_Name.text().strip()
        email = self.ui.lineEdit_Email.text().strip()
        password = self.ui.lineEdit_Password.text()

        # Validation
        if not name:
            self.show_error("Name cannot be empty")
            return
        if not email:
            self.show_error("Email cannot be empty")
            return

        # Check for duplicate email if email changed
        if email != self.user.identifier:
            with get_db_session() as session:
                existing_user = session.execute(
                    select(User).where(User.identifier == email)
                ).scalar_one_or_none()
                if existing_user:
                    self.show_error("A user with this email already exists")
                    return

        # Update user in database
        with get_db_session() as session:
            user = session.execute(
                select(User).where(User.id == self.user.id)
            ).scalar_one_or_none()
            if user:
                user.display_name = name
                user.identifier = email
                # Only update password if a new one was provided
                if password:
                    user.password = hash_password(password)
                self.accept()

    def show_error(self, information: str):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Validation Error")
        msg_box.setText("Cannot save user!")
        msg_box.setInformativeText(information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)

        # Connect tab change signal to load logs when Logs tab is displayed
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.ui.pushButton_RefreshLogs.clicked.connect(self.load_logs)

        self.ui.pushButton_CreateUser.clicked.connect(self.create_user)
        self.ui.pushButton_EditUser.clicked.connect(self.on_edit_user_clicked)

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
        """Handle tab changes - load logs when the Logs tab is selected."""
        match self.ui.tabWidget.widget(index):
            case self.ui.tab_users:
                self.load_users()
            case self.ui.tab_logs:
                self.load_logs()
            case _:
                pass

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def load_users(self):
        with get_db_session() as session:
            try:
                users = session.execute(select(User)).scalars().all()
                self.ui.listWidget_CurrentUsers.clear()
                for user in users:
                    self.ui.listWidget_CurrentUsers.addItem(user.identifier)
            except Exception as e:
                self.ui.statusBar.showMessage(f"Error listing users: {e}")

    def on_edit_user_clicked(self):
        """Handle edit user button click - open edit dialog for selected user."""
        selected_items = self.ui.listWidget_CurrentUsers.selectedItems()
        if not selected_items:
            self.show_error("Please select a user to edit")
            return

        identifier = selected_items[0].text()
        with get_db_session() as session:
            user = session.execute(
                select(User).where(User.identifier == identifier)
            ).scalar_one_or_none()
            if user:
                dialog = EditUserDialog(self, user)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_users()

    def create_user(self):
        role = "user"
        name = self.ui.lineEdit_UserName.text()
        identifier = self.ui.lineEdit_UserEmail.text()
        password = self.ui.lineEdit_UserPassword.text()
        with get_db_session() as session:
            user = session.execute(
                select(User).where(User.identifier == identifier)
            ).scalar_one_or_none()

            if user:
                self.show_error("User already exists")
            else:
                user = User(
                    id=str(uuid.uuid4()),
                    display_name=name,
                    identifier=identifier,
                    metadata_=json.dumps(
                        {
                            "role": role,
                            "created_by": "cli",
                        }
                    ),
                    password=hash_password(password),
                    createdAt=datetime.now().isoformat() + "Z",
                )
                session.add(user)
                self.load_users()
                self.ui.lineEdit_UserName.clear()
                self.ui.lineEdit_UserEmail.clear()
                self.ui.lineEdit_UserPassword.clear()

    def show_error(self, information: str):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText("An error occurred!")
        msg_box.setInformativeText(information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        msg_box.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Aria")
    app.setApplicationDisplayName("Aria")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
