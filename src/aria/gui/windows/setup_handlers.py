"""Setup tab handlers for the MainWindow.

This module provides a mixin class with Setup tab functionality for the Aria
GUI application, including llama.cpp binary downloads and GGUF model downloads.
"""

from __future__ import annotations

import io
import queue
import re
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal
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


class _QueueStream(io.TextIOBase):
    """A writable text stream that queues completed lines for later polling.

    Used to redirect ``sys.stdout`` / ``sys.stderr`` inside worker threads so
    that all console output (rich, print, loguru) is forwarded to the GUI text
    area instead of the terminal.

    Unlike the previous ``_SignalStream`` implementation, this class does
    **not** emit PySide6 signals from the worker thread.  Instead, finished
    lines are placed into a :class:`queue.Queue` that the main thread drains
    on a timer.  This avoids the segfault caused by PySide6's C++ signal
    dispatch interacting with Qt's internal mutexes from a non-GUI thread.

    Thread-safe: a lock protects the internal buffer because the
    ``sys.stdout``/``sys.stderr`` redirect is process-global, meaning
    writes can arrive from the worker QThread, the main thread (loguru
    sinks, Qt debug output), or internal threads spawned by libraries
    such as ``huggingface_hub``.
    """

    _LINE_SEP = re.compile(r"[\r\n]+")

    def __init__(self) -> None:
        super().__init__()
        self._buf = ""
        self._lock = threading.Lock()
        self.lines: queue.Queue[str] = queue.Queue()

    def write(self, text: str) -> int:  # type: ignore[override]
        with self._lock:
            self._buf += text
            parts = self._LINE_SEP.split(self._buf)
            # Last element is the incomplete trailing chunk.
            self._buf = parts[-1]
            for part in parts[:-1]:
                stripped = part.rstrip()
                if stripped:
                    self.lines.put(stripped)
        return len(text)

    def flush(self) -> None:
        with self._lock:
            if self._buf.strip():
                self.lines.put(self._buf.strip())
                self._buf = ""


# ---------------------------------------------------------------------------
# Generic download worker
# ---------------------------------------------------------------------------


class _BaseDownloadWorker(QObject):
    """Base worker that redirects stdout/stderr to a queue for GUI display.

    Subclasses must implement :meth:`run` and call
    :meth:`_run_with_redirected_output` with the actual download callable.
    """

    finished = Signal()
    error = Signal(str)

    # Set by the main-thread signal handlers so the drain timer can
    # detect completion without touching Qt from the worker thread.
    _done: bool = False
    _error_msg: Optional[str] = None

    def run(self) -> None:
        """Execute the download. Must be overridden by subclasses."""

    def _run_with_redirected_output(
        self, fn: Callable, *args, **kwargs
    ) -> None:
        """Run *fn* with stdout/stderr redirected to ``_stream``."""
        stream = _QueueStream()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        # Expose stream so the main-thread timer can drain it.
        self._stream = stream
        # Store originals so the cancel handler can restore them if
        # the thread is terminated before the finally-block runs.
        self._prev_stdout = old_stdout
        self._prev_stderr = old_stderr
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


class _VllmInstallWorker(_BaseDownloadWorker):
    """Worker that installs vLLM in a background thread."""

    def run(self) -> None:
        from aria.scripts.vllm import install_vllm

        self._run_with_redirected_output(install_vllm)


class _ModelDownloadWorker(_BaseDownloadWorker):
    """Worker that downloads a model snapshot in a background thread."""

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
        from huggingface_hub import snapshot_download

        from aria.config.models import Chat, Embeddings

        model_path = None
        if self._alias == "chat":
            model_path = Chat.model_path
            if not model_path:
                self.error.emit(
                    "Chat model is not configured (CHAT_MODEL_PATH)."
                )
                return
        elif self._alias == "embeddings":
            model_path = Embeddings.model_path
            if not model_path:
                self.error.emit(
                    "Embeddings model is not configured (EMBED_MODEL_PATH)."
                )
                return
        else:
            self.error.emit(f"Unknown model alias: {self._alias!r}")
            return

        def _download_all():
            kwargs: dict = {"repo_id": model_path, "token": self._token}
            if self._force:
                kwargs["force_download"] = True
            snapshot_download(**kwargs)

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
        self.ui.pushButton_VllmInstall.clicked.connect(
            self.on_vllm_install_clicked
        )
        self.ui.pushButton_ModelDownload.clicked.connect(
            self.on_model_download_clicked
        )
        self.ui.pushButton_LightpandaDownload.clicked.connect(
            self.on_lightpanda_download_clicked
        )

        # Thread / worker attribute handles (kept for closeEvent compat)
        self._vllm_dl_thread: Optional[QThread] = None
        self._vllm_dl_worker: Optional[_VllmInstallWorker] = None
        self._model_dl_thread: Optional[QThread] = None
        self._model_dl_worker: Optional[_ModelDownloadWorker] = None
        self._lightpanda_dl_thread: Optional[QThread] = None
        self._lightpanda_dl_worker: Optional[_LightpandaDownloadWorker] = None

        self._dl_slots: dict[str, _DownloadSlot] = {
            "vllm": _DownloadSlot(
                thread_attr="_vllm_dl_thread",
                worker_attr="_vllm_dl_worker",
                button=self.ui.pushButton_VllmInstall,
                output=self.ui.plainTextEdit_VllmOutput,
                default_text="Install vLLM",
                start_handler=self.on_vllm_install_clicked,
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
        from pathlib import Path

        from aria.config.models import Chat, Embeddings
        from aria.scripts.vllm import get_vllm_version, is_vllm_installed

        # vLLM status
        if is_vllm_installed():
            ver = get_vllm_version()
            self.ui.label_VllmVersion.setText(
                f'<span style="color:green">✓</span> vLLM {ver}'
            )
        else:
            self.ui.label_VllmVersion.setText(
                '<span style="color:red">✗</span> Not installed'
            )

        def _check_model(model_path: str) -> bool:
            if not model_path:
                return False
            p = Path(model_path)
            if p.is_absolute():
                return p.exists() and p.is_dir()
            from huggingface_hub import try_to_load_from_cache

            try:
                cached = try_to_load_from_cache(model_path, "config.json")
                return cached is not None and cached != "None"
            except Exception:
                return False

        model_configs = [
            ("label_ModelChat_Status", Chat.model_path),
            ("label_ModelEmbeddings_Status", Embeddings.model_path),
        ]
        for label_name, model_path in model_configs:
            label = getattr(self.ui, label_name)
            if not model_path:
                label.setText("not configured")
                continue
            downloaded = _check_model(model_path)
            icon = "✓" if downloaded else "✗"
            color = "green" if downloaded else "red"
            label.setText(
                f'<span style="color:{color}">{icon}</span> {model_path}'
            )

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
        # Restore stdout/stderr if the terminated thread had redirected them.
        worker_attr = attr.replace("_thread", "_worker")
        worker = getattr(self, worker_attr, None)
        if worker is not None and hasattr(worker, "_prev_stdout"):
            if sys.stdout is not worker._prev_stdout:
                sys.stdout = worker._prev_stdout
            if sys.stderr is not worker._prev_stderr:
                sys.stderr = worker._prev_stderr

    def _cleanup_vllm_dl_thread(self) -> None:
        self._cleanup_thread("_vllm_dl_thread")
        self._vllm_dl_worker = None

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
        self._stop_log_timer(key)
        self._cleanup_thread(slot.thread_attr)
        setattr(self, slot.worker_attr, None)

        # Reset UI
        slot.output.clear()

        # Flag polled by the drain timer — avoids calling Qt widgets
        # from the worker thread (AutoConnection + lambda → Direct).
        worker._done = False
        worker._error_msg = None

        # Create and wire thread
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        # finished/error only set flags; the timer does all UI work.
        worker.finished.connect(lambda w=worker: setattr(w, "_done", True))

        def _set_error(msg, w=worker):
            w._done = True
            w._error_msg = msg

        worker.error.connect(_set_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        # NOTE: do NOT connect thread.finished to _clear_dl_worker here.
        # The timer's _drain_log handles cleanup after detecting _done,
        # otherwise the worker reference is cleared before the timer can
        # see the completion flag.

        # Store references
        setattr(self, slot.thread_attr, thread)
        setattr(self, slot.worker_attr, worker)

        # Switch button to Cancel mode
        slot.button.setText("Cancel")
        slot.button.setIcon(
            QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ProcessStop))
        )
        slot.button.clicked.disconnect()
        slot.button.clicked.connect(
            lambda _checked, k=key: self._cancel_download(k)
        )
        slot.button.setEnabled(True)

        thread.start()

        # Start a QTimer that drains the worker's queue and — once the
        # worker signals completion — performs all UI updates in the main
        # thread.  No PySide6 widget/signal access from worker threads.
        timer = QTimer()
        timer.setInterval(100)
        timer.timeout.connect(lambda k=key: self._drain_log(k))
        timer.start()
        setattr(self, f"_{key}_log_timer", timer)

    def _stop_log_timer(self, key: str) -> None:
        """Stop and remove the drain timer for a download slot."""
        timer = getattr(self, f"_{key}_log_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            setattr(self, f"_{key}_log_timer", None)

    def _drain_log(self, key: str) -> None:
        """Drain queued log lines from the worker and append to the widget.

        When the worker signals completion (``_done`` flag), this method
        also stops the timer, appends any error message, resets the button,
        and refreshes the setup status — all in the main thread.
        """
        slot = self._dl_slots[key]
        worker = getattr(self, slot.worker_attr, None)
        if worker is None or not hasattr(worker, "_stream"):
            self._stop_log_timer(key)
            return
        stream: _QueueStream = worker._stream
        while not stream.lines.empty():
            try:
                line = stream.lines.get_nowait()
                slot.output.appendPlainText(_strip_ansi(line))
            except queue.Empty:
                break
        # If the worker has finished, wrap up — all in the main thread.
        if worker._done:
            # Final drain in case flush() added lines after _done was set.
            while not stream.lines.empty():
                try:
                    slot.output.appendPlainText(
                        _strip_ansi(stream.lines.get_nowait())
                    )
                except queue.Empty:
                    break
            if worker._error_msg:
                slot.output.appendPlainText(f"ERROR: {worker._error_msg}")
            self._stop_log_timer(key)
            self._reset_download_button(key)
            self.load_setup()
            self._run_preflight()

    def _cancel_download(self, key: str) -> None:
        """Cancel a running download."""
        self._stop_log_timer(key)
        slot = self._dl_slots[key]
        thread = getattr(self, slot.thread_attr, None)
        worker = getattr(self, slot.worker_attr, None)
        if thread is not None and thread.isRunning():
            thread.terminate()
            thread.wait()
        # Drain any remaining lines after termination.
        if worker is not None and hasattr(worker, "_stream"):
            self._drain_log(key)
        # thread.terminate() skips the finally-block in
        # _run_with_redirected_output, so restore stdout/stderr here to
        # prevent a stale stream from receiving further writes.
        if worker is not None and hasattr(worker, "_prev_stdout"):
            sys.stdout = worker._prev_stdout
            sys.stderr = worker._prev_stderr
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

    def _on_dl_finished(self, key: str) -> None:
        """Handle download completion."""
        self._stop_log_timer(key)
        self._drain_log(key)
        self._reset_download_button(key)
        self.load_setup()
        self._run_preflight()

    def _on_dl_error(self, key: str, message: str) -> None:
        """Handle download error."""
        self._stop_log_timer(key)
        self._drain_log(key)
        slot = self._dl_slots[key]
        slot.output.appendPlainText(f"ERROR: {message}")
        self._reset_download_button(key)

    # ------------------------------------------------------------------
    # Per-download click handlers (thin wrappers)
    # ------------------------------------------------------------------

    def on_vllm_install_clicked(self) -> None:
        """Handle Install vLLM button click."""
        worker = _VllmInstallWorker()
        self._start_download("vllm", worker)

    def on_model_download_clicked(self) -> None:
        """Handle Download Model button click."""
        from aria.config.huggingface import HuggingFace

        alias = self.ui.comboBox_ModelSelect.currentText()
        token_text = (
            self.ui.lineEdit_HFToken.text().strip() or HuggingFace.token
        )
        force = self.ui.checkBox_ModelForce.isChecked()
        worker = _ModelDownloadWorker(
            alias=alias, token=token_text, force=force
        )
        self._start_download("model", worker)

    def on_lightpanda_download_clicked(self) -> None:
        """Handle Download Lightpanda button click."""
        from aria.config.api import Lightpanda

        version_text = (
            self.ui.lineEdit_LightpandaVersion.text().strip() or None
        )
        worker = _LightpandaDownloadWorker(
            bin_dir=Lightpanda.get_bin_path(), version=version_text
        )
        self._start_download("lightpanda", worker)
