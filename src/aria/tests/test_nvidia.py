"""Comprehensive tests for NVIDIA GPU detection and monitoring utilities."""

import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from aria.helpers.nvidia import (
    GPUMetadata,
    check_gpu_memory_usage,
    check_nvidia_smi_available,
    detect_gpu_count,
    detect_gpus_with_details,
    detect_nvlink,
    get_free_vram_per_gpu,
    get_nvidia_smi_version,
    get_total_vram_mb,
)

# ============================================================================
# Mock Data Constants
# ============================================================================

MOCK_GPU_LIST_SINGLE = "GPU 0: NVIDIA GeForce RTX 3090 (UUID: GPU-xxx)"

MOCK_GPU_LIST_DUAL = """GPU 0: NVIDIA GeForce RTX 3090 (UUID: GPU-xxx)
GPU 1: NVIDIA GeForce RTX 3090 (UUID: GPU-yyy)"""

MOCK_GPU_LIST_QUAD = """GPU 0: NVIDIA GeForce RTX 3090 (UUID: GPU-aaa)
GPU 1: NVIDIA GeForce RTX 3090 (UUID: GPU-bbb)
GPU 2: NVIDIA GeForce RTX 3090 (UUID: GPU-ccc)
GPU 3: NVIDIA GeForce RTX 3090 (UUID: GPU-ddd)"""

MOCK_GPU_LIST_WITH_EMPTY_LINES = """GPU 0: NVIDIA GeForce RTX 3090 (UUID: GPU-xxx)

GPU 1: NVIDIA GeForce RTX 3090 (UUID: GPU-yyy)
"""

MOCK_VRAM_TOTAL_SINGLE = "24576"

MOCK_VRAM_TOTAL_DUAL = """24576
24576"""

MOCK_VRAM_TOTAL_QUAD = """24576
24576
24576
24576"""

MOCK_VRAM_FREE_DUAL = """20480
22528"""

MOCK_VRAM_MEMORY_USED_TOTAL = "12288, 24576"

MOCK_NVLINK_TOPOLOGY_WITH_NVLINK = """    GPU0    GPU1
GPU0     X      NV4
GPU1    NV4      X

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks"""

MOCK_NVLINK_TOPOLOGY_NO_NVLINK = """    GPU0    GPU1
GPU0     X      SYS
GPU1    SYS      X"""

MOCK_NVLINK_TOPOLOGY_BONDED = """    GPU0    GPU1
GPU0     X      NV2
GPU1    NV2      X

Bonded"""

MOCK_VERSION_OUTPUT = """NVIDIA-SMI 535.104.05    Driver Version: 535.104.05    CUDA Version: 12.2"""

MOCK_VERSION_OUTPUT_ALT = """NVIDIA-SMI 525.85.12
Driver Version: 525.85.12
CUDA Version: 12.0"""

MOCK_VERSION_OUTPUT_WITH_COLON = """NVIDIA-SMI version  : 590.48.01
NVML version        : 590.48
DRIVER version      : 590.48.01
CUDA Version        : 13.1"""

# Mock data for detect_gpus_with_details()
MOCK_GPU_DETAILS_SINGLE = """0, NVIDIA GeForce RTX 3090, GPU-12345678-1234-1234-1234-123456789012, 24576, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, Enabled"""

MOCK_GPU_DETAILS_DUAL = """0, NVIDIA GeForce RTX 3090, GPU-12345678-1234-1234-1234-123456789012, 24576, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, Enabled
1, NVIDIA GeForce RTX 3090, GPU-87654321-4321-4321-4321-210987654321, 24576, 8192, 16384, Default, 535.104.05, 350, 250, 58, 40, Disabled"""

MOCK_GPU_DETAILS_WITH_UNITS = """0, NVIDIA GeForce RTX 3090, GPU-12345678-1234-1234-1234-123456789012, 24576, 12288, 12288, Default, 535.104.05, 350W, 280W, 65C, 45%, Enabled"""

MOCK_GPU_DETAILS_MALFORMED = """0, NVIDIA GeForce RTX 3090, GPU-12345678"""

MOCK_GPU_DETAILS_INVALID_NUMBERS = """0, NVIDIA GeForce RTX 3090, GPU-12345678-1234-1234-1234-123456789012, invalid, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, Enabled"""

MOCK_GPU_DETAILS_EMPTY_VALUES = """0, NVIDIA GeForce RTX 3090, GPU-12345678-1234-1234-1234-123456789012, , , , Default, 535.104.05, , , , , Enabled"""

MOCK_GPU_DETAILS_DISPLAY_VARIATIONS = """0, GPU1, UUID1, 24576, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, enabled
1, GPU2, UUID2, 24576, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, ENABLED
2, GPU3, UUID3, 24576, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, Disabled
3, GPU4, UUID4, 24576, 12288, 12288, Default, 535.104.05, 350, 280, 65, 45, disabled"""


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_subprocess_success():
    """Create a mock for successful subprocess.run calls."""

    def _mock_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        return mock_result

    return _mock_run


@pytest.fixture
def mock_subprocess_failure():
    """Create a mock that raises CalledProcessError."""

    def _mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, "Error")

    return _mock_run


@pytest.fixture
def mock_subprocess_not_found():
    """Create a mock that raises FileNotFoundError."""

    def _mock_run(cmd, **kwargs):
        raise FileNotFoundError("nvidia-smi not found")

    return _mock_run


# ============================================================================
# Tests for detect_gpu_count()
# ============================================================================


class TestDetectGpuCount:
    """Test suite for detect_gpu_count function."""

    def test_single_gpu(self):
        """Test detection of single GPU."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_LIST_SINGLE
            )
            assert detect_gpu_count() == 1

    def test_dual_gpu(self):
        """Test detection of two GPUs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_LIST_DUAL
            )
            assert detect_gpu_count() == 2

    def test_quad_gpu(self):
        """Test detection of four GPUs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_LIST_QUAD
            )
            assert detect_gpu_count() == 4

    def test_no_gpus_empty_output(self):
        """Test handling of empty output (no GPUs)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            assert detect_gpu_count() == 0

    def test_output_with_empty_lines(self):
        """Test that empty lines are filtered correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_LIST_WITH_EMPTY_LINES
            )
            # Should still detect 2 GPUs despite empty lines
            assert detect_gpu_count() == 2

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            assert detect_gpu_count() == 0

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            assert detect_gpu_count() == 0

    def test_whitespace_only_lines(self):
        """Test handling of whitespace-only lines."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="   \n\t\n  \n")
            assert detect_gpu_count() == 0


# ============================================================================
# Tests for get_total_vram_mb()
# ============================================================================


class TestGetTotalVramMb:
    """Test suite for get_total_vram_mb function."""

    def test_single_gpu_vram(self):
        """Test VRAM calculation for single GPU."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_TOTAL_SINGLE
            )
            assert get_total_vram_mb() == 24576

    def test_dual_gpu_vram(self):
        """Test VRAM calculation for two GPUs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_TOTAL_DUAL
            )
            assert get_total_vram_mb() == 49152  # 24576 * 2

    def test_quad_gpu_vram(self):
        """Test VRAM calculation for four GPUs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_TOTAL_QUAD
            )
            assert get_total_vram_mb() == 98304  # 24576 * 4

    def test_empty_output(self):
        """Test handling of empty output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            assert get_total_vram_mb() == 0

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            assert get_total_vram_mb() == 0

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            assert get_total_vram_mb() == 0

    def test_invalid_vram_values(self):
        """Test handling of non-numeric VRAM values."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="invalid\ndata")
            assert get_total_vram_mb() == 0

    def test_mixed_valid_invalid_values(self):
        """Test handling of mixed valid and invalid values."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="24576\ninvalid\n16384"
            )
            # Should fail on first invalid value
            assert get_total_vram_mb() == 0

    def test_vram_with_empty_lines(self):
        """Test that empty lines are filtered correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="24576\n\n24576\n"
            )
            assert get_total_vram_mb() == 49152


# ============================================================================
# Tests for check_gpu_memory_usage()
# ============================================================================


class TestCheckGpuMemoryUsage:
    """Test suite for check_gpu_memory_usage function."""

    def test_usage_below_threshold(self):
        """Test when memory usage is below threshold."""
        with patch("subprocess.run") as mock_run:
            # 12288 MB used out of 24576 MB = 50% usage
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_MEMORY_USED_TOTAL
            )
            # 50% < 75% threshold
            assert check_gpu_memory_usage(0, 75.0) is True

    def test_usage_above_threshold(self):
        """Test when memory usage is above threshold."""
        with patch("subprocess.run") as mock_run:
            # 12288 MB used out of 24576 MB = 50% usage
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_MEMORY_USED_TOTAL
            )
            # 50% > 25% threshold
            assert check_gpu_memory_usage(0, 25.0) is False

    def test_usage_exactly_at_threshold(self):
        """Test when memory usage equals threshold."""
        with patch("subprocess.run") as mock_run:
            # 12288 MB used out of 24576 MB = 50% usage
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_MEMORY_USED_TOTAL
            )
            # 50% == 50% threshold, should return False (not below)
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_negative_gpu_index(self):
        """Test input validation for negative GPU index."""
        assert check_gpu_memory_usage(-1, 50.0) is False

    def test_negative_threshold(self):
        """Test input validation for negative threshold."""
        assert check_gpu_memory_usage(0, -10.0) is False

    def test_threshold_above_100(self):
        """Test input validation for threshold > 100."""
        assert check_gpu_memory_usage(0, 150.0) is False

    def test_threshold_zero(self):
        """Test edge case with threshold of 0."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_MEMORY_USED_TOTAL
            )
            # Any usage > 0% will be above 0% threshold
            assert check_gpu_memory_usage(0, 0.0) is False

    def test_threshold_100(self):
        """Test edge case with threshold of 100."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_MEMORY_USED_TOTAL
            )
            # 50% < 100% threshold
            assert check_gpu_memory_usage(0, 100.0) is True

    def test_zero_total_memory(self):
        """Test handling of zero total memory (edge case)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="0, 0")
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_invalid_gpu_index(self):
        """Test handling of invalid GPU index."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Invalid GPU index"
            )
            assert check_gpu_memory_usage(99, 50.0) is False

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_invalid_memory_values(self):
        """Test handling of non-numeric memory values."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="invalid, data")
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_malformed_output_single_value(self):
        """Test handling of malformed output with single value."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="12288")
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_malformed_output_too_many_values(self):
        """Test handling of malformed output with too many values."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="12288, 24576, 8192"
            )
            assert check_gpu_memory_usage(0, 50.0) is False

    def test_full_memory_usage(self):
        """Test when GPU memory is fully utilized."""
        with patch("subprocess.run") as mock_run:
            # 24576 MB used out of 24576 MB = 100% usage
            mock_run.return_value = Mock(returncode=0, stdout="24576, 24576")
            assert check_gpu_memory_usage(0, 100.0) is False
            assert check_gpu_memory_usage(0, 99.0) is False

    def test_minimal_memory_usage(self):
        """Test when GPU memory usage is minimal."""
        with patch("subprocess.run") as mock_run:
            # 100 MB used out of 24576 MB ≈ 0.4% usage
            mock_run.return_value = Mock(returncode=0, stdout="100, 24576")
            assert check_gpu_memory_usage(0, 1.0) is True
            assert check_gpu_memory_usage(0, 0.5) is True


# ============================================================================
# Tests for get_free_vram_per_gpu()
# ============================================================================


class TestGetFreeVramPerGpu:
    """Test suite for get_free_vram_per_gpu function."""

    def test_dual_gpu_free_vram(self):
        """Test free VRAM for two GPUs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VRAM_FREE_DUAL
            )
            result = get_free_vram_per_gpu()
            assert result == [20480, 22528]

    def test_single_gpu_free_vram(self):
        """Test free VRAM for single GPU."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="20480")
            result = get_free_vram_per_gpu()
            assert result == [20480]

    def test_empty_output(self):
        """Test handling of empty output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            assert get_free_vram_per_gpu() == []

    def test_output_with_empty_lines(self):
        """Test that empty lines are filtered correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="20480\n\n22528\n"
            )
            result = get_free_vram_per_gpu()
            assert result == [20480, 22528]

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            assert get_free_vram_per_gpu() == []

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            assert get_free_vram_per_gpu() == []

    def test_invalid_vram_values(self):
        """Test handling of non-numeric VRAM values."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="invalid\ndata")
            assert get_free_vram_per_gpu() == []

    def test_quad_gpu_free_vram(self):
        """Test free VRAM for four GPUs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="20480\n22528\n18432\n21504"
            )
            result = get_free_vram_per_gpu()
            assert result == [20480, 22528, 18432, 21504]
            assert len(result) == 4


# ============================================================================
# Tests for detect_nvlink()
# ============================================================================


class TestDetectNvlink:
    """Test suite for detect_nvlink function."""

    def test_nvlink_detected(self):
        """Test detection of NVLink connectivity."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_NVLINK_TOPOLOGY_WITH_NVLINK
            )
            has_nvlink, bond_type = detect_nvlink()
            assert has_nvlink is True
            assert bond_type is None  # No "Bonded" keyword in this output

    def test_nvlink_with_bonding(self):
        """Test detection of NVLink with bonding."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_NVLINK_TOPOLOGY_BONDED
            )
            has_nvlink, bond_type = detect_nvlink()
            assert has_nvlink is True
            assert bond_type == "Bonded"

    def test_no_nvlink(self):
        """Test when no NVLink is present (PCIe only)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_NVLINK_TOPOLOGY_NO_NVLINK
            )
            has_nvlink, bond_type = detect_nvlink()
            assert has_nvlink is False
            assert bond_type is None

    def test_empty_topology_output(self):
        """Test handling of empty topology output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            has_nvlink, bond_type = detect_nvlink()
            assert has_nvlink is False
            assert bond_type is None

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            has_nvlink, bond_type = detect_nvlink()
            assert has_nvlink is False
            assert bond_type is None

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            has_nvlink, bond_type = detect_nvlink()
            assert has_nvlink is False
            assert bond_type is None

    def test_nvlink_different_versions(self):
        """Test detection of different NVLink versions."""
        topologies = [
            "GPU0  X  NV1\nGPU1 NV1  X",
            "GPU0  X  NV2\nGPU1 NV2  X",
            "GPU0  X  NV4\nGPU1 NV4  X",
            "GPU0  X  NV8\nGPU1 NV8  X",
        ]
        for topology in topologies:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout=topology)
                has_nvlink, _ = detect_nvlink()
                assert has_nvlink is True


# ============================================================================
# Tests for check_nvidia_smi_available()
# ============================================================================


class TestCheckNvidiaSmiAvailable:
    """Test suite for check_nvidia_smi_available function."""

    def test_nvidia_smi_available(self):
        """Test when nvidia-smi is available."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VERSION_OUTPUT
            )
            assert check_nvidia_smi_available() is True

    def test_nvidia_smi_not_found(self):
        """Test when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            assert check_nvidia_smi_available() is False

    def test_nvidia_smi_fails(self):
        """Test when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            assert check_nvidia_smi_available() is False

    def test_nvidia_smi_permission_denied(self):
        """Test when nvidia-smi exists but permission is denied."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                126, "nvidia-smi", "Permission denied"
            )
            assert check_nvidia_smi_available() is False


# ============================================================================
# Tests for get_nvidia_smi_version()
# ============================================================================


class TestGetNvidiaSmiVersion:
    """Test suite for get_nvidia_smi_version function."""

    def test_version_standard_format(self):
        """Test parsing of standard version format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VERSION_OUTPUT
            )
            version = get_nvidia_smi_version()
            assert version == "535.104.05"

    def test_version_alternative_format(self):
        """Test parsing of alternative version format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VERSION_OUTPUT_ALT
            )
            version = get_nvidia_smi_version()
            assert version == "525.85.12"

    def test_version_two_part(self):
        """Test parsing of two-part version number."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="NVIDIA-SMI 535.104"
            )
            version = get_nvidia_smi_version()
            assert version == "535.104"

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            assert get_nvidia_smi_version() == ""

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            assert get_nvidia_smi_version() == ""

    def test_unexpected_output_format(self):
        """Test handling of unexpected output format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Unexpected output format"
            )
            assert get_nvidia_smi_version() == ""

    def test_empty_output(self):
        """Test handling of empty output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            assert get_nvidia_smi_version() == ""

    def test_version_with_extra_text(self):
        """Test parsing version with extra text around it."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Some text\nNVIDIA-SMI 470.129.06\nMore text",
            )
            version = get_nvidia_smi_version()
            assert version == "470.129.06"

    def test_version_with_colon_format(self):
        """Test parsing version with 'version  :' format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_VERSION_OUTPUT_WITH_COLON
            )
            version = get_nvidia_smi_version()
            assert version == "590.48.01"


# ============================================================================
# Tests for detect_gpus_with_details()
# ============================================================================


class TestDetectGpusWithDetails:
    """Test suite for detect_gpus_with_details function."""

    def test_single_gpu_with_details(self):
        """Test detection of single GPU with full details."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_SINGLE
            )
            gpus = detect_gpus_with_details()

            assert len(gpus) == 1
            gpu = gpus[0]

            assert isinstance(gpu, GPUMetadata)
            assert gpu.index == 0
            assert gpu.name == "NVIDIA GeForce RTX 3090"
            assert gpu.uuid == "GPU-12345678-1234-1234-1234-123456789012"
            assert gpu.total_memory == 24576
            assert gpu.used_memory == 12288
            assert gpu.free_memory == 12288
            assert gpu.memory_utilization == 50.0
            assert gpu.power_limit == 350
            assert gpu.power_draw == 280
            assert gpu.temperature == 65
            assert gpu.fan_speed == 45
            assert gpu.driver_version == "535.104.05"
            assert gpu.display_active is True
            assert gpu.compute_mode == "Default"

    def test_dual_gpu_with_details(self):
        """Test detection of two GPUs with different states."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_DUAL
            )
            gpus = detect_gpus_with_details()

            assert len(gpus) == 2

            # First GPU
            assert gpus[0].index == 0
            assert gpus[0].memory_utilization == 50.0
            assert gpus[0].display_active is True

            # Second GPU
            assert gpus[1].index == 1
            assert gpus[1].used_memory == 8192
            assert gpus[1].free_memory == 16384
            assert gpus[1].memory_utilization == 33.33
            assert gpus[1].power_draw == 250
            assert gpus[1].temperature == 58
            assert gpus[1].fan_speed == 40
            assert gpus[1].display_active is False

    def test_gpu_with_unit_suffixes(self):
        """Test parsing values with unit suffixes (W, C, %)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_WITH_UNITS
            )
            gpus = detect_gpus_with_details()

            assert len(gpus) == 1
            gpu = gpus[0]

            # Should correctly parse values with units
            assert gpu.power_limit == 350
            assert gpu.power_draw == 280
            assert gpu.temperature == 65
            assert gpu.fan_speed == 45

    def test_empty_output(self):
        """Test handling of empty output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            gpus = detect_gpus_with_details()
            assert gpus == []

    def test_malformed_csv_line(self):
        """Test handling of malformed CSV with insufficient columns."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_MALFORMED
            )
            gpus = detect_gpus_with_details()
            # Should skip malformed lines
            assert gpus == []

    def test_invalid_numeric_values(self):
        """Test handling of invalid numeric values in memory fields."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_INVALID_NUMBERS
            )
            gpus = detect_gpus_with_details()
            # Should skip lines with invalid numbers
            assert gpus == []

    def test_empty_field_values(self):
        """Test handling of empty field values."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_EMPTY_VALUES
            )
            gpus = detect_gpus_with_details()

            assert len(gpus) == 1
            gpu = gpus[0]

            # Empty values should default to 0
            assert gpu.total_memory == 0
            assert gpu.used_memory == 0
            assert gpu.free_memory == 0
            assert gpu.memory_utilization == 0.0
            assert gpu.power_limit == 0
            assert gpu.power_draw == 0
            assert gpu.temperature == 0
            assert gpu.fan_speed == 0

    def test_display_active_variations(self):
        """Test different variations of display_active field."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_DISPLAY_VARIATIONS
            )
            gpus = detect_gpus_with_details()

            assert len(gpus) == 4
            # "enabled" (lowercase)
            assert gpus[0].display_active is True
            # "ENABLED" (uppercase)
            assert gpus[1].display_active is True
            # "Disabled"
            assert gpus[2].display_active is False
            # "disabled"
            assert gpus[3].display_active is False

    def test_nvidia_smi_not_found(self):
        """Test handling when nvidia-smi is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            gpus = detect_gpus_with_details()
            assert gpus == []

    def test_nvidia_smi_fails(self):
        """Test handling when nvidia-smi command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "nvidia-smi", "Error"
            )
            gpus = detect_gpus_with_details()
            assert gpus == []

    def test_output_with_empty_lines(self):
        """Test that empty lines are filtered correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_SINGLE + "\n\n\n"
            )
            gpus = detect_gpus_with_details()
            assert len(gpus) == 1

    def test_memory_utilization_calculation(self):
        """Test memory utilization percentage calculation."""
        with patch("subprocess.run") as mock_run:
            # 12288 / 24576 = 50%
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_SINGLE
            )
            gpus = detect_gpus_with_details()
            assert gpus[0].memory_utilization == 50.0

    def test_zero_total_memory(self):
        """Test handling of zero total memory (edge case)."""
        mock_data = """0, GPU, UUID, 0, 0, 0, Default, 535.104.05, 350, 280, 65, 45, Enabled"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_data)
            gpus = detect_gpus_with_details()

            assert len(gpus) == 1
            assert gpus[0].memory_utilization == 0.0

    def test_pydantic_model_validation(self):
        """Test that GPUMetadata model validates correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=MOCK_GPU_DETAILS_SINGLE
            )
            gpus = detect_gpus_with_details()

            gpu = gpus[0]
            # Test that we can access all fields
            assert hasattr(gpu, "index")
            assert hasattr(gpu, "name")
            assert hasattr(gpu, "uuid")
            assert hasattr(gpu, "total_memory")
            assert hasattr(gpu, "used_memory")
            assert hasattr(gpu, "free_memory")
            assert hasattr(gpu, "memory_utilization")
            assert hasattr(gpu, "power_limit")
            assert hasattr(gpu, "power_draw")
            assert hasattr(gpu, "temperature")
            assert hasattr(gpu, "fan_speed")
            assert hasattr(gpu, "driver_version")
            assert hasattr(gpu, "display_active")
            assert hasattr(gpu, "compute_mode")

    def test_float_values_in_memory(self):
        """Test handling of float values in memory fields."""
        mock_data = """0, GPU, UUID, 24576.5, 12288.3, 12288.2, Default, 535.104.05, 350, 280, 65, 45, Enabled"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_data)
            gpus = detect_gpus_with_details()

            assert len(gpus) == 1
            # Should convert floats to ints
            assert gpus[0].total_memory == 24576
            assert gpus[0].used_memory == 12288
            assert gpus[0].free_memory == 12288


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for nvidia module functions."""

    def test_availability_check_before_operations(self):
        """Test checking availability before performing operations."""
        with patch("subprocess.run") as mock_run:
            # First call: check availability
            # Subsequent calls: actual operations
            mock_run.side_effect = [
                Mock(returncode=0, stdout=MOCK_VERSION_OUTPUT),  # available
                Mock(returncode=0, stdout=MOCK_GPU_LIST_DUAL),  # gpu count
                Mock(returncode=0, stdout=MOCK_VRAM_TOTAL_DUAL),  # total vram
            ]

            # Check if nvidia-smi is available first
            if check_nvidia_smi_available():
                gpu_count = detect_gpu_count()
                total_vram = get_total_vram_mb()

                assert gpu_count == 2
                assert total_vram == 49152

    def test_graceful_degradation_when_unavailable(self):
        """Test that all functions degrade gracefully when nvidia-smi is unavailable."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

            # All functions should return safe defaults
            assert check_nvidia_smi_available() is False
            assert detect_gpu_count() == 0
            assert get_total_vram_mb() == 0
            assert get_free_vram_per_gpu() == []
            assert check_gpu_memory_usage(0, 50.0) is False
            assert detect_nvlink() == (False, None)
            assert get_nvidia_smi_version() == ""
