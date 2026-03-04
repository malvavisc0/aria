"""Setup tab handlers for the MainWindow.

This module provides a mixin class with Setup tab functionality for the Aria
GUI application, including llama.cpp binary downloads and GGUF model downloads.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import Callable, Optional

_ANSI_ESCAPE = re.compile(
    r"\x1b\[[0-9;?]*[a-zA-Z]"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    r"|\x1b[@-Z\\-_]"
    r"|\r"
)


def _strip_ansi(text: str) -> str:
    """Remove ANSI/VT100 escape sequences and carriage returns from *text*."""
    return _ANSI_ESCAPE.sub("", text)


from PySide6.QtCore import QObject, QThread, Signal

from aria.gui.ui.mainwindow import Ui_MainWindow


class _SignalStream(io.TextIOBase):
    """A writable text stream that emits each completed line via a callback.

    Used to redirect ``sys.stdout`` / ``sys.stderr`` inside worker threads so
    that all console output (rich, print, loguru) is forwarded to the GUI text
    area instead of the terminal.

    Args:
        emit_fn: Callable that receives a single non-empty stripped line.
    """

    def __init__(self, emit_fn: Callable[[str], None]):
        super().__init__()
        self._emit = emit_fn
        self._buf = ""

    def write(self, text: str) -> int:  # type: ignore[override]
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            stripped = line.rstrip()
            if stripped:
                self._emit(stripped)
        return len(text)

    def flush(self) -> None:
        if self._buf.strip():
            self._emit(self._buf.strip())
            self._buf = ""


class _LlamaDownloadWorker(QObject):
    """Worker that downloads llama.cpp binaries in a background thread.

    Emits ``log_line`` for each line of output, ``finished`` on success,
    or ``error`` with a message string on failure.
    """

    finished = Signal()
    error = Signal(str)
    log_line = Signal(str)

    def __init__(self, bin_dir: Path, version: Optional[str] = None):
        super().__init__()
        self._bin_dir = bin_dir
        self._version = version

    def run(self) -> None:
        """Download llama.cpp binaries (runs in a QThread)."""
        from aria.scripts.llama import download_llama_cpp

        stream = _SignalStream(self.log_line.emit)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = stream  # type: ignore[assignment]
        sys.stderr = stream  # type: ignore[assignment]
        try:
            download_llama_cpp(bin_dir=self._bin_dir, version=self._version)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class _ModelDownloadWorker(QObject):
    """Worker that downloads a GGUF model in a background thread.

    Emits ``log_line`` for each line of output, ``finished`` on success,
    or ``error`` with a message string on failure.

    For the ``vl`` alias the mmproj file is also downloaded when configured.
    """

    finished = Signal()
    error = Signal(str)
    log_line = Signal(str)

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
        """Download the selected GGUF model (runs in a QThread)."""
        from aria.config.api import LlamaCpp
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import download_gguf_model

        models_dir = LlamaCpp.models_path
        downloads: list[tuple[str, str]] = []

        if self._alias == "chat":
            if not Chat.repo_id or not Chat.filename:
                self.error.emit(
                    "Chat model is not configured "
                    "(CHAT_MODEL_REPO / CHAT_MODEL)."
                )
                return
            downloads.append((Chat.repo_id, Chat.filename))

        elif self._alias == "vl":
            if not Vision.repo_id or not Vision.filename:
                self.error.emit(
                    "Vision model is not configured "
                    "(VL_MODEL_REPO / VL_MODEL)."
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

        stream = _SignalStream(self.log_line.emit)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = stream  # type: ignore[assignment]
        sys.stderr = stream  # type: ignore[assignment]
        try:
            for repo_id, filename in downloads:
                download_gguf_model(
                    repo_id=repo_id,
                    filename=filename,
                    models_dir=models_dir,
                    token=self._token,
                    force=self._force,
                )
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class _LightpandaDownloadWorker(QObject):
    """Worker that downloads Lightpanda binary in a background thread.

    Emits ``log_line`` for each line of output, ``finished`` on success,
    or ``error`` with a message string on failure.
    """

    finished = Signal()
    error = Signal(str)
    log_line = Signal(str)

    def __init__(self, bin_dir: Path, version: Optional[str] = None):
        super().__init__()
        self._bin_dir = bin_dir
        self._version = version

    def run(self) -> None:
        """Download Lightpanda binary (runs in a QThread)."""
        from aria.scripts.lightpanda import download_lightpanda

        stream = _SignalStream(self.log_line.emit)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = stream  # type: ignore[assignment]
        sys.stderr = stream  # type: ignore[assignment]
        try:
            download_lightpanda(bin_dir=self._bin_dir, version=self._version)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class SetupHandlersMixin:
    """Mixin class providing Setup tab handlers for MainWindow.

    This mixin expects to be combined with a QMainWindow that has a ``ui``
    attribute of type ``Ui_MainWindow``. It provides:

    - Status label population for LlamaCpp binaries, GGUF models, and Lightpanda
    - Background download of llama.cpp binaries via ``_LlamaDownloadWorker``
    - Background download of GGUF models via ``_ModelDownloadWorker``
    - Background download of Lightpanda via ``_LightpandaDownloadWorker``

    Attributes:
        _llama_dl_thread: QThread for the llama.cpp download worker.
        _llama_dl_worker: The active llama download worker (kept alive).
        _model_dl_thread: QThread for the model download worker.
        _model_dl_worker: The active model download worker (kept alive).
        _lightpanda_dl_thread: QThread for Lightpanda download worker.
        _lightpanda_dl_worker: Active Lightpanda download worker (kept alive).
    """

    ui: Ui_MainWindow

    # Provided by ServerHandlersMixin when combined in MainWindow
    def _run_preflight(self) -> None: ...

    def _connect_setup_signals(self) -> None:
        """Wire Setup tab button signals and initialise thread handles.

        Call this from ``MainWindow.__init__()`` after ``setupUi()``.
        """
        self.ui.pushButton_LlamaDownload.clicked.connect(
            self.on_llama_download_clicked
        )
        self.ui.pushButton_ModelDownload.clicked.connect(
            self.on_model_download_clicked
        )
        self.ui.pushButton_LightpandaDownload.clicked.connect(
            self.on_lightpanda_download_clicked
        )
        self._llama_dl_thread: Optional[QThread] = None
        self._llama_dl_worker: Optional[_LlamaDownloadWorker] = None
        self._model_dl_thread: Optional[QThread] = None
        self._model_dl_worker: Optional[_ModelDownloadWorker] = None
        self._lightpanda_dl_thread: Optional[QThread] = None
        self._lightpanda_dl_worker: Optional[_LightpandaDownloadWorker] = None

    def load_setup(self) -> None:
        """Populate all Setup tab status labels from current configuration."""
        from aria.config.api import LlamaCpp
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import is_model_downloaded

        self.ui.label_LlamaBinDir.setText(str(LlamaCpp.bin_path))
        self.ui.label_LlamaVersion.setText(LlamaCpp.version)

        binaries = {
            "label_LlamaBin_cli": "llama-cli",
            "label_LlamaBin_server": "llama-server",
            "label_LlamaBin_bench": "llama-bench",
            "label_LlamaBin_quantize": "llama-quantize",
        }
        for label_name, binary in binaries.items():
            exists = (LlamaCpp.bin_path / binary).exists()
            icon = "✓" if exists else "✗"
            color = "green" if exists else "red"
            label = getattr(self.ui, label_name)
            label.setText(
                f'<span style="color:{color}">{icon}</span> {binary}'
            )

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
            label.setText(
                f'<span style="color:{color}">{icon}</span> {filename}'
            )

        # Lightpanda status
        from aria.config.api import Lightpanda

        self.ui.label_Lightpanda_BinDir.setText(str(Lightpanda.get_bin_path()))
        self.ui.label_Lightpanda_Version.setText(Lightpanda.version)

        binary_path = Lightpanda.get_binary_path()
        if binary_path:
            self.ui.label_Lightpanda_BinaryPath.setText(str(binary_path))
            self.ui.label_Lightpanda_Status.setText(
                '<span style="color:green">✓ Installed</span>'
            )
            self.ui.label_Lightpanda_BrowserTools.setText("Available")
        else:
            self.ui.label_Lightpanda_BinaryPath.setText("—")
            self.ui.label_Lightpanda_Status.setText(
                '<span style="color:red">✗ Not installed</span>'
            )
            self.ui.label_Lightpanda_BrowserTools.setText("Disabled")

    def _cleanup_thread(self, attr: str) -> None:
        """Safely stop and clean up a QThread stored as an instance attribute.

        Args:
            attr: Name of the ``QThread`` attribute on ``self``.
        """
        thread = getattr(self, attr, None)
        if thread is not None:
            if thread.isRunning():
                thread.quit()
                if not thread.wait(5000):
                    thread.terminate()
                    thread.wait()
            setattr(self, attr, None)

    def _cleanup_llama_dl_thread(self) -> None:
        """Safely stop and clean up the llama download thread."""
        self._cleanup_thread("_llama_dl_thread")
        self._llama_dl_worker = None

    def on_llama_download_clicked(self) -> None:
        """Handle Download Binaries button click.

        Starts ``_LlamaDownloadWorker`` in a background QThread.
        """
        from aria.config.api import LlamaCpp

        self._cleanup_llama_dl_thread()
        self.ui.pushButton_LlamaDownload.setEnabled(False)
        self.ui.plainTextEdit_LlamaOutput.clear()

        version_text = self.ui.lineEdit_LlamaVersion.text().strip() or None

        self._llama_dl_worker = _LlamaDownloadWorker(
            bin_dir=LlamaCpp.bin_path, version=version_text
        )
        self._llama_dl_thread = QThread()
        self._llama_dl_worker.moveToThread(self._llama_dl_thread)

        self._llama_dl_thread.started.connect(self._llama_dl_worker.run)
        self._llama_dl_worker.log_line.connect(self._on_llama_log_line)
        self._llama_dl_worker.finished.connect(self._on_llama_dl_finished)
        self._llama_dl_worker.error.connect(self._on_llama_dl_error)
        self._llama_dl_worker.finished.connect(self._llama_dl_thread.quit)
        self._llama_dl_worker.error.connect(self._llama_dl_thread.quit)
        self._llama_dl_thread.finished.connect(
            self._llama_dl_worker.deleteLater
        )
        self._llama_dl_thread.finished.connect(self._clear_llama_dl_worker)

        self._llama_dl_thread.start()

    def _clear_llama_dl_worker(self) -> None:
        self._llama_dl_worker = None

    def _on_llama_log_line(self, line: str) -> None:
        self.ui.plainTextEdit_LlamaOutput.appendPlainText(_strip_ansi(line))

    def _on_llama_dl_finished(self) -> None:
        self.ui.pushButton_LlamaDownload.setEnabled(True)
        self.load_setup()
        self._run_preflight()

    def _on_llama_dl_error(self, message: str) -> None:
        self.ui.plainTextEdit_LlamaOutput.appendPlainText(f"ERROR: {message}")
        self.ui.pushButton_LlamaDownload.setEnabled(True)

    def _cleanup_model_dl_thread(self) -> None:
        """Safely stop and clean up the model download thread."""
        self._cleanup_thread("_model_dl_thread")
        self._model_dl_worker = None

    def on_model_download_clicked(self) -> None:
        """Handle Download Model button click.

        Starts ``_ModelDownloadWorker`` in a background QThread.
        """
        from aria.config.huggingface import HuggingFace

        self._cleanup_model_dl_thread()
        self.ui.pushButton_ModelDownload.setEnabled(False)
        self.ui.plainTextEdit_ModelOutput.clear()

        alias = self.ui.comboBox_ModelSelect.currentText()
        token_text = (
            self.ui.lineEdit_HFToken.text().strip() or HuggingFace.token
        )
        force = self.ui.checkBox_ModelForce.isChecked()

        self._model_dl_worker = _ModelDownloadWorker(
            alias=alias, token=token_text, force=force
        )
        self._model_dl_thread = QThread()
        self._model_dl_worker.moveToThread(self._model_dl_thread)

        self._model_dl_thread.started.connect(self._model_dl_worker.run)
        self._model_dl_worker.log_line.connect(self._on_model_log_line)
        self._model_dl_worker.finished.connect(self._on_model_dl_finished)
        self._model_dl_worker.error.connect(self._on_model_dl_error)
        self._model_dl_worker.finished.connect(self._model_dl_thread.quit)
        self._model_dl_worker.error.connect(self._model_dl_thread.quit)
        self._model_dl_thread.finished.connect(
            self._model_dl_worker.deleteLater
        )
        self._model_dl_thread.finished.connect(self._clear_model_dl_worker)

        self._model_dl_thread.start()

    def _clear_model_dl_worker(self) -> None:
        self._model_dl_worker = None

    def _on_model_log_line(self, line: str) -> None:
        self.ui.plainTextEdit_ModelOutput.appendPlainText(_strip_ansi(line))

    def _on_model_dl_finished(self) -> None:
        self.ui.pushButton_ModelDownload.setEnabled(True)
        self.load_setup()
        self._run_preflight()

    def _on_model_dl_error(self, message: str) -> None:
        self.ui.plainTextEdit_ModelOutput.appendPlainText(f"ERROR: {message}")
        self.ui.pushButton_ModelDownload.setEnabled(True)

    def _cleanup_lightpanda_dl_thread(self) -> None:
        """Safely stop and clean up the Lightpanda download thread."""
        self._cleanup_thread("_lightpanda_dl_thread")
        self._lightpanda_dl_worker = None

    def on_lightpanda_download_clicked(self) -> None:
        """Handle Download Lightpanda button click.

        Starts ``_LightpandaDownloadWorker`` in a background QThread.
        """
        from aria.config.api import Lightpanda

        self._cleanup_lightpanda_dl_thread()
        self.ui.pushButton_LightpandaDownload.setEnabled(False)
        self.ui.plainTextEdit_LightpandaOutput.clear()

        version_text = (
            self.ui.lineEdit_LightpandaVersion.text().strip() or None
        )

        self._lightpanda_dl_worker = _LightpandaDownloadWorker(
            bin_dir=Lightpanda.get_bin_path(), version=version_text
        )
        self._lightpanda_dl_thread = QThread()
        self._lightpanda_dl_worker.moveToThread(self._lightpanda_dl_thread)

        self._lightpanda_dl_thread.started.connect(
            self._lightpanda_dl_worker.run
        )
        self._lightpanda_dl_worker.log_line.connect(
            self._on_lightpanda_log_line
        )
        self._lightpanda_dl_worker.finished.connect(
            self._on_lightpanda_dl_finished
        )
        self._lightpanda_dl_worker.error.connect(self._on_lightpanda_dl_error)
        self._lightpanda_dl_worker.finished.connect(
            self._lightpanda_dl_thread.quit
        )
        self._lightpanda_dl_worker.error.connect(
            self._lightpanda_dl_thread.quit
        )
        self._lightpanda_dl_thread.finished.connect(
            self._lightpanda_dl_worker.deleteLater
        )
        self._lightpanda_dl_thread.finished.connect(
            self._clear_lightpanda_dl_worker
        )

        self._lightpanda_dl_thread.start()

    def _clear_lightpanda_dl_worker(self) -> None:
        self._lightpanda_dl_worker = None

    def _on_lightpanda_log_line(self, line: str) -> None:
        self.ui.plainTextEdit_LightpandaOutput.appendPlainText(
            _strip_ansi(line)
        )

    def _on_lightpanda_dl_finished(self) -> None:
        self.ui.pushButton_LightpandaDownload.setEnabled(True)
        self.load_setup()
        self._run_preflight()

    def _on_lightpanda_dl_error(self, message: str) -> None:
        self.ui.plainTextEdit_LightpandaOutput.appendPlainText(
            f"ERROR: {message}"
        )
        self.ui.pushButton_LightpandaDownload.setEnabled(True)
