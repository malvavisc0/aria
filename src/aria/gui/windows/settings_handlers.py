"""Settings tab handlers for the MainWindow."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtWidgets import QComboBox, QMainWindow

from aria.gui.ui.mainwindow import Ui_MainWindow
from aria.helpers.dotenv import parse_dotenv, write_dotenv
from aria.helpers.network import get_network_ip

_ENV_PATH = Path(".env")

CONTEXT_SIZES = [str(2**n) for n in range(11, 18)]
QUANT_TYPES = ["Q4_0", "Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"]


def _set_combo_value(combo: QComboBox, value: str) -> None:
    idx = combo.findText(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)
        return
    combo.addItem(value)
    combo.setCurrentIndex(combo.count() - 1)


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class SettingsHandlersMixin:
    """Mixin that adds Settings tab load/save behaviour to MainWindow."""

    ui: Ui_MainWindow

    def _status_bar(self):
        return cast(QMainWindow, self).statusBar()

    def _connect_settings_signals(self) -> None:
        self.ui.pushButton_SettingsSave.clicked.connect(self.save_settings)
        self.ui.pushButton_SettingsRevert.clicked.connect(self.load_settings)

    def _init_settings_choices(self) -> None:
        for combo in (self.ui.comboBox_ChatCtxSize,):
            combo.clear()
            combo.addItems(CONTEXT_SIZES)

        for combo in (self.ui.comboBox_ChatQuantType,):
            combo.clear()
            combo.addItems(QUANT_TYPES)

    def load_settings(self) -> None:
        self._init_settings_choices()
        values, self._env_raw_lines = parse_dotenv(_ENV_PATH)

        self.ui.checkBox_Debug.setChecked(
            values.get("DEBUG", "false").strip().lower() == "true"
        )
        # Always detect and show current network IP
        current_host = values.get("SERVER_HOST", "0.0.0.0")
        if current_host == "0.0.0.0":
            detected_ip = get_network_ip()
            self.ui.lineEdit_ServerHost.setText(detected_ip)
        else:
            # Check if current IP is still valid (may have changed on network change)
            detected_ip = get_network_ip()
            if detected_ip != current_host:
                # Network IP changed, update display but don't auto-save
                self.ui.lineEdit_ServerHost.setText(detected_ip)
            else:
                self.ui.lineEdit_ServerHost.setText(current_host)

        port = _safe_int(values.get("SERVER_PORT", "9876"), 9876)
        port = min(max(port, 1), 65535)
        self.ui.spinBox_ServerPort.setValue(port)

        self.ui.lineEdit_ChatRepo.setText(values.get("CHAT_MODEL_REPO", ""))
        self.ui.lineEdit_ChatModel.setText(values.get("CHAT_MODEL", ""))
        _set_combo_value(
            self.ui.comboBox_ChatQuantType,
            values.get("CHAT_MODEL_TYPE", "Q8_0"),
        )
        _set_combo_value(
            self.ui.comboBox_ChatCtxSize,
            values.get("CHAT_CONTEXT_SIZE", "32768"),
        )

        # Run preflight checks to verify configuration is valid
        from aria.preflight import run_preflight_checks

        preflight_result = run_preflight_checks()

        if preflight_result.passed:
            self._status_bar().showMessage(
                "Settings loaded — all checks passed. Server can be started.",
                5000,
            )
        else:
            failure_count = len(preflight_result.failures)
            self._status_bar().showMessage(
                f"Settings loaded — {failure_count} preflight check(s) failed. "
                "Fix issues before starting the server.",
                10000,
            )
            # Show tooltip with failure details
            failures = "\n".join(
                f"  • {c.name}: {c.error}" for c in preflight_result.failures
            )
            self.ui.pushButton_SettingsSave.setToolTip(
                f"Preflight checks failed:\n{failures}"
            )
        self._status_bar().showMessage("Settings loaded.", 3000)

    def save_settings(self) -> None:
        # Always detect and save current network IP
        values = {
            "DEBUG": "true" if self.ui.checkBox_Debug.isChecked() else "false",
            "SERVER_HOST": get_network_ip(),
            "SERVER_PORT": str(self.ui.spinBox_ServerPort.value()),
            "CHAT_MODEL_REPO": self.ui.lineEdit_ChatRepo.text().strip(),
            "CHAT_MODEL": self.ui.lineEdit_ChatModel.text().strip(),
            "CHAT_MODEL_TYPE": self.ui.comboBox_ChatQuantType.currentText(),
            "CHAT_CONTEXT_SIZE": self.ui.comboBox_ChatCtxSize.currentText(),
        }

        _, raw_lines = parse_dotenv(_ENV_PATH)
        write_dotenv(_ENV_PATH, values, raw_lines)

        # Run preflight checks to verify configuration is valid
        from aria.preflight import run_preflight_checks

        preflight_result = run_preflight_checks()

        if preflight_result.passed:
            self._status_bar().showMessage(
                "Settings saved — all checks passed. Restart the service to apply.",
                5000,
            )
        else:
            failure_count = len(preflight_result.failures)
            self._status_bar().showMessage(
                f"Settings saved — {failure_count} preflight check(s) failed. "
                "Restart the service to apply.",
                10000,
            )
            # Show tooltip with failure details
            failures = "\n".join(
                f"  • {c.name}: {c.error}" for c in preflight_result.failures
            )
            self.ui.pushButton_SettingsSave.setToolTip(
                f"Preflight checks failed:\n{failures}"
            )
