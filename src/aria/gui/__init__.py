"""Aria GUI application.

This package provides the graphical user interface for the Aria application,
including the main window and various dialogs.

Example usage:
    from aria.gui import main

    main()
"""

import sys

from PySide6.QtWidgets import QApplication

from aria.gui.main_window import MainWindow

__all__ = ["MainWindow", "main"]


def main():
    """Launch the Aria GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Aria")
    app.setApplicationDisplayName("Aria")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
