"""User management handlers for the MainWindow."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox, QWidget
from sqlalchemy import select

from aria.cli import get_db_session
from aria.db.auth import hash_password
from aria.db.models import User
from aria.gui.dialogs import EditUserDialog
from aria.gui.ui.mainwindow import Ui_MainWindow

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserHandlersMixin:
    """Mixin class providing user management functionality for MainWindow.

    This mixin expects to be combined with a QMainWindow that has a `ui`
    attribute of type Ui_MainWindow.
    """

    ui: Ui_MainWindow

    def load_users(self) -> None:
        """Load users from database into the list widget."""
        try:
            with get_db_session() as session:
                users = session.execute(select(User)).scalars().all()
                self.ui.listWidget_CurrentUsers.clear()
                for user in users:
                    self.ui.listWidget_CurrentUsers.addItem(user.identifier)
                if not users:
                    item = QListWidgetItem(
                        "No users yet. Create one to get started."
                    )
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    item.setForeground(QColor("#999999"))
                    self.ui.listWidget_CurrentUsers.addItem(item)
        except Exception as e:
            self.ui.statusBar.showMessage(f"Error listing users: {e}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Return True if *email* has a basic valid format."""
        return bool(_EMAIL_RE.match(email))

    @staticmethod
    def _password_strength(password: str) -> tuple[str, str]:
        """Return (label, color) for password strength."""
        if not password:
            return "", ""
        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"[0-9]", password):
            score += 1
        if re.search(r"[^A-Za-z0-9]", password):
            score += 1
        if score <= 2:
            return "Weak", "#c62828"
        elif score <= 3:
            return "Fair", "#e65100"
        else:
            return "Strong", "#2e7d32"

    def _update_password_strength(self) -> None:
        """Update the password strength indicator label."""
        label, color = self._password_strength(
            self.ui.lineEdit_UserPassword.text()
        )
        self.ui.label_PasswordStrength.setText(label)
        if color:
            self.ui.label_PasswordStrength.setStyleSheet(
                f"color: {color}; font-weight: bold;"
            )
        else:
            self.ui.label_PasswordStrength.setStyleSheet("")

    def validate_create_fields(self) -> None:
        """Enable Create User button only when all fields are filled."""
        name = self.ui.lineEdit_UserName.text().strip()
        email = self.ui.lineEdit_UserEmail.text().strip()
        password = self.ui.lineEdit_UserPassword.text()
        confirm = self.ui.lineEdit_UserConfirmPassword.text()

        email_valid = self._is_valid_email(email) if email else False
        all_filled = bool(
            name and email_valid and password and password == confirm
        )
        self.ui.pushButton_CreateUser.setEnabled(all_filled)

    def validate_user_selection(self) -> None:
        """Enable Edit and Delete buttons when a user is selected."""
        has_selection = bool(self.ui.listWidget_CurrentUsers.selectedItems())
        self.ui.pushButton_EditUser.setEnabled(has_selection)
        self.ui.pushButton_DeleteUser.setEnabled(has_selection)

    def on_create_user_clicked(self) -> None:
        """Handle create user button click."""
        role = "user"
        name = self.ui.lineEdit_UserName.text().strip()
        identifier = self.ui.lineEdit_UserEmail.text().strip()
        password = self.ui.lineEdit_UserPassword.text()

        if not self._is_valid_email(identifier):
            self.show_error("Please enter a valid email address")
            return

        if password != self.ui.lineEdit_UserConfirmPassword.text():
            self.show_error("Passwords do not match")
            return

        try:
            with get_db_session() as session:
                existing = session.execute(
                    select(User).where(User.identifier == identifier)
                ).scalar_one_or_none()

                if existing:
                    self.show_error("User already exists")
                    return

                session.add(
                    User(
                        id=str(uuid.uuid4()),
                        display_name=name,
                        identifier=identifier,
                        metadata_=json.dumps(
                            {"role": role, "created_by": "cli"}
                        ),
                        password=hash_password(password),
                        createdAt=datetime.now().isoformat() + "Z",
                    )
                )
            # Session committed — now refresh UI
            self.load_users()
            self.ui.lineEdit_UserName.clear()
            self.ui.lineEdit_UserEmail.clear()
            self.ui.lineEdit_UserPassword.clear()
            self.ui.lineEdit_UserConfirmPassword.clear()
            self.ui.label_PasswordStrength.setText("")
            self.ui.label_PasswordStrength.setStyleSheet("")
            self.ui.statusBar.showMessage(
                f"User '{identifier}' created.", 3000
            )
        except Exception as e:
            self.ui.statusBar.showMessage(f"Error creating user: {e}")

    def on_edit_user_clicked(self) -> None:
        """Open edit dialog for the selected user."""
        selected_items = self.ui.listWidget_CurrentUsers.selectedItems()
        if not selected_items:
            self.show_error("Please select a user to edit")
            return

        identifier = selected_items[0].text()
        try:
            with get_db_session() as session:
                user = session.execute(
                    select(User).where(User.identifier == identifier)
                ).scalar_one_or_none()
                if user:
                    # self is MainWindow which inherits from QWidget
                    parent_widget: QWidget = self  # type: ignore[assignment]
                    dialog = EditUserDialog(parent_widget, user)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        self.load_users()
        except Exception as e:
            self.ui.statusBar.showMessage(f"Error editing user: {e}")

    def on_delete_user_clicked(self) -> None:
        """Handle delete user button click with confirmation."""
        selected_items = self.ui.listWidget_CurrentUsers.selectedItems()
        if not selected_items:
            self.show_error("Please select a user to delete")
            return

        identifier = selected_items[0].text()

        # self is MainWindow which inherits from QWidget
        parent_widget: QWidget = self  # type: ignore[assignment]

        # Show confirmation dialog
        msg_box = QMessageBox(parent_widget)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(
            f"Are you sure you want to delete user '{identifier}'?"
        )
        msg_box.setInformativeText("This action cannot be undone.")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                deleted = False
                with get_db_session() as session:
                    user = session.execute(
                        select(User).where(User.identifier == identifier)
                    ).scalar_one_or_none()
                    if user:
                        session.delete(user)
                        deleted = True
                # Session committed — now refresh UI
                if deleted:
                    self.load_users()
                    self.ui.statusBar.showMessage(
                        f"User '{identifier}' deleted.", 3000
                    )
            except Exception as e:
                self.ui.statusBar.showMessage(f"Error deleting user: {e}")

    def show_error(self, message: str) -> None:
        """Display an error message box."""
        # self is MainWindow which inherits from QWidget
        parent_widget: QWidget = self  # type: ignore[assignment]

        msg_box = QMessageBox(parent_widget)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
