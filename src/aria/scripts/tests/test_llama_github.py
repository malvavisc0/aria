"""Tests for GitHub API integration functions in llama.py."""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from aria.scripts.llama import (
    _find_linux_binary_asset,
    _find_macos_binary_asset,
    _find_windows_binary_asset,
    _get_latest_release_info,
    _get_release_by_tag,
)


class TestGetLatestReleaseInfo:
    """Tests for _get_latest_release_info() function."""

    def test_returns_valid_release_info(self):
        """Test that _get_latest_release_info returns valid release info."""
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"tag_name": "v1.2.3", "assets": []}'
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = _get_latest_release_info()

            assert result["tag_name"] == "v1.2.3"
            assert result["assets"] == []

    def test_returns_release_with_assets(self):
        """Test that _get_latest_release_info returns release with assets."""
        mock_response = MagicMock()
        assets = [
            {
                "name": "ubuntu-x64.tar.gz",
                "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
            },
            {
                "name": "linux-gpu.tar.gz",
                "browser_download_url": "https://example.com/linux-gpu.tar.gz",
            },
        ]
        mock_response.read.return_value = (
            b'{"tag_name": "v1.2.3", "assets": '
            + __import__("json").dumps(assets).encode()
            + b"}"
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = _get_latest_release_info()

            assert result["tag_name"] == "v1.2.3"
            assert len(result["assets"]) == 2
            assert result["assets"][0]["name"] == "ubuntu-x64.tar.gz"

    def test_raises_url_error_on_network_failure(self):
        """Test that _get_latest_release_info raises URLError on network failure."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(urllib.error.URLError):
                _get_latest_release_info()

    def test_raises_exception_on_invalid_json(self):
        """Test that _get_latest_release_info raises exception on invalid JSON."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"invalid json'

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with pytest.raises(ValueError):
                _get_latest_release_info()


class TestGetReleaseByTag:
    """Tests for _get_release_by_tag() function."""

    def test_returns_release_info_for_valid_tag(self):
        """Test that _get_release_by_tag returns release info for valid tag."""
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"tag_name": "v1.2.3", "assets": []}'
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = _get_release_by_tag("v1.2.3")

            assert result["tag_name"] == "v1.2.3"
            mock_urlopen.assert_called_once()

    def test_raises_url_error_for_invalid_tag(self):
        """Test that _get_release_by_tag raises URLError for invalid tag."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Not found")

            with pytest.raises(urllib.error.URLError):
                _get_release_by_tag("invalid-tag")

    def test_raises_exception_on_network_failure(self):
        """Test that _get_release_by_tag raises exception on network failure."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(urllib.error.URLError):
                _get_release_by_tag("v1.2.3")


class TestFindLinuxBinaryAsset:
    """Tests for _find_linux_binary_asset() function."""

    def test_finds_ubuntu_x64_binary(self):
        """Test that _find_linux_binary_asset finds ubuntu-x64 binary."""
        assets = [
            {
                "name": "ubuntu-x64.tar.gz",
                "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
            },
            {
                "name": "linux-gpu.tar.gz",
                "browser_download_url": "https://example.com/linux-gpu.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "ubuntu-x64.tar.gz"

    def test_finds_ubuntu_vulkan_binary(self):
        """Test that _find_linux_binary_asset finds ubuntu-vulkan binary when no ubuntu-x64."""
        assets = [
            {
                "name": "ubuntu-vulkan.tar.gz",
                "browser_download_url": "https://example.com/ubuntu-vulkan.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "ubuntu-vulkan.tar.gz"

    def test_finds_linux_gpu_cuda_binary(self):
        """Test that _find_linux_binary_asset finds linux-gpu-cuda binary."""
        assets = [
            {
                "name": "linux-gpu-cuda.tar.gz",
                "browser_download_url": "https://example.com/linux-gpu-cuda.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux-gpu-cuda.tar.gz"

    def test_finds_linux_gpu_binary(self):
        """Test that _find_linux_binary_asset finds linux-gpu binary."""
        assets = [
            {
                "name": "linux-gpu.tar.gz",
                "browser_download_url": "https://example.com/linux-gpu.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux-gpu.tar.gz"

    def test_finds_linux_cuda_binary(self):
        """Test that _find_linux_binary_asset finds linux-cuda binary."""
        assets = [
            {
                "name": "linux-cuda.tar.gz",
                "browser_download_url": "https://example.com/linux-cuda.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux-cuda.tar.gz"

    def test_finds_generic_linux_binary(self):
        """Test that _find_linux_binary_asset finds generic linux binary."""
        assets = [
            {
                "name": "linux.tar.gz",
                "browser_download_url": "https://example.com/linux.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux.tar.gz"

    def test_returns_none_when_no_linux_asset(self):
        """Test that _find_linux_binary_asset returns None when no Linux asset."""
        assets = [
            {
                "name": "macos-x64.zip",
                "browser_download_url": "https://example.com/macos-x64.tar.gz",
            },
            {
                "name": "windows-x64.zip",
                "browser_download_url": "https://example.com/windows-x64.zip",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is None

    def test_returns_none_for_empty_assets(self):
        """Test that _find_linux_binary_asset returns None for empty assets."""
        assets = []

        result = _find_linux_binary_asset(assets)

        assert result is None

    def test_ignores_non_tar_gz_files(self):
        """Test that _find_linux_binary_asset ignores non-tar.gz files."""
        assets = [
            {
                "name": "ubuntu-x64.zip",
                "browser_download_url": "https://example.com/ubuntu-x64.zip",
            },
            {
                "name": "linux.tar.gz",
                "browser_download_url": "https://example.com/linux.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux.tar.gz"

    def test_priority_order_respected(self):
        """Test that _find_linux_binary_asset respects priority order."""
        assets = [
            {
                "name": "linux.tar.gz",
                "browser_download_url": "https://example.com/linux.tar.gz",
            },
            {
                "name": "ubuntu-x64.tar.gz",
                "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        # Should prefer ubuntu-x64 over generic linux
        assert result is not None
        assert result["name"] == "ubuntu-x64.tar.gz"

    def test_handles_asset_without_name(self):
        """Test that _find_linux_binary_asset handles asset without name."""
        assets = [
            {"browser_download_url": "https://example.com/unknown"},
            {
                "name": "linux.tar.gz",
                "browser_download_url": "https://example.com/linux.tar.gz",
            },
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux.tar.gz"

    def test_handles_asset_without_download_url(self):
        """Test that _find_linux_binary_asset handles asset without download URL."""
        assets = [
            {"name": "linux.tar.gz"},
        ]

        result = _find_linux_binary_asset(assets)

        assert result is not None
        assert result["name"] == "linux.tar.gz"


class TestFindMacosBinaryAsset:
    """Tests for _find_macos_binary_asset() function."""

    def test_finds_arm64_asset_by_default(self):
        """Test that _find_macos_binary_asset finds arm64 asset on Apple Silicon."""
        assets = [
            {
                "name": "llama-b5000-bin-macos-arm64.tar.gz",
                "browser_download_url": "https://example.com/macos-arm64.tar.gz",
            },
            {
                "name": "llama-b5000-bin-macos-x64.tar.gz",
                "browser_download_url": "https://example.com/macos-x64.tar.gz",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos-arm64.tar.gz"

    def test_finds_x64_asset_for_intel(self):
        """Test that _find_macos_binary_asset finds x64 asset on Intel Mac."""
        assets = [
            {
                "name": "llama-b5000-bin-macos-arm64.tar.gz",
                "browser_download_url": "https://example.com/macos-arm64.tar.gz",
            },
            {
                "name": "llama-b5000-bin-macos-x64.tar.gz",
                "browser_download_url": "https://example.com/macos-x64.tar.gz",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="x86_64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos-x64.tar.gz"

    def test_falls_back_to_generic_macos(self):
        """Test that _find_macos_binary_asset falls back to any macos asset."""
        assets = [
            {
                "name": "llama-b5000-bin-macos.zip",
                "browser_download_url": "https://example.com/macos.zip",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos.zip"

    def test_returns_none_when_no_macos_asset(self):
        """Test that _find_macos_binary_asset returns None when no macOS asset."""
        assets = [
            {
                "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
            },
            {
                "name": "llama-b5000-bin-win-cpu-x64.zip",
                "browser_download_url": "https://example.com/win-cpu-x64.zip",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is None

    def test_returns_none_for_empty_assets(self):
        """Test that _find_macos_binary_asset returns None for empty assets list."""
        result = _find_macos_binary_asset([], arch="arm64")
        assert result is None

    def test_accepts_tar_gz_format(self):
        """Test that _find_macos_binary_asset accepts .tar.gz format (current b8000+ releases)."""
        assets = [
            {
                "name": "llama-b5000-bin-macos-arm64.tar.gz",
                "browser_download_url": "https://example.com/macos-arm64.tar.gz",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos-arm64.tar.gz"

    def test_accepts_zip_format(self):
        """Test that _find_macos_binary_asset also accepts .zip format (older releases)."""
        assets = [
            {
                "name": "llama-b5000-bin-macos-arm64.zip",
                "browser_download_url": "https://example.com/macos-arm64.zip",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos-arm64.zip"

    def test_ignores_other_archive_formats(self):
        """Test that _find_macos_binary_asset ignores unsupported archive formats."""
        assets = [
            {
                "name": "llama-b5000-bin-macos-arm64.7z",
                "browser_download_url": "https://example.com/macos-arm64.7z",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is None

    def test_ignores_src_archives(self):
        """Test that _find_macos_binary_asset ignores source archives."""
        assets = [
            {
                "name": "llama-b5000-macos-src.zip",
                "browser_download_url": "https://example.com/macos-src.zip",
            },
            {
                "name": "llama-b5000-bin-macos-arm64.tar.gz",
                "browser_download_url": "https://example.com/macos-arm64.tar.gz",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="arm64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos-arm64.tar.gz"

    def test_treats_aarch64_as_arm64(self):
        """Test that _find_macos_binary_asset treats aarch64 as arm64."""
        assets = [
            {
                "name": "llama-b5000-bin-macos-arm64.tar.gz",
                "browser_download_url": "https://example.com/macos-arm64.tar.gz",
            },
        ]

        result = _find_macos_binary_asset(assets, arch="aarch64")

        assert result is not None
        assert result["name"] == "llama-b5000-bin-macos-arm64.tar.gz"


class TestFindWindowsBinaryAsset:
    """Tests for _find_windows_binary_asset() function."""

    def test_finds_avx2_asset_without_cuda(self):
        """Test that _find_windows_binary_asset finds avx2 asset when CUDA not preferred."""
        assets = [
            {
                "name": "llama-b5000-bin-win-cpu-x64.zip",
                "browser_download_url": "https://example.com/win-cpu-x64.zip",
            },
            {
                "name": "llama-b5000-bin-win-cuda-cu12.4.1-x64.zip",
                "browser_download_url": "https://example.com/win-cuda-x64.zip",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=False)

        assert result is not None
        assert result["name"] == "llama-b5000-bin-win-cpu-x64.zip"

    def test_finds_cuda_asset_when_cuda_preferred(self):
        """Test that _find_windows_binary_asset finds CUDA asset when CUDA preferred."""
        assets = [
            {
                "name": "llama-b5000-bin-win-cpu-x64.zip",
                "browser_download_url": "https://example.com/win-cpu-x64.zip",
            },
            {
                "name": "llama-b5000-bin-win-cuda-cu12.4.1-x64.zip",
                "browser_download_url": "https://example.com/win-cuda-x64.zip",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=True)

        assert result is not None
        assert result["name"] == "llama-b5000-bin-win-cuda-cu12.4.1-x64.zip"

    def test_finds_vulkan_asset(self):
        """Test that _find_windows_binary_asset finds vulkan asset."""
        assets = [
            {
                "name": "llama-b5000-bin-win-vulkan-x64.zip",
                "browser_download_url": "https://example.com/win-vulkan-x64.zip",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=False)

        assert result is not None
        assert result["name"] == "llama-b5000-bin-win-vulkan-x64.zip"

    def test_finds_noavx_as_fallback(self):
        """Test that _find_windows_binary_asset falls back to noavx."""
        assets = [
            {
                "name": "llama-b5000-bin-win-noavx-x64.zip",
                "browser_download_url": "https://example.com/win-noavx-x64.zip",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=False)

        assert result is not None
        assert result["name"] == "llama-b5000-bin-win-noavx-x64.zip"

    def test_returns_none_when_no_windows_asset(self):
        """Test that _find_windows_binary_asset returns None when no Windows asset."""
        assets = [
            {
                "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
            },
            {
                "name": "llama-b5000-bin-macos-arm64.tar.gz",
                "browser_download_url": "https://example.com/macos-arm64.tar.gz",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=False)

        assert result is None

    def test_returns_none_for_empty_assets(self):
        """Test that _find_windows_binary_asset returns None for empty assets."""
        result = _find_windows_binary_asset([], prefer_cuda=False)
        assert result is None

    def test_ignores_non_zip_files(self):
        """Test that _find_windows_binary_asset ignores non-zip files."""
        assets = [
            {
                "name": "llama-b5000-bin-win-avx2-x64.tar.gz",
                "browser_download_url": "https://example.com/win-avx2-x64.tar.gz",
            },
            {
                "name": "llama-b5000-bin-win-cpu-x64.zip",
                "browser_download_url": "https://example.com/win-cpu-x64.zip",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=False)

        assert result is not None
        assert result["name"] == "llama-b5000-bin-win-cpu-x64.zip"

    def test_priority_cpu_over_avx(self):
        """Test that win-cpu is preferred over win-avx when CUDA not requested."""
        assets = [
            {
                "name": "llama-b5000-bin-win-avx-x64.zip",
                "browser_download_url": "https://example.com/win-avx-x64.zip",
            },
            {
                "name": "llama-b5000-bin-win-cpu-x64.zip",
                "browser_download_url": "https://example.com/win-cpu-x64.zip",
            },
        ]

        result = _find_windows_binary_asset(assets, prefer_cuda=False)

        assert result is not None
        assert result["name"] == "llama-b5000-bin-win-cpu-x64.zip"
