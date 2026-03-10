"""Aria GUI application.

This package provides the graphical user interface for the Aria application,
including the main window and various dialogs.

Example usage:
    from aria.gui import main

    main()
"""

import sys

from PySide6.QtWidgets import QApplication

__all__ = ["main"]


def main():
    """Launch the Aria GUI application."""
    from aria.initializer import is_initialized, run_initialization

    if not is_initialized():
        run_initialization()

    from aria.gui.windows import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Aria")
    app.setApplicationDisplayName("Aria")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
