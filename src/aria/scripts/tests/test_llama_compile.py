"""Tests for compilation functions in llama.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aria.scripts.llama import install_llama_cpp_from_source


class TestInstallLlamaCppFromSource:
    """Tests for install_llama_cpp_from_source() function."""

    def test_compiles_successfully(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source compiles successfully."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            # Mock dependency checks (git, cmake, make)
            dep_check_result = Mock()
            dep_check_result.returncode = 0
            dep_check_result.stdout = ""

            # Mock successful cmake configuration
            cmake_config_result = Mock()
            cmake_config_result.returncode = 0
            cmake_config_result.stdout = ""

            # Mock successful cmake build
            cmake_build_result = Mock()
            cmake_build_result.returncode = 0
            cmake_build_result.stdout = ""

            mock_run.side_effect = [
                dep_check_result,  # git check
                dep_check_result,  # cmake check
                dep_check_result,  # make check
                cmake_config_result,
                cmake_build_result,
            ]

            result = install_llama_cpp_from_source(
                repo_dir=repo_dir,
                build_dir=build_dir,
                use_cuda=True,
                use_blas=True,
                verbose=False,
            )

            assert result == build_dir
            assert build_dir.exists()

    def test_creates_build_directory(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source creates build directory."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir
            )

            assert build_dir.exists()

    def test_cleans_existing_build_directory(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source cleans existing build directory."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "old_file.txt").write_text("old content")

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir
            )

            # Old file should be gone after clean
            assert not (build_dir / "old_file.txt").exists()

    def test_runs_cmake_configuration(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source runs cmake configuration."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir
            )

            # Check that cmake was called with correct arguments
            # Skip the first 3 calls which are dependency checks (git, cmake, make)
            assert mock_run.call_count >= 4
            cmake_call = mock_run.call_args_list[3]  # 4th call is cmake config
            assert "cmake" in cmake_call[0][0]
            assert "-B" in cmake_call[0][0]
            assert "-S" in cmake_call[0][0]

    def test_runs_cmake_build(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source runs cmake build."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir
            )

            # Check that cmake build was called
            build_calls = [
                call
                for call in mock_run.call_args_list
                if "--build" in call[0][0]
            ]
            assert len(build_calls) >= 1

    def test_enables_cuda_when_use_cuda_true(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source enables CUDA when use_cuda=True."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir, use_cuda=True
            )

            # Check that -DGGML_CUDA=ON was passed
            cmake_args = [
                call[0][0]
                for call in mock_run.call_args_list
                if "cmake" in call[0][0] and "-B" in call[0][0]
            ]
            assert any("-DGGML_CUDA=ON" in args for args in cmake_args[0])

    def test_disables_cuda_when_use_cuda_false(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source disables CUDA when use_cuda=False."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir, use_cuda=False
            )

            # Check that -DGGML_CUDA=ON was NOT passed
            cmake_args = [
                call[0][0]
                for call in mock_run.call_args_list
                if "cmake" in call[0][0] and "-B" in call[0][0]
            ]
            assert not any("-DGGML_CUDA=ON" in args for args in cmake_args[0])

    def test_enables_blas_when_use_blas_true(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source enables BLAS when use_blas=True."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir, use_blas=True
            )

            # Check that -DGGML_BLAS=ON was passed
            cmake_args = [
                call[0][0]
                for call in mock_run.call_args_list
                if "cmake" in call[0][0] and "-B" in call[0][0]
            ]
            assert any("-DGGML_BLAS=ON" in args for args in cmake_args[0])

    def test_disables_blas_when_use_blas_false(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source disables BLAS when use_blas=False."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir, use_blas=False
            )

            # Check that -DGGML_BLAS=ON was NOT passed
            cmake_args = [
                call[0][0]
                for call in mock_run.call_args_list
                if "cmake" in call[0][0] and "-B" in call[0][0]
            ]
            assert not any("-DGGML_BLAS=ON" in args for args in cmake_args[0])

    def test_enables_verbose_when_verbose_true(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source enables verbose when verbose=True."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(
                repo_dir=repo_dir, build_dir=build_dir, verbose=True
            )

            # Check that -DCMAKE_VERBOSE_MAKEFILE=ON was passed
            cmake_args = [
                call[0][0]
                for call in mock_run.call_args_list
                if "cmake" in call[0][0] and "-B" in call[0][0]
            ]
            assert any(
                "-DCMAKE_VERBOSE_MAKEFILE=ON" in args for args in cmake_args[0]
            )

    def test_uses_default_build_dir(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source uses default build directory."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = repo_dir / "build"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            install_llama_cpp_from_source(repo_dir=repo_dir)

            assert build_dir.exists()

    def test_raises_error_on_missing_dependency(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source raises error on missing dependency."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            # Mock 'which' command to fail for git
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            with pytest.raises(RuntimeError) as exc_info:
                install_llama_cpp_from_source(
                    repo_dir=repo_dir, build_dir=build_dir
                )

            assert "Required dependency" in str(exc_info.value)
            assert "not found" in str(exc_info.value)

    def test_raises_error_on_cmake_configuration_failure(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source raises error on cmake configuration failure."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            # Mock dependency checks to succeed
            dep_check_result = Mock()
            dep_check_result.returncode = 0
            dep_check_result.stdout = ""

            # Mock cmake configuration to fail
            cmake_fail_result = Mock()
            cmake_fail_result.returncode = 1
            cmake_fail_result.stdout = ""
            cmake_fail_result.stderr = "CMake error: invalid configuration"

            mock_run.side_effect = [
                dep_check_result,  # git check
                dep_check_result,  # cmake check
                dep_check_result,  # make check
                cmake_fail_result,  # cmake config fails
            ]

            with pytest.raises(RuntimeError) as exc_info:
                install_llama_cpp_from_source(
                    repo_dir=repo_dir, build_dir=build_dir
                )

            assert "CMake configuration failed" in str(exc_info.value)

    def test_raises_error_on_compilation_failure(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source raises error on compilation failure."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            # Mock dependency checks to succeed
            dep_check_result = Mock()
            dep_check_result.returncode = 0
            dep_check_result.stdout = ""

            # Mock cmake configuration to succeed
            cmake_config_result = Mock()
            cmake_config_result.returncode = 0
            cmake_config_result.stdout = ""

            # Mock cmake build to fail
            cmake_build_result = Mock()
            cmake_build_result.returncode = 1
            cmake_build_result.stdout = "Build output"
            cmake_build_result.stderr = "Compilation error"

            mock_run.side_effect = [
                dep_check_result,  # git check
                dep_check_result,  # cmake check
                dep_check_result,  # make check
                cmake_config_result,
                cmake_build_result,
            ]

            with pytest.raises(RuntimeError) as exc_info:
                install_llama_cpp_from_source(
                    repo_dir=repo_dir, build_dir=build_dir
                )

            assert "Compilation failed" in str(exc_info.value)

    def test_raises_error_on_subprocess_called_process_error(
        self, tmp_path: Path
    ):
        """Test that install_llama_cpp_from_source raises error on subprocess.CalledProcessError."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "cmake", "Error"
            )

            with pytest.raises(subprocess.CalledProcessError):
                install_llama_cpp_from_source(
                    repo_dir=repo_dir, build_dir=build_dir
                )

    def test_raises_error_on_other_exception(self, tmp_path: Path):
        """Test that install_llama_cpp_from_source raises error on other exceptions."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        build_dir = tmp_path / "build"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception) as exc_info:
                install_llama_cpp_from_source(
                    repo_dir=repo_dir, build_dir=build_dir
                )

            assert "Unexpected error" in str(exc_info.value)
