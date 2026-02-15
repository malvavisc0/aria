"""Tests for GitHub API integration functions in llama.py."""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from aria.scripts.llama import (
    _find_linux_binary_asset,
    _get_latest_release_info,
    _get_release_by_tag,
)


class TestGetLatestReleaseInfo:
    """Tests for _get_latest_release_info() function."""

    def test_returns_valid_release_info(self):
        """Test that _get_latest_release_info returns valid release info."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.2.3", "assets": []}'

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
        mock_response.read.return_value = b'{"tag_name": "v1.2.3", "assets": []}'

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
                "browser_download_url": "https://example.com/macos-x64.zip",
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
