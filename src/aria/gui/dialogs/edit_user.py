"""Edit user dialog for modifying user information."""

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget
from sqlalchemy import select

from aria.cli import get_db_session
from aria.db.auth import hash_password
from aria.db.models import User
from aria.gui.ui.edituserdialog import Ui_EditUserDialog


class EditUserDialog(QDialog):
    """Dialog for editing user information with optional password change."""

    def __init__(self, parent: QWidget, user: User):
        super().__init__(parent=parent)
        self.ui = Ui_EditUserDialog()
        self.ui.setupUi(self)
        self.user = user

        # Pre-populate name field
        self.ui.lineEdit_Name.setText(user.display_name)

        # Connect buttons
        self.ui.pushButton_Save.clicked.connect(self.save_user)
        self.ui.pushButton_Cancel.clicked.connect(self.reject)

    def save_user(self):
        """Validate and save user changes.

        Performs validation and updates the user in a single database session.
        The session is automatically committed by get_db_session() on success.
        """
        name = self.ui.lineEdit_Name.text().strip()
        password = self.ui.lineEdit_Password.text()

        if not name:
            self.show_error("Name cannot be empty")
            return

        try:
            with get_db_session() as session:
                user = session.execute(
                    select(User).where(User.id == self.user.id)
                ).scalar_one_or_none()
                if user:
                    user.display_name = name
                    if password:
                        user.password = hash_password(password)
                    self.accept()
        except Exception as e:
            self.show_error(f"Failed to save user: {e}")

    def show_error(self, information: str):
        """Display an error message box."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Validation Error")
        msg_box.setText("Cannot save user!")
        msg_box.setInformativeText(information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
