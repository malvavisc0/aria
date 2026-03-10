"""About dialog for the Aria application."""

from PySide6.QtWidgets import QDialog, QWidget

from aria.gui.ui.aboutwindow import Ui_AboutDialog


class AboutDialog(QDialog):
    """Dialog showing application information."""

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)

        self.ui.pushButton_Ok.clicked.connect(self.accept)
