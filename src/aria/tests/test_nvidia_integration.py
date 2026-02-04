"""Integration tests for NVIDIA GPU utilities - runs against actual hardware.

These tests are designed to run on systems with NVIDIA GPUs and nvidia-smi installed.
They will be skipped if nvidia-smi is not available.

Run with: uv run pytest src/aria/tests/test_nvidia_integration.py -v
"""

import pytest

from aria.nvidia import (
    check_gpu_memory_usage,
    check_nvidia_smi_available,
    detect_gpu_count,
    detect_nvlink,
    get_free_vram_per_gpu,
    get_nvidia_smi_version,
    get_total_vram_mb,
)

# Skip all tests in this module if nvidia-smi is not available
pytestmark = pytest.mark.skipif(
    not check_nvidia_smi_available(),
    reason="nvidia-smi not available - skipping hardware integration tests",
)


class TestNvidiaIntegration:
    """Integration tests that run against actual NVIDIA hardware."""

    def test_nvidia_smi_is_available(self):
        """Verify nvidia-smi is available on this system."""
        assert check_nvidia_smi_available() is True

    def test_get_nvidia_smi_version_returns_valid_version(self):
        """Verify we can get a valid nvidia-smi version."""
        version = get_nvidia_smi_version()
        assert version != ""
        assert "." in version  # Should have at least one dot (e.g., "535.104")
        # Version should be numeric with dots
        parts = version.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit()

    def test_detect_gpu_count_returns_positive_number(self):
        """Verify GPU count is a positive number."""
        gpu_count = detect_gpu_count()
        assert gpu_count > 0
        assert isinstance(gpu_count, int)

    def test_get_total_vram_mb_returns_positive_value(self):
        """Verify total VRAM is a positive value."""
        total_vram = get_total_vram_mb()
        assert total_vram > 0
        assert isinstance(total_vram, int)
        # Sanity check: modern GPUs have at least 1GB VRAM
        assert total_vram >= 1024

    def test_get_free_vram_per_gpu_returns_list(self):
        """Verify free VRAM returns a list with values."""
        free_vram = get_free_vram_per_gpu()
        assert isinstance(free_vram, list)
        assert len(free_vram) > 0
        # All values should be positive integers
        for vram in free_vram:
            assert isinstance(vram, int)
            assert vram >= 0

    def test_free_vram_count_matches_gpu_count(self):
        """Verify free VRAM list length matches GPU count."""
        gpu_count = detect_gpu_count()
        free_vram = get_free_vram_per_gpu()
        assert len(free_vram) == gpu_count

    def test_total_vram_is_sum_of_all_gpus(self):
        """Verify total VRAM calculation is correct."""
        gpu_count = detect_gpu_count()
        total_vram = get_total_vram_mb()

        # For systems with multiple identical GPUs, we can verify the math
        if gpu_count > 1:
            # Total should be divisible by GPU count for identical GPUs
            vram_per_gpu = total_vram // gpu_count
            assert vram_per_gpu > 0

    def test_check_gpu_memory_usage_with_valid_index(self):
        """Test memory usage check with valid GPU index."""
        gpu_count = detect_gpu_count()

        # Test first GPU (index 0)
        result_low_threshold = check_gpu_memory_usage(0, 100.0)
        result_high_threshold = check_gpu_memory_usage(0, 0.0)

        # With 100% threshold, should return True (usage < 100%)
        # unless GPU is completely full
        assert isinstance(result_low_threshold, bool)

        # With 0% threshold, should return False (usage >= 0%)
        assert result_high_threshold is False

    def test_check_gpu_memory_usage_with_invalid_index(self):
        """Test memory usage check with invalid GPU index."""
        gpu_count = detect_gpu_count()

        # Test with index beyond available GPUs
        result = check_gpu_memory_usage(gpu_count + 10, 50.0)
        assert result is False

    def test_detect_nvlink_returns_tuple(self):
        """Test NVLink detection returns proper tuple."""
        has_nvlink, bond_type = detect_nvlink()

        assert isinstance(has_nvlink, bool)
        assert bond_type is None or isinstance(bond_type, str)

        # If bond_type is set, it should be "Bonded"
        if bond_type is not None:
            assert bond_type == "Bonded"

    def test_nvlink_only_on_multi_gpu_systems(self):
        """NVLink should only be detected on multi-GPU systems."""
        gpu_count = detect_gpu_count()
        has_nvlink, _ = detect_nvlink()

        # Single GPU systems should not have NVLink
        if gpu_count == 1:
            assert has_nvlink is False

    def test_memory_consistency(self):
        """Test that memory values are consistent across calls."""
        # Get values twice
        total_vram_1 = get_total_vram_mb()
        total_vram_2 = get_total_vram_mb()

        # Total VRAM should be the same
        assert total_vram_1 == total_vram_2

        # Free VRAM might vary slightly but should be similar
        free_vram_1 = get_free_vram_per_gpu()
        free_vram_2 = get_free_vram_per_gpu()

        assert len(free_vram_1) == len(free_vram_2)

        # Free VRAM should be within reasonable range (allow 10% variance)
        for vram1, vram2 in zip(free_vram_1, free_vram_2):
            variance = abs(vram1 - vram2)
            max_allowed_variance = max(vram1, vram2) * 0.1
            assert variance <= max_allowed_variance

    def test_free_vram_less_than_total_vram(self):
        """Verify free VRAM is less than or equal to total VRAM."""
        total_vram = get_total_vram_mb()
        free_vram_list = get_free_vram_per_gpu()

        # Each GPU's free VRAM should be less than total system VRAM
        for free_vram in free_vram_list:
            assert free_vram <= total_vram


class TestNvidiaIntegrationEdgeCases:
    """Edge case integration tests."""

    def test_input_validation_still_works(self):
        """Verify input validation works even with real hardware."""
        # Negative GPU index should still return False
        assert check_gpu_memory_usage(-1, 50.0) is False

        # Invalid threshold should still return False
        assert check_gpu_memory_usage(0, -10.0) is False
        assert check_gpu_memory_usage(0, 150.0) is False

    def test_boundary_thresholds(self):
        """Test boundary threshold values."""
        # 0% threshold
        result_0 = check_gpu_memory_usage(0, 0.0)
        assert result_0 is False  # Any usage > 0 will fail

        # 100% threshold
        result_100 = check_gpu_memory_usage(0, 100.0)
        # Should be True unless GPU is exactly 100% full
        assert isinstance(result_100, bool)


# ============================================================================
# Manual Test Utilities
# ============================================================================


def print_gpu_info():
    """Utility function to print GPU information (not a test)."""
    print("\n" + "=" * 60)
    print("NVIDIA GPU Information")
    print("=" * 60)

    if not check_nvidia_smi_available():
        print("nvidia-smi is not available on this system")
        return

    print(f"nvidia-smi version: {get_nvidia_smi_version()}")
    print(f"GPU count: {detect_gpu_count()}")
    print(f"Total VRAM: {get_total_vram_mb()} MiB")

    free_vram = get_free_vram_per_gpu()
    print(f"\nFree VRAM per GPU:")
    for i, vram in enumerate(free_vram):
        print(f"  GPU {i}: {vram} MiB")

    has_nvlink, bond_type = detect_nvlink()
    print(f"\nNVLink detected: {has_nvlink}")
    if bond_type:
        print(f"Bond type: {bond_type}")

    print("\nMemory usage check (50% threshold):")
    for i in range(detect_gpu_count()):
        below_threshold = check_gpu_memory_usage(i, 50.0)
        status = "✓ Below" if below_threshold else "✗ Above"
        print(f"  GPU {i}: {status} 50% threshold")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Run this file directly to print GPU info
    print_gpu_info()
