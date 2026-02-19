"""Tests for CLI entry point in llama.py."""

from pathlib import Path
from unittest.mock import patch

import pytest

from aria.scripts.llama import main


class TestMain:
    """Tests for main() function."""

    def test_calls_download_llama_cpp(self):
        """Test that main() calls download_llama_cpp()."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.return_value = None

            main()

            mock_download.assert_called_once_with(
                bin_dir=Path("bin/llamacpp"), version=None
            )

    def test_calls_download_llama_cpp_with_version(self):
        """Test that main() calls download_llama_cpp() with version."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.return_value = None

            main(version="v1.2.3")

            mock_download.assert_called_once_with(
                bin_dir=Path("bin/llamacpp"), version="v1.2.3"
            )

    def test_exits_with_code_0_on_success(self):
        """Test that main() exits with code 0 on success."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.return_value = None

            with patch("sys.exit") as mock_exit:
                main()

                mock_exit.assert_not_called()  # No exit on success

    def test_exits_with_code_1_on_exception(self):
        """Test that main() exits with code 1 on exception."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = Exception("Installation failed")

            with patch("sys.exit") as mock_exit:
                main()

                mock_exit.assert_called_once_with(1)

    def test_prints_error_on_exception(self):
        """Test that main() prints error on exception."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = Exception("Installation failed")

            with patch("aria.scripts.llama.error_console") as mock_error_console:
                with patch("sys.exit"):
                    main()

                    mock_error_console.print.assert_called_once()
                    assert "Installation failed" in str(
                        mock_error_console.print.call_args
                    )

    def test_prints_error_message_on_exception(self):
        """Test that main() prints the exception message."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = ValueError("Invalid version")

            with patch("aria.scripts.llama.error_console") as mock_error_console:
                with patch("sys.exit"):
                    main()

                    mock_error_console.print.assert_called_once()
                    call_args = str(mock_error_console.print.call_args)
                    assert "Invalid version" in call_args

    def test_handles_subprocess_error(self):
        """Test that main() handles subprocess errors."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = subprocess_error = __import__(
                "subprocess"
            ).CalledProcessError(1, "cmd", "Error")

            with patch("aria.scripts.llama.error_console") as mock_error_console:
                with patch("sys.exit") as mock_exit:
                    main()

                    mock_exit.assert_called_once_with(1)

    def test_handles_file_not_found_error(self):
        """Test that main() handles FileNotFoundError."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = FileNotFoundError("Binary not found")

            with patch("aria.scripts.llama.error_console") as mock_error_console:
                with patch("sys.exit") as mock_exit:
                    main()

                    mock_exit.assert_called_once_with(1)

    def test_handles_runtime_error(self):
        """Test that main() handles RuntimeError."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = RuntimeError("Compilation failed")

            with patch("aria.scripts.llama.error_console") as mock_error_console:
                with patch("sys.exit") as mock_exit:
                    main()

                    mock_exit.assert_called_once_with(1)

    def test_handles_keyboard_interrupt(self):
        """Test that main() allows KeyboardInterrupt to propagate."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = KeyboardInterrupt()

            with pytest.raises(KeyboardInterrupt):
                main()

    def test_handles_system_exit(self):
        """Test that main() allows SystemExit to propagate."""
        with patch("aria.scripts.llama.download_llama_cpp") as mock_download:
            mock_download.side_effect = SystemExit(1)

            with pytest.raises(SystemExit):
                main()
