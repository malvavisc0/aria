"""First-run setup wizard for Aria.

A QWizard-based guided setup that walks new users through:
1. Download AI Engine (llama.cpp)
2. Download AI Model
3. Create admin user
4. Start server

The wizard is shown automatically on first run when no users exist.
"""

from __future__ import annotations

import io
import json
import re
import threading
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)
from sqlalchemy import select

if TYPE_CHECKING:
    from aria.gui.windows.main_window import MainWindow


class _DownloadWorker(QObject):
    """Generic background worker for wizard downloads."""

    log_line = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        import sys

        stream = _WizardStream(self.log_line.emit)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = stream  # type: ignore[assignment]
        sys.stderr = stream  # type: ignore[assignment]
        try:
            self._fn(*self._args, **self._kwargs)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class _WizardStream(io.TextIOBase):
    """A writable text stream that emits each completed line via a callback.

    Thread-safe: a lock protects the internal buffer because the
    ``sys.stdout``/``sys.stderr`` redirect is process-global.
    """

    _LINE_SEP = re.compile(r"[\r\n]+")

    def __init__(self, emit_fn):
        super().__init__()
        self._emit = emit_fn
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, text: str) -> int:  # type: ignore[override]
        with self._lock:
            self._buf += text
            parts = self._LINE_SEP.split(self._buf)
            self._buf = parts[-1]
            for part in parts[:-1]:
                stripped = part.rstrip()
                if stripped:
                    self._emit(stripped)
        return len(text)

    def flush(self) -> None:
        with self._lock:
            if self._buf.strip():
                self._emit(self._buf.strip())
                self._buf = ""


class _EnginePage(QWizardPage):
    """Wizard page for downloading the AI engine (llama.cpp)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Install AI Engine")
        self.setSubTitle(
            "Aria uses vLLM to run AI models locally. "
            "Install the vLLM package to get started."
        )

        layout = QVBoxLayout(self)

        self._status_label = QLabel("Ready to download.")
        layout.addWidget(self._status_label)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(200)
        self._log_view.setStyleSheet("color: #666; font-family: monospace;")
        layout.addWidget(self._log_view)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        self._download_btn = QPushButton("Install vLLM")
        self._download_btn.setIcon(
            QIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoDown))
        )
        self._download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self._download_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._thread: QThread | None = None
        self._worker: _DownloadWorker | None = None
        self._download_done = False

    def _start_download(self):
        from aria.scripts.vllm import install_vllm

        self._download_btn.setEnabled(False)
        self._status_label.setText("Installing…")
        self._log_view.clear()

        self._worker = _DownloadWorker(install_vllm)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_failed)

        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_log(self, line: str):
        self._log_view.appendPlainText(line)

    def _on_finished(self):
        self._download_done = True
        self._download_btn.setEnabled(True)
        self._status_label.setText("✓ vLLM installed successfully!")
        self._status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        self.completeChanged.emit()

    def _on_failed(self, error: str):
        self._download_btn.setEnabled(True)
        self._status_label.setText(f"✗ Download failed: {error}")
        self._status_label.setStyleSheet("color: #c62828; font-weight: bold;")

    def isComplete(self) -> bool:
        return self._download_done

    def cleanupPage(self):
        try:
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(3000)
        except RuntimeError:
            pass
        self._thread = None


class _ModelPage(QWizardPage):
    """Wizard page for downloading an AI model."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Download AI Model")
        self.setSubTitle(
            "Download a chat model to start having conversations with Aria."
        )

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._model_combo = QComboBox()
        self._model_combo.addItems(["chat", "embeddings"])
        form.addRow("Model type:", self._model_combo)
        layout.addLayout(form)

        self._status_label = QLabel("Ready to download.")
        layout.addWidget(self._status_label)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(200)
        self._log_view.setStyleSheet("color: #666; font-family: monospace;")
        layout.addWidget(self._log_view)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        self._download_btn = QPushButton("Download Model")
        self._download_btn.setIcon(
            QIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoDown))
        )
        self._download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self._download_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._thread: QThread | None = None
        self._worker: _DownloadWorker | None = None
        self._download_done = False

    def initializePage(self):
        """Auto-detect already-downloaded models and mark step as done."""
        from pathlib import Path

        from aria.config.models import Chat

        if Chat.model_path:
            path = Path(Chat.model_path)
            exists = path.is_absolute() and path.exists() and path.is_dir()
            if not exists:
                from huggingface_hub import try_to_load_from_cache

                try:
                    cached = try_to_load_from_cache(
                        Chat.model_path, "config.json"
                    )
                    exists = cached is not None and cached != "None"
                except Exception:
                    exists = False
            if exists:
                self._download_done = True
                self._status_label.setText(
                    "✓ Chat model already available. Click Next to continue."
                )
                self._status_label.setStyleSheet(
                    "color: #2e7d32; font-weight: bold;"
                )
                self.completeChanged.emit()

    def _start_download(self):
        from huggingface_hub import snapshot_download

        from aria.config.models import Chat, Embeddings

        self._download_btn.setEnabled(False)
        self._status_label.setText("Downloading…")
        self._log_view.clear()

        alias = self._model_combo.currentText()

        model_path = None
        if alias == "chat":
            model_path = Chat.model_path
            if not model_path:
                self._on_failed(
                    "Chat model is not configured (CHAT_MODEL_PATH)."
                )
                return
        elif alias == "embeddings":
            model_path = Embeddings.model_path
            if not model_path:
                self._on_failed(
                    "Embeddings model is not configured (EMBED_MODEL_PATH)."
                )
                return

        def _download_all():
            snapshot_download(repo_id=model_path, token=None)

        self._worker = _DownloadWorker(_download_all)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_failed)

        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_log(self, line: str):
        self._log_view.appendPlainText(line)

    def _on_finished(self):
        self._download_done = True
        self._download_btn.setEnabled(True)
        self._status_label.setText("✓ Model downloaded successfully!")
        self._status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        self.completeChanged.emit()

    def _on_failed(self, error: str):
        self._download_btn.setEnabled(True)
        self._status_label.setText(f"✗ Download failed: {error}")
        self._status_label.setStyleSheet("color: #c62828; font-weight: bold;")

    def isComplete(self) -> bool:
        return self._download_done

    def cleanupPage(self):
        try:
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(3000)
        except RuntimeError:
            pass
        self._thread = None


class _UserPage(QWizardPage):
    """Wizard page for creating the admin user."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Create Admin User")
        self.setSubTitle(
            "Create your first user account to access the Aria web interface."
        )

        layout = QFormLayout(self)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Your name")
        layout.addRow("Name:", self._name_edit)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("you@example.com")
        layout.addRow("E-Mail:", self._email_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self._password_edit.setPlaceholderText("Choose a password")
        layout.addRow("Password:", self._password_edit)

        self._confirm_edit = QLineEdit()
        self._confirm_edit.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self._confirm_edit.setPlaceholderText("Confirm password")
        layout.addRow("Confirm:", self._confirm_edit)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #c62828;")
        self._error_label.setWordWrap(True)
        layout.addRow(self._error_label)

        self._name_edit.textChanged.connect(self._validate)
        self._email_edit.textChanged.connect(self._validate)
        self._password_edit.textChanged.connect(self._validate)
        self._confirm_edit.textChanged.connect(self._validate)

    def _validate(self):
        name = self._name_edit.text().strip()
        email = self._email_edit.text().strip()
        password = self._password_edit.text()
        confirm = self._confirm_edit.text()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("A valid e-mail address is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        self._error_label.setText("\n".join(errors))
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        name = self._name_edit.text().strip()
        email = self._email_edit.text().strip()
        password = self._password_edit.text()
        confirm = self._confirm_edit.text()

        return (
            bool(name)
            and bool(email)
            and "@" in email
            and len(password) >= 6
            and password == confirm
        )

    def create_user(self) -> bool:
        """Create the user in the database.

        Returns True on success, False on failure.
        """
        from aria.cli import get_db_session
        from aria.db.auth import hash_password
        from aria.db.models import User

        try:
            with get_db_session() as session:
                existing = session.execute(
                    select(User).where(
                        User.identifier == self._email_edit.text().strip()
                    )
                ).scalar_one_or_none()

                if existing:
                    QMessageBox.warning(
                        self,
                        "User Exists",
                        "A user with this email already exists.",
                    )
                    return False

                session.add(
                    User(
                        id=str(uuid.uuid4()),
                        display_name=self._name_edit.text().strip(),
                        identifier=self._email_edit.text().strip(),
                        metadata_=json.dumps(
                            {"role": "admin", "created_by": "wizard"}
                        ),
                        password=hash_password(self._password_edit.text()),
                        createdAt=datetime.now().isoformat() + "Z",
                    )
                )
            return True
        except Exception as exc:
            QMessageBox.warning(
                self,
                "User Creation Failed",
                f"Could not create user:\n{exc}",
            )
            return False


class _FinishPage(QWizardPage):
    """Final wizard page — ready to start."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("All Set!")
        self.setSubTitle(
            "Aria is ready. Click Finish to close the wizard and "
            "start using the application."
        )

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "You can start the server from the main window "
                "using the Start button in the toolbar."
            )
        )
        layout.addStretch()


class SetupWizard(QWizard):
    """First-run setup wizard for Aria."""

    def __init__(self, parent: MainWindow | None = None):
        super().__init__(parent)
        self.setWindowTitle("Aria Setup Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(550, 400)

        self.setPage(0, _EnginePage(self))
        self.setPage(1, _ModelPage(self))
        self.setPage(2, _UserPage(self))
        self.setPage(3, _FinishPage(self))


def should_show_wizard() -> bool:
    """Check if the first-run wizard should be shown.

    Returns True if no users exist in the database.
    """
    try:
        from aria.cli import get_db_session
        from aria.db.models import User

        with get_db_session() as session:
            users = session.execute(select(User)).scalars().all()
            return len(users) == 0
    except Exception:
        return True


def run_wizard(parent: MainWindow | None = None) -> bool:
    """Show the setup wizard and return True if the user was created.

    Returns False if the wizard was cancelled or user creation failed.
    """
    wizard = SetupWizard(parent)
    result = wizard.exec()

    if result == QWizard.DialogCode.Accepted:
        user_page: _UserPage = wizard.page(2)  # type: ignore[assignment]
        return user_page.create_user()

    return False
