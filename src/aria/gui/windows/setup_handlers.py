"""Setup tab handlers for the MainWindow.

This module provides a mixin class with Setup tab functionality for the Aria
GUI application, including llama.cpp binary downloads and GGUF model downloads.
"""

from __future__ import annotations

import io
import re
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QIcon

from aria.gui.ui.mainwindow import Ui_MainWindow

_ANSI_ESCAPE = re.compile(
    r"\x1b\[[0-9;?]*[a-zA-Z]"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    r"|\x1b[@-Z\\-_]"
    r"|\r"
)


def _strip_ansi(text: str) -> str:
    """Remove ANSI/VT100 escape sequences and carriage returns."""
    return _ANSI_ESCAPE.sub("", text)


class _SignalStream(io.TextIOBase):
    """A writable text stream that emits each completed line via a callback.

    Used to redirect ``sys.stdout`` / ``sys.stderr`` inside worker threads so
    that all console output (rich, print, loguru) is forwarded to the GUI text
    area instead of the terminal.

    Thread-safe: a lock protects the internal buffer because the
    ``sys.stdout``/``sys.stderr`` redirect is process-global, meaning
    writes can arrive from the worker QThread, the main thread (loguru
    sinks, Qt debug output), or internal threads spawned by libraries
    such as ``huggingface_hub``.
    """

    _LINE_SEP = re.compile(r"[\r\n]+")

    def __init__(self, emit_fn: Callable[[str], None]):
        super().__init__()
        self._emit = emit_fn
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, text: str) -> int:  # type: ignore[override]
        with self._lock:
            self._buf += text
            parts = self._LINE_SEP.split(self._buf)
            # Last element is the incomplete trailing chunk.
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


# ---------------------------------------------------------------------------
# Generic download worker
# ---------------------------------------------------------------------------


class _BaseDownloadWorker(QObject):
    """Base worker that redirects stdout/stderr to the ``log_line`` signal.

    Subclasses must implement :meth:`run` and call
    :meth:`_run_with_redirected_output` with the actual download callable.
    """

    finished = Signal()
    error = Signal(str)
    log_line = Signal(str)

    def run(self) -> None:
        """Execute the download. Must be overridden by subclasses."""

    def _run_with_redirected_output(self, fn: Callable, *args, **kwargs) -> None:
        """Run *fn* with stdout/stderr redirected to ``log_line``."""
        stream = _SignalStream(self.log_line.emit)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = stream  # type: ignore[assignment]
        sys.stderr = stream  # type: ignore[assignment]
        try:
            fn(*args, **kwargs)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class _LlamaDownloadWorker(_BaseDownloadWorker):
    """Worker that downloads llama.cpp binaries in a background thread."""

    def __init__(self, bin_dir: Path, version: Optional[str] = None):
        super().__init__()
        self._bin_dir = bin_dir
        self._version = version

    def run(self) -> None:
        from aria.scripts.llama import download_llama_cpp

        self._run_with_redirected_output(
            download_llama_cpp,
            bin_dir=self._bin_dir,
            version=self._version,
        )


class _ModelDownloadWorker(_BaseDownloadWorker):
    """Worker that downloads a GGUF model in a background thread."""

    def __init__(
        self,
        alias: str,
        token: Optional[str],
        force: bool,
    ):
        super().__init__()
        self._alias = alias
        self._token = token
        self._force = force

    def run(self) -> None:
        from aria.config.api import LlamaCpp
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import download_gguf_model

        models_dir = LlamaCpp.models_path
        downloads: list[tuple[str, str]] = []

        if self._alias == "chat":
            if not Chat.repo_id or not Chat.filename:
                self.error.emit(
                    "Chat model is not configured " "(CHAT_MODEL_REPO / CHAT_MODEL)."
                )
                return
            downloads.append((Chat.repo_id, Chat.filename))

        elif self._alias == "vl":
            if not Vision.repo_id or not Vision.filename:
                self.error.emit(
                    "Vision model is not configured " "(VL_MODEL_REPO / VL_MODEL)."
                )
                return
            downloads.append((Vision.repo_id, Vision.filename))
            if Vision.mmproj_filename:
                downloads.append((Vision.repo_id, Vision.mmproj_filename))

        elif self._alias == "embeddings":
            if not Embeddings.repo_id or not Embeddings.filename:
                self.error.emit(
                    "Embeddings model is not configured "
                    "(EMBEDDINGS_MODEL_REPO / EMBEDDINGS_MODEL)."
                )
                return
            downloads.append((Embeddings.repo_id, Embeddings.filename))

        else:
            self.error.emit(f"Unknown model alias: {self._alias!r}")
            return

        def _download_all():
            for repo_id, filename in downloads:
                download_gguf_model(
                    repo_id=repo_id,
                    filename=filename,
                    models_dir=models_dir,
                    token=self._token,
                    force=self._force,
                )

        self._run_with_redirected_output(_download_all)


class _LightpandaDownloadWorker(_BaseDownloadWorker):
    """Worker that downloads Lightpanda binary in a background thread."""

    def __init__(self, bin_dir: Path, version: Optional[str] = None):
        super().__init__()
        self._bin_dir = bin_dir
        self._version = version

    def run(self) -> None:
        from aria.scripts.lightpanda import download_lightpanda

        self._run_with_redirected_output(
            download_lightpanda,
            bin_dir=self._bin_dir,
            version=self._version,
        )


# ---------------------------------------------------------------------------
# Download slot — bundles per-download widget references
# ---------------------------------------------------------------------------


class _DownloadSlot:
    """Holds per-download widget references and callbacks."""

    def __init__(
        self,
        thread_attr: str,
        worker_attr: str,
        button,
        output,
        default_text: str,
        start_handler: Callable,
    ):
        self.thread_attr = thread_attr
        self.worker_attr = worker_attr
        self.button = button
        self.output = output
        self.default_text = default_text
        self.start_handler = start_handler


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------


class SetupHandlersMixin:
    """Mixin class providing Setup tab handlers for MainWindow.

    This mixin expects to be combined with a QMainWindow that has a ``ui``
    attribute of type ``Ui_MainWindow``.  It provides:

    - Status label population for binaries, models, and Lightpanda
    - Generic background download with cancel and auto-refresh
    """

    ui: Ui_MainWindow

    # Provided by ServerHandlersMixin when combined in MainWindow
    def _run_preflight(self) -> None: ...  # pragma: no cover

    def _connect_setup_signals(self) -> None:
        """Wire Setup tab button signals and initialise download slots."""
        self.ui.pushButton_LlamaDownload.clicked.connect(self.on_llama_download_clicked)
        self.ui.pushButton_ModelDownload.clicked.connect(self.on_model_download_clicked)
        self.ui.pushButton_LightpandaDownload.clicked.connect(
            self.on_lightpanda_download_clicked
        )

        # Thread / worker attribute handles (kept for closeEvent compat)
        self._llama_dl_thread: Optional[QThread] = None
        self._llama_dl_worker: Optional[_LlamaDownloadWorker] = None
        self._model_dl_thread: Optional[QThread] = None
        self._model_dl_worker: Optional[_ModelDownloadWorker] = None
        self._lightpanda_dl_thread: Optional[QThread] = None
        self._lightpanda_dl_worker: Optional[_LightpandaDownloadWorker] = None

        self._dl_slots: dict[str, _DownloadSlot] = {
            "llama": _DownloadSlot(
                thread_attr="_llama_dl_thread",
                worker_attr="_llama_dl_worker",
                button=self.ui.pushButton_LlamaDownload,
                output=self.ui.plainTextEdit_LlamaOutput,
                default_text="Download Binaries",
                start_handler=self.on_llama_download_clicked,
            ),
            "model": _DownloadSlot(
                thread_attr="_model_dl_thread",
                worker_attr="_model_dl_worker",
                button=self.ui.pushButton_ModelDownload,
                output=self.ui.plainTextEdit_ModelOutput,
                default_text="Download Model",
                start_handler=self.on_model_download_clicked,
            ),
            "lightpanda": _DownloadSlot(
                thread_attr="_lightpanda_dl_thread",
                worker_attr="_lightpanda_dl_worker",
                button=self.ui.pushButton_LightpandaDownload,
                output=self.ui.plainTextEdit_LightpandaOutput,
                default_text="Download",
                start_handler=self.on_lightpanda_download_clicked,
            ),
        }

    # ------------------------------------------------------------------
    # Setup tab — status labels
    # ------------------------------------------------------------------

    def load_setup(self) -> None:
        """Populate all Setup tab status labels from current config."""
        from aria.config.api import LlamaCpp
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import is_model_downloaded

        self.ui.label_LlamaBinDir.setText(str(LlamaCpp.bin_path))
        self.ui.label_LlamaVersion.setText(LlamaCpp.version)

        models_dir = LlamaCpp.models_path
        model_configs = [
            ("label_ModelChat_Status", Chat.filename, Chat.repo_id),
            ("label_ModelVL_Status", Vision.filename, Vision.repo_id),
            (
                "label_ModelEmbeddings_Status",
                Embeddings.filename,
                Embeddings.repo_id,
            ),
        ]
        for label_name, filename, repo_id in model_configs:
            label = getattr(self.ui, label_name)
            if not filename or not repo_id:
                label.setText("not configured")
                continue
            downloaded = is_model_downloaded(filename, models_dir)
            icon = "✓" if downloaded else "✗"
            color = "green" if downloaded else "red"
            label.setText(f'<span style="color:{color}">{icon}</span> {filename}')

        # Lightpanda status
        from aria.config.api import Lightpanda

        self.ui.label_Lightpanda_BinDir.setText(str(Lightpanda.get_bin_path()))
        self.ui.label_Lightpanda_Version.setText(Lightpanda.version)

        binary_path = Lightpanda.get_binary_path()
        if binary_path:
            self.ui.label_Lightpanda_Status.setText(
                '<span style="color:green">✓ Installed</span>'
            )
        else:
            self.ui.label_Lightpanda_Status.setText(
                '<span style="color:red">✗ Not installed</span>'
            )

    # ------------------------------------------------------------------
    # Generic download helpers
    # ------------------------------------------------------------------

    def _cleanup_thread(self, attr: str) -> None:
        """Safely stop and clean up a QThread stored as an instance attr."""
        thread = getattr(self, attr, None)
        if thread is not None:
            if thread.isRunning():
                thread.quit()
                if not thread.wait(5000):
                    thread.terminate()
                    thread.wait()
            setattr(self, attr, None)

    def _cleanup_llama_dl_thread(self) -> None:
        self._cleanup_thread("_llama_dl_thread")
        self._llama_dl_worker = None

    def _cleanup_model_dl_thread(self) -> None:
        self._cleanup_thread("_model_dl_thread")
        self._model_dl_worker = None

    def _cleanup_lightpanda_dl_thread(self) -> None:
        self._cleanup_thread("_lightpanda_dl_thread")
        self._lightpanda_dl_worker = None

    def _start_download(self, key: str, worker: _BaseDownloadWorker) -> None:
        """Start a generic download in a background thread."""
        slot = self._dl_slots[key]

        # Clean up any previous download
        self._cleanup_thread(slot.thread_attr)
        setattr(self, slot.worker_attr, None)

        # Reset UI
        slot.output.clear()

        # Create and wire thread
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_line.connect(lambda line, k=key: self._on_dl_log_line(k, line))
        worker.finished.connect(lambda k=key: self._on_dl_finished(k))
        worker.error.connect(lambda msg, k=key: self._on_dl_error(k, msg))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda k=key: self._clear_dl_worker(k))

        # Store references
        setattr(self, slot.thread_attr, thread)
        setattr(self, slot.worker_attr, worker)

        # Switch button to Cancel mode
        slot.button.setText("Cancel")
        slot.button.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ProcessStop)))
        slot.button.clicked.disconnect()
        slot.button.clicked.connect(lambda k=key: self._cancel_download(k))
        slot.button.setEnabled(True)

        thread.start()

    def _cancel_download(self, key: str) -> None:
        """Cancel a running download."""
        slot = self._dl_slots[key]
        thread = getattr(self, slot.thread_attr, None)
        if thread is not None and thread.isRunning():
            thread.terminate()
            thread.wait()
        self._reset_download_button(key)

    def _reset_download_button(self, key: str) -> None:
        """Reset a download button to its default state."""
        slot = self._dl_slots[key]
        slot.button.setText(slot.default_text)
        slot.button.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoDown)))
        slot.button.setEnabled(True)
        slot.button.clicked.disconnect()
        slot.button.clicked.connect(slot.start_handler)

    def _clear_dl_worker(self, key: str) -> None:
        """Clear the worker reference for a download slot."""
        slot = self._dl_slots[key]
        setattr(self, slot.worker_attr, None)

    def _on_dl_log_line(self, key: str, line: str) -> None:
        """Append a log line to the output text area."""
        slot = self._dl_slots[key]
        slot.output.appendPlainText(_strip_ansi(line))

    def _on_dl_finished(self, key: str) -> None:
        """Handle download completion."""
        self._reset_download_button(key)
        self.load_setup()
        self._run_preflight()

    def _on_dl_error(self, key: str, message: str) -> None:
        """Handle download error."""
        slot = self._dl_slots[key]
        slot.output.appendPlainText(f"ERROR: {message}")
        self._reset_download_button(key)

    # ------------------------------------------------------------------
    # Per-download click handlers (thin wrappers)
    # ------------------------------------------------------------------

    def on_llama_download_clicked(self) -> None:
        """Handle Download Binaries button click."""
        from aria.config.api import LlamaCpp

        version_text = self.ui.lineEdit_LlamaVersion.text().strip() or None
        worker = _LlamaDownloadWorker(bin_dir=LlamaCpp.bin_path, version=version_text)
        self._start_download("llama", worker)

    def on_model_download_clicked(self) -> None:
        """Handle Download Model button click."""
        from aria.config.huggingface import HuggingFace

        alias = self.ui.comboBox_ModelSelect.currentText()
        token_text = self.ui.lineEdit_HFToken.text().strip() or HuggingFace.token
        force = self.ui.checkBox_ModelForce.isChecked()
        worker = _ModelDownloadWorker(alias=alias, token=token_text, force=force)
        self._start_download("model", worker)

    def on_lightpanda_download_clicked(self) -> None:
        """Handle Download Lightpanda button click."""
        from aria.config.api import Lightpanda

        version_text = self.ui.lineEdit_LightpandaVersion.text().strip() or None
        worker = _LightpandaDownloadWorker(
            bin_dir=Lightpanda.get_bin_path(), version=version_text
        )
        self._start_download("lightpanda", worker)
