"""Tests for vLLM install detection utilities in scripts/vllm.py."""

import importlib.metadata
from unittest.mock import MagicMock, patch

import pytest

from aria.scripts.vllm import (
    detect_install_target,
    get_vllm_version,
    is_vllm_installed,
)


class TestDetectInstallTarget:
    """Tests for detect_install_target()."""

    def test_returns_cu126_for_cuda_126(self):
        """CUDA 12.6+ should map to cu126."""
        with patch(
            "aria.helpers.nvidia.get_cuda_version", return_value="12.6"
        ):
            result = detect_install_target()
        assert result == "cu126"

    def test_returns_cu124_for_cuda_124(self):
        """CUDA 12.4 should map to cu124."""
        with patch(
            "aria.helpers.nvidia.get_cuda_version", return_value="12.4"
        ):
            result = detect_install_target()
        assert result == "cu124"

    def test_returns_cu121_for_cuda_121(self):
        """CUDA 12.1 should map to cu121."""
        with patch(
            "aria.helpers.nvidia.get_cuda_version", return_value="12.1"
        ):
            result = detect_install_target()
        assert result == "cu121"

    def test_returns_rocm6_when_rocm_smi_present(self):
        """rocm-smi on PATH should map to rocm6."""
        with (
            patch(
                "aria.helpers.nvidia.get_cuda_version",
                return_value=None,
            ),
            patch("shutil.which", return_value="/usr/bin/rocm-smi"),
        ):
            result = detect_install_target()
        assert result == "rocm6"

    def test_returns_cpu_when_no_gpu(self):
        """No GPU detection → cpu fallback."""
        with (
            patch(
                "aria.helpers.nvidia.get_cuda_version",
                return_value=None,
            ),
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.is_dir", return_value=False),
        ):
            result = detect_install_target()
        assert result == "cpu"

    def test_returns_string(self):
        """Result must always be a known target string."""
        result = detect_install_target()
        assert isinstance(result, str)
        assert result in ("cu126", "cu124", "cu121", "cu118", "rocm6", "cpu")


class TestIsVllmInstalled:
    """Tests for is_vllm_installed()."""

    def test_returns_true_when_installed(self):
        """Should return True when vllm metadata is available."""
        with patch.object(
            importlib.metadata, "version", return_value="0.20.0"
        ):
            assert is_vllm_installed() is True

    def test_returns_false_when_not_installed(self):
        """Should return False when vllm is not installed."""
        with patch.object(
            importlib.metadata,
            "version",
            side_effect=importlib.metadata.PackageNotFoundError("vllm"),
        ):
            assert is_vllm_installed() is False


class TestGetVllmVersion:
    """Tests for get_vllm_version()."""

    def test_returns_version_string(self):
        """Should return version string when vllm is installed."""
        with patch.object(
            importlib.metadata, "version", return_value="0.20.0"
        ):
            assert get_vllm_version() == "0.20.0"

    def test_returns_empty_string_when_not_installed(self):
        """Should return empty string when vllm is not installed."""
        with patch.object(
            importlib.metadata,
            "version",
            side_effect=importlib.metadata.PackageNotFoundError("vllm"),
        ):
            assert get_vllm_version() == ""
