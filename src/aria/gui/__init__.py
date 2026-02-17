import sys
from collections import deque

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QWidget

from aria.config.folders import Debug
from aria.gui.ui.aboutwindow import Ui_AboutDialog
from aria.gui.ui.mainwindow import Ui_MainWindow


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

        # Connect tab change signal to load logs when Logs tab is displayed
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.ui.pushButton_RefreshLogs.clicked.connect(self.load_logs)

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
        current_tab = self.ui.tabWidget.widget(index)

        # Check if this is the Logs tab
        if current_tab == self.ui.tab_logs:
            self.load_logs()

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
