"""Llama.cpp management utilities.

This module provides functionality to download and manage llama.cpp binaries
from GitHub releases. It supports downloading the latest version or a specific
version tag.

Example:
    ```python
    from pathlib import Path
    from aria.scripts.llama import download_latest_llama_cpp, get_llama_cpp_binary

    # Download the latest release to bin/llamacpp/
    download_latest_llama_cpp(bin_dir=Path("bin/llamacpp"))

    # Get the path to the llama-cli binary
    binary_path = get_llama_cpp_binary("llama-cli", bin_dir=Path("bin/llamacpp"))
    print(f"Binary location: {binary_path}")
    ```
"""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger
from rich.console import Console

from aria.config import LLAMA_CPP_BIN_DIR
from aria.helpers.nvidia import check_nvidia_smi_available

console = Console()
error_console = Console(stderr=True, style="bold red")

# Binary names to copy to bin/llamacpp/
BINARY_NAMES = [
    "llama-cli",
    "llama-server",
    "llama-bench",
    "llama-quantize",
]

# Shared library patterns to copy
SHARED_LIB_PATTERNS = ["libggml", "libllama", "libmtmd"]


def _download_and_extract_zip(url: str, dest_dir: Path) -> Path:
    """Download and extract a zip file from a URL.

    Args:
        url: URL to download from.
        dest_dir: Directory to extract to.

    Returns:
        Path to the extracted directory (first subdirectory in the zip).
    """
    logger.info(f"Downloading from {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / "download.zip"

        urllib.request.urlretrieve(url, zip_path)

        logger.info("Extracting archive")
        dest_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)

        # Return the first subdirectory (llama.cpp-{tag})
        subdirs = [d for d in dest_dir.iterdir() if d.is_dir()]
        if subdirs:
            return subdirs[0]
        return dest_dir


def _is_linux() -> bool:
    """Check if the current OS is Linux.

    Returns:
        True if running on Linux, False otherwise.
    """
    return platform.system() == "Linux"


def _is_ubuntu() -> bool:
    """Check if the current Linux distribution is Ubuntu.

    Returns:
        True if running on Ubuntu, False otherwise.
    """
    if not _is_linux():
        return False

    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
            return "ubuntu" in content
    except (FileNotFoundError, IOError):
        return False


def _is_cuda_available() -> bool:
    """Check if CUDA is available via nvidia-smi.

    Returns:
        True if nvidia-smi is available and detects GPUs, False otherwise.
    """
    if not _is_linux():
        return False

    return check_nvidia_smi_available()


def _nvcc_available() -> bool:
    """Check if nvcc (CUDA compiler) is available.

    Returns:
        True if nvcc is found and executable, False otherwise.
    """
    try:
        result = subprocess.run(
            ["which", "nvcc"], capture_output=True, text=True, check=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# Binary names to look for in the release
BINARY_NAMES = [
    "llama-cli",
    "llama-server",
    "llama-quantize",
    "llama-bench",
]


def _get_latest_release_info() -> dict:
    """Fetch the latest release information from GitHub API.

    Returns:
        dict: Release information including tag_name and assets.
    """
    api_url = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
    with urllib.request.urlopen(api_url) as response:
        return __import__("json").loads(response.read())


def _get_release_by_tag(tag: str) -> dict:
    """Fetch release information for a specific tag.

    Args:
        tag: The git tag of the release (e.g., "v1.0.0").

    Returns:
        dict: Release information including assets.
    """
    api_url = (
        f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{tag}"
    )
    with urllib.request.urlopen(api_url) as response:
        return __import__("json").loads(response.read())


def _find_linux_binary_asset(assets: list) -> Optional[dict]:
    """Find the appropriate Linux binary asset from the release assets.

    Args:
        assets: List of asset dictionaries from the release.

    Returns:
        The asset dictionary for the Linux binary, or None if not found.
    """
    # Priority order for binary types
    # Updated to match current llama.cpp release naming conventions
    priority = [
        "ubuntu-x64",  # Most common Linux x64 build
        "ubuntu-vulkan",  # Ubuntu with Vulkan support
        "linux-gpu-cuda",
        "linux-gpu",
        "linux-cuda",
        "linux",
    ]

    for prefix in priority:
        for asset in assets:
            name = asset.get("name", "").lower()
            if prefix in name and (
                name.endswith(".tar.gz") or name.endswith(".gz")
            ):
                return asset
    return None


def _download_and_extract(url: str, dest_dir: Path) -> list[str]:
    """Download and extract a tar.gz file.

    Args:
        url: URL to download from.
        dest_dir: Directory to extract to.

    Returns:
        List of extracted file paths.
    """
    extracted_files = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_path = tmp_path / "download.tar.gz"

        logger.info(f"Downloading from {url}")
        urllib.request.urlretrieve(url, archive_path)

        logger.info("Extracting archive")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(dest_dir)
            extracted_files = [
                str(Path(dest_dir) / m.name) for m in tar.getmembers()
            ]

    return extracted_files


def _verify_binary(binary_path: Path) -> bool:
    """Verify that a binary exists and is executable.

    Args:
        binary_path: Path to the binary.

    Returns:
        True if the binary exists and is executable.
    """
    return binary_path.exists() and os.access(binary_path, os.X_OK)


def _make_executable(file_path: Path) -> None:
    """Make a file executable.

    Args:
        file_path: Path to the file.
    """
    os.chmod(file_path, os.stat(file_path).st_mode | 0o111)


def get_llama_cpp_binary(binary_name: str, bin_dir: Path) -> Optional[Path]:
    """Get the path to a llama.cpp binary.

    Args:
        binary_name: Name of the binary (e.g., "llama-cli").
        bin_dir: Directory containing the llama.cpp binaries.

    Returns:
        Path to the binary if found, None otherwise.
    """
    binary_path = bin_dir / binary_name
    if _verify_binary(binary_path):
        return binary_path

    # Also check in subdirectories (for extracted archives)
    for item in bin_dir.rglob(binary_name):
        if _verify_binary(item):
            return item

    return None


def download_latest_llama_cpp(
    bin_dir: Path, version: Optional[str] = None
) -> Path:
    """Download and install the latest llama.cpp binary or compile from source.

    This function implements the following logic:
    - If Ubuntu and no nvcc available: download pre-built binary from GitHub
    - If Linux with nvcc available: compile from source with CUDA support
    - If not Linux: compile from source

    Args:
        bin_dir: Directory to install the binaries to.
        version: Specific version tag to download (e.g., "v1.0.0").
                 If None, downloads the latest release.

    Returns:
        Path to the directory containing the binaries.

    Raises:
        RuntimeError: If download, extraction, or compilation fails.
    """
    logger.info("Starting llama.cpp installation")

    # Ensure bin directory exists
    bin_dir.mkdir(parents=True, exist_ok=True)

    # Determine installation method based on system configuration
    if not _is_linux():
        logger.info("Non-Linux OS detected, compiling from source")
        raise NotImplementedError(
            "Source compilation is required for non-Linux systems. "
            "Please clone the llama.cpp repository and run cmake build manually."
        )

    if _nvcc_available():
        logger.info(
            "CUDA (nvcc) detected, compiling from source with CUDA support"
        )

        # Get release information to get the tag
        if version and version.lower() != "latest":
            logger.info(f"Fetching release info for tag: {version}")
            release = _get_release_by_tag(version)
        else:
            logger.info("Fetching latest release info")
            release = _get_latest_release_info()

        tag = release.get("tag_name", "unknown")
        logger.info(f"Found release: {tag}")

        # Download source from GitHub zip URL
        zip_url = f"https://github.com/ggml-org/llama.cpp/archive/refs/tags/{tag}.zip"

        # Download to /tmp and extract
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_dir = _download_and_extract_zip(
                zip_url, tmp_path / "source"
            )
            logger.info(f"Source extracted to {source_dir}")

            # Compile from source
            build_dir = install_llama_cpp_from_source(
                repo_dir=source_dir,
                build_dir=source_dir / "build",
                use_cuda=True,
                use_blas=True,
                verbose=False,
            )

            # Copy binaries and shared libraries directly to bin_dir
            console.print(
                "[green]✓[/green] Copying binaries and libraries to bin_dir"
            )

            # Copy binaries
            for binary_name in BINARY_NAMES:
                src_binary = build_dir / "bin" / binary_name
                if src_binary.exists():
                    dst_binary = bin_dir / binary_name
                    shutil.copy2(src_binary, dst_binary)
                    _make_executable(dst_binary)
                    logger.info(f"Copied {binary_name} to {bin_dir}")

            # Copy shared libraries
            for lib_pattern in SHARED_LIB_PATTERNS:
                for lib_file in build_dir.glob(f"bin/{lib_pattern}*.so*"):
                    dst_lib = bin_dir / lib_file.name
                    shutil.copy2(lib_file, dst_lib)
                    logger.info(f"Copied {lib_file.name} to {bin_dir}")

            # Test the binary
            test_binary = get_llama_cpp_binary("llama-server", bin_dir)
            if test_binary:
                console.print("[green]✓[/green] Testing binary...")
                try:
                    result = subprocess.run(
                        [str(test_binary), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        console.print(
                            f"  [green]llama-server version: {result.stdout.strip()}[/green]"
                        )
                    else:
                        console.print(
                            f"  [yellow]Warning: Version check failed: {result.stderr}[/yellow]"
                        )
                except subprocess.TimeoutExpired:
                    console.print(
                        "  [yellow]Warning: Version check timed out[/yellow]"
                    )
                except Exception as e:
                    console.print(
                        f"  [yellow]Warning: Could not test binary: {e}[/yellow]"
                    )

            # Cleanup source directory
            console.print("[green]✓[/green] Cleaning up source directory")
            shutil.rmtree(source_dir, ignore_errors=True)

        console.print("[green]✓[/green] llama.cpp installed successfully!")
        console.print(f"  Version: {tag}")
        console.print(f"  Location: {bin_dir}")
        return bin_dir

    if not _is_ubuntu():
        logger.info("Non-Ubuntu Linux detected, compiling from source")

        # Get release information to get the tag
        if version and version.lower() != "latest":
            logger.info(f"Fetching release info for tag: {version}")
            release = _get_release_by_tag(version)
        else:
            logger.info("Fetching latest release info")
            release = _get_latest_release_info()

        tag = release.get("tag_name", "unknown")
        logger.info(f"Found release: {tag}")

        # Download source from GitHub zip URL
        zip_url = f"https://github.com/ggml-org/llama.cpp/archive/refs/tags/{tag}.zip"

        # Download to /tmp and extract
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_dir = _download_and_extract_zip(
                zip_url, tmp_path / "source"
            )
            logger.info(f"Source extracted to {source_dir}")

            # Determine CUDA support based on nvcc availability
            use_cuda = _nvcc_available()
            logger.info(f"Compiling with CUDA support: {use_cuda}")

            # Compile from source
            build_dir = install_llama_cpp_from_source(
                repo_dir=source_dir,
                build_dir=source_dir / "build",
                use_cuda=use_cuda,
                use_blas=False,
                verbose=False,
            )

            # Copy binaries and shared libraries directly to bin_dir
            console.print(
                "[green]✓[/green] Copying binaries and libraries to bin_dir"
            )

            # Copy binaries
            for binary_name in BINARY_NAMES:
                src_binary = build_dir / "bin" / binary_name
                if src_binary.exists():
                    dst_binary = bin_dir / binary_name
                    shutil.copy2(src_binary, dst_binary)
                    _make_executable(dst_binary)
                    logger.info(f"Copied {binary_name} to {bin_dir}")

            # Copy shared libraries
            for lib_pattern in SHARED_LIB_PATTERNS:
                for lib_file in build_dir.glob(f"bin/{lib_pattern}*.so*"):
                    dst_lib = bin_dir / lib_file.name
                    shutil.copy2(lib_file, dst_lib)
                    logger.info(f"Copied {lib_file.name} to {bin_dir}")

            # Test the binary
            test_binary = get_llama_cpp_binary("llama-server", bin_dir)
            if test_binary:
                console.print("[green]✓[/green] Testing binary...")
                try:
                    result = subprocess.run(
                        [str(test_binary), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        console.print(
                            f"  [green]llama-server version: {result.stdout.strip()}[/green]"
                        )
                    else:
                        console.print(
                            f"  [yellow]Warning: Version check failed: {result.stderr}[/yellow]"
                        )
                except subprocess.TimeoutExpired:
                    console.print(
                        "  [yellow]Warning: Version check timed out[/yellow]"
                    )
                except Exception as e:
                    console.print(
                        f"  [yellow]Warning: Could not test binary: {e}[/yellow]"
                    )

            # Cleanup source directory
            console.print("[green]✓[/green] Cleaning up source directory")
            shutil.rmtree(source_dir, ignore_errors=True)

        console.print("[green]✓[/green] llama.cpp installed successfully!")
        console.print(f"  Version: {tag}")
        console.print(f"  Location: {bin_dir}")
        return bin_dir

    # Ubuntu with no nvcc - download pre-built binary
    logger.info("Ubuntu detected with no CUDA, downloading pre-built binary")

    try:
        # Get release information
        if version and version.lower() != "latest":
            logger.info(f"Fetching release info for tag: {version}")
            release = _get_release_by_tag(version)
        else:
            logger.info("Fetching latest release info")
            release = _get_latest_release_info()

        tag = release.get("tag_name", "unknown")
        logger.info(f"Found release: {tag}")

        # Find Linux binary asset
        assets = release.get("assets", [])
        binary_asset = _find_linux_binary_asset(assets)

        if not binary_asset:
            error_console.print(
                "[red]Error: No suitable Linux binary found in release[/red]"
            )
            error_console.print("Available assets:")
            for asset in assets:
                error_console.print(f"  - {asset.get('name', 'unknown')}")
            raise RuntimeError("No suitable Linux binary found")

        download_url = binary_asset.get("browser_download_url")
        if not download_url:
            raise RuntimeError("Could not find download URL for binary asset")

        # Download and extract
        extracted = _download_and_extract(download_url, bin_dir)
        logger.info(f"Extracted {len(extracted)} files")

        # Make binaries executable
        for binary_name in BINARY_NAMES:
            binary_path = get_llama_cpp_binary(binary_name, bin_dir)
            if binary_path:
                _make_executable(binary_path)
                logger.info(f"Made {binary_name} executable")

        # Print success message
        console.print("[green]✓[/green] llama.cpp installed successfully!")
        console.print(f"  Version: {tag}")
        console.print(f"  Location: {bin_dir}")

        # List installed binaries
        console.print("\nInstalled binaries:")
        for binary_name in BINARY_NAMES:
            binary_path = get_llama_cpp_binary(binary_name, bin_dir)
            if binary_path:
                console.print(
                    f"  - [green]{binary_name}[/green]: {binary_path}"
                )

        return bin_dir

    except urllib.error.URLError as e:
        error_console.print(f"[red]Network error: {e}[/red]")
        raise
    except Exception as e:
        error_console.print(f"[red]Error: {e}[/red]")
        raise


def install_llama_cpp_from_source(
    repo_dir: Path,
    build_dir: Optional[Path] = None,
    use_cuda: bool = True,
    use_blas: bool = False,
    verbose: bool = False,
) -> Path:
    """Install llama.cpp from source (fallback method).

    This method compiles llama.cpp from source using CMake. It's more time-consuming
    than downloading pre-built binaries but allows for custom compilation flags.

    Args:
        repo_dir: Directory containing the llama.cpp source code.
        build_dir: Build directory (defaults to repo_dir/build).
        use_cuda: Enable CUDA compilation.
        use_blas: Enable OpenBLAS compilation.
        verbose: Enable verbose output.

    Returns:
        Path to the build directory containing binaries.

    Raises:
        RuntimeError: If compilation fails.
    """
    if build_dir is None:
        build_dir = repo_dir / "build"

    logger.info("Compiling llama.cpp from source")

    # Check dependencies
    dependencies = ["git", "cmake", "make"]
    for dep in dependencies:
        result = subprocess.run(["which", dep], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Required dependency '{dep}' not found")

    try:
        # Clean build directory
        if build_dir.exists():
            logger.info("Cleaning existing build directory")
            shutil.rmtree(build_dir)

        build_dir.mkdir(parents=True, exist_ok=True)

        # Configure with CMake
        cmake_args = [
            "cmake",
            "-B",
            str(build_dir),
            "-S",
            str(repo_dir),
        ]

        if use_cuda:
            cmake_args.append("-DGGML_CUDA=ON")

        if use_blas:
            cmake_args.extend(
                [
                    "-DGGML_BLAS=ON",
                    "-DGGML_BLAS_VENDOR=OpenBLAS",
                ]
            )

        if verbose:
            cmake_args.append("-DCMAKE_VERBOSE_MAKEFILE=ON")

        logger.info(f"Running: {' '.join(cmake_args)}")
        result = subprocess.run(
            cmake_args,
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("CMake configuration failed")

        # Build
        threads = os.cpu_count() or 1
        build_args = [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            "Release",
            "-j",
            str(threads),
        ]

        logger.info(f"Running: {' '.join(build_args)}")
        result = subprocess.run(
            build_args,
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error_console.print("[red]Compilation failed![/red]")
            if result.stderr:
                error_console.print(
                    f"[red]Error output:[/red]\n{result.stderr}"
                )
            if result.stdout:
                error_console.print(f"[red]Stdout:[/red]\n{result.stdout}")
            raise RuntimeError("Compilation failed")

        console.print("[green]✓[/green] llama.cpp compiled successfully!")
        console.print(f"  Location: {build_dir}")

        return build_dir

    except subprocess.CalledProcessError as e:
        error_console.print(f"[red]Command failed: {e}[/red]")
        raise
    except Exception as e:
        error_console.print(f"[red]Error: {e}[/red]")
        raise


def main(
    bin_dir: Path = Path("bin/llamacpp"), version: Optional[str] = None
) -> None:
    """CLI entry point for llama.cpp installation.

    Args:
        bin_dir: Directory to install the binaries to.
        version: Optional version tag to install.
    """
    try:
        download_latest_llama_cpp(bin_dir=bin_dir, version=version)
    except Exception as e:
        error_console.print(f"[red]Installation failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
