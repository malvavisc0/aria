import sys

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QWidget

from aria.config.folders import Debug
from aria.gui.ui.aboutwindow import Ui_AboutDialog
from aria.gui.ui.mainwindow import Ui_MainWindow


def read_logs() -> str:
    content = ""
    with open(Debug.logs_path, "r") as file:
        content = file.read()
    return content


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)

        self.ui.pushButton_Ok.clicked.connect(self.accept)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)

        # self.ui.plainTextEdit_Logs.showEvent

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Aria")
    app.setApplicationDisplayName("Aria")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
