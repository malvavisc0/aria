"""Setup tab handlers for the MainWindow.

This module provides a mixin class with Setup tab functionality for the Aria
GUI application, including llama.cpp binary downloads and GGUF model downloads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from aria.gui.ui.mainwindow import Ui_MainWindow


class _LlamaDownloadWorker(QObject):
    """Worker that downloads llama.cpp binaries in a background thread.

    Emits ``log_line`` for each progress message, ``finished`` on success,
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
        from loguru import logger

        from aria.scripts.llama import download_llama_cpp

        # Add a loguru sink that forwards log records to the log_line signal
        sink_id = logger.add(
            lambda msg: self.log_line.emit(msg.strip()),
            format="{level}: {message}",
            level="DEBUG",
        )

        try:
            self.log_line.emit("Starting llama.cpp download...")
            download_llama_cpp(bin_dir=self._bin_dir, version=self._version)
            self.log_line.emit("Download complete.")
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            logger.remove(sink_id)


class _ModelDownloadWorker(QObject):
    """Worker that downloads a GGUF model in a background thread.

    Emits ``log_line`` for each progress message, ``finished`` on success,
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
        from loguru import logger

        from aria.config.api import LlamaCpp
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import download_gguf_model

        models_dir = LlamaCpp.models_path

        # Resolve alias → (repo_id, filename) pairs to download
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

        # Add a loguru sink that forwards log records to the log_line signal
        sink_id = logger.add(
            lambda msg: self.log_line.emit(msg.strip()),
            format="{level}: {message}",
            level="DEBUG",
        )

        try:
            for repo_id, filename in downloads:
                self.log_line.emit(f"Downloading {filename} from {repo_id}...")
                download_gguf_model(
                    repo_id=repo_id,
                    filename=filename,
                    models_dir=models_dir,
                    token=self._token,
                    force=self._force,
                )
                self.log_line.emit(f"Done: {filename}")
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            logger.remove(sink_id)


class SetupHandlersMixin:
    """Mixin class providing Setup tab handlers for MainWindow.

    This mixin expects to be combined with a QMainWindow that has a ``ui``
    attribute of type ``Ui_MainWindow``. It provides:

    - Status label population for LlamaCpp binaries and GGUF models
    - Background download of llama.cpp binaries via ``_LlamaDownloadWorker``
    - Background download of GGUF models via ``_ModelDownloadWorker``

    Attributes:
        _llama_dl_thread: QThread for the llama.cpp download worker.
        _model_dl_thread: QThread for the model download worker.
    """

    ui: Ui_MainWindow

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _connect_setup_signals(self) -> None:
        """Wire Setup tab button signals and initialise thread handles.

        Call this from ``MainWindow.__init__()`` after ``setupUi()``.
        """
        self.ui.pushButton_LlamaDownload.clicked.connect(self.on_llama_download_clicked)
        self.ui.pushButton_ModelDownload.clicked.connect(self.on_model_download_clicked)
        self._llama_dl_thread: Optional[QThread] = None
        self._model_dl_thread: Optional[QThread] = None

    # ------------------------------------------------------------------
    # Status population
    # ------------------------------------------------------------------

    def load_setup(self) -> None:
        """Populate all Setup tab status labels from current configuration."""
        from aria.config.api import LlamaCpp
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import is_model_downloaded

        # --- LlamaCpp binary status ---
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
            label.setText(f'<span style="color:{color}">{icon}</span> {binary}')

        # --- GGUF model status ---
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

    # ------------------------------------------------------------------
    # Thread helpers
    # ------------------------------------------------------------------

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

    def on_llama_download_clicked(self) -> None:
        """Handle Download Binaries button click.

        Starts ``_LlamaDownloadWorker`` in a background QThread.
        """
        from aria.config.api import LlamaCpp

        self._cleanup_llama_dl_thread()
        self.ui.pushButton_LlamaDownload.setEnabled(False)
        self.ui.plainTextEdit_LlamaOutput.clear()

        version_text = self.ui.lineEdit_LlamaVersion.text().strip() or None

        worker = _LlamaDownloadWorker(bin_dir=LlamaCpp.bin_path, version=version_text)
        self._llama_dl_thread = QThread()
        worker.moveToThread(self._llama_dl_thread)

        self._llama_dl_thread.started.connect(worker.run)
        worker.log_line.connect(self._on_llama_log_line)
        worker.finished.connect(self._on_llama_dl_finished)
        worker.error.connect(self._on_llama_dl_error)
        worker.finished.connect(self._llama_dl_thread.quit)
        worker.error.connect(self._llama_dl_thread.quit)
        self._llama_dl_thread.finished.connect(worker.deleteLater)

        self._llama_dl_thread.start()

    def _on_llama_log_line(self, line: str) -> None:
        self.ui.plainTextEdit_LlamaOutput.appendPlainText(line)

    def _on_llama_dl_finished(self) -> None:
        self.ui.pushButton_LlamaDownload.setEnabled(True)
        self.load_setup()

    def _on_llama_dl_error(self, message: str) -> None:
        self.ui.plainTextEdit_LlamaOutput.appendPlainText(f"ERROR: {message}")
        self.ui.pushButton_LlamaDownload.setEnabled(True)

    # ------------------------------------------------------------------
    # Model download
    # ------------------------------------------------------------------

    def _cleanup_model_dl_thread(self) -> None:
        """Safely stop and clean up the model download thread."""
        self._cleanup_thread("_model_dl_thread")

    def on_model_download_clicked(self) -> None:
        """Handle Download Model button click.

        Starts ``_ModelDownloadWorker`` in a background QThread.
        """
        from aria.config.huggingface import HuggingFace

        self._cleanup_model_dl_thread()
        self.ui.pushButton_ModelDownload.setEnabled(False)
        self.ui.plainTextEdit_ModelOutput.clear()

        alias = self.ui.comboBox_ModelSelect.currentText()
        token_text = self.ui.lineEdit_HFToken.text().strip() or HuggingFace.token
        force = self.ui.checkBox_ModelForce.isChecked()

        worker = _ModelDownloadWorker(alias=alias, token=token_text, force=force)
        self._model_dl_thread = QThread()
        worker.moveToThread(self._model_dl_thread)

        self._model_dl_thread.started.connect(worker.run)
        worker.log_line.connect(self._on_model_log_line)
        worker.finished.connect(self._on_model_dl_finished)
        worker.error.connect(self._on_model_dl_error)
        worker.finished.connect(self._model_dl_thread.quit)
        worker.error.connect(self._model_dl_thread.quit)
        self._model_dl_thread.finished.connect(worker.deleteLater)

        self._model_dl_thread.start()

    def _on_model_log_line(self, line: str) -> None:
        self.ui.plainTextEdit_ModelOutput.appendPlainText(line)

    def _on_model_dl_finished(self) -> None:
        self.ui.pushButton_ModelDownload.setEnabled(True)
        self.load_setup()

    def _on_model_dl_error(self, message: str) -> None:
        self.ui.plainTextEdit_ModelOutput.appendPlainText(f"ERROR: {message}")
        self.ui.pushButton_ModelDownload.setEnabled(True)
