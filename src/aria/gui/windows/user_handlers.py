"""User management handlers for the MainWindow."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget
from sqlalchemy import select

from aria.cli import get_db_session
from aria.db.auth import hash_password
from aria.db.models import User
from aria.gui.dialogs import EditUserDialog
from aria.gui.ui.mainwindow import Ui_MainWindow


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
        except Exception as e:
            self.ui.statusBar.showMessage(f"Error listing users: {e}")

    def validate_create_fields(self) -> None:
        """Enable Create User button only when all fields are filled."""
        name = self.ui.lineEdit_UserName.text().strip()
        email = self.ui.lineEdit_UserEmail.text().strip()
        password = self.ui.lineEdit_UserPassword.text()

        all_filled = bool(name and email and password)
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
