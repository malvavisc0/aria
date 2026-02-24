"""Llama.cpp management utilities.

This module provides functionality to download and manage llama.cpp binaries
from GitHub releases. It supports downloading the latest version or a specific
version tag.

Example:
    ```python
    from pathlib import Path
    from aria.scripts.llama import download_llama_cpp, get_llama_cpp_binary

    # Download the latest release to bin/llamacpp/
    download_llama_cpp(bin_dir=Path("bin/llamacpp"))

    # Get the path to the llama-cli binary
    binary_path = get_llama_cpp_binary("llama-cli", bin_dir=Path("bin/llamacpp"))
    print(f"Binary location: {binary_path}")
    ```
"""

import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console(width=200)
error_console = Console(stderr=True, style="bold red", width=200)

# Binary names to copy to bin/llamacpp/
BINARY_NAMES = [
    "llama-cli",
    "llama-server",
    "llama-bench",
    "llama-quantize",
]

# Shared library patterns to copy
SHARED_LIB_PATTERNS = ["libggml", "libllama", "libmtmd"]


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
    """Check if CUDA is available via nvcc.

    NVCC is the CUDA compiler and is the definitive way to check if
    CUDA toolkit is installed. This works on both Linux and Windows.

    Returns:
        True if nvcc is found and executable, False otherwise.
    """
    return _nvcc_available()


def _nvcc_available() -> bool:
    """Check if nvcc (CUDA compiler) is available.

    Uses shutil.which for cross-platform compatibility (works on both
    Linux and Windows).

    Returns:
        True if nvcc is found in PATH, False otherwise.
    """
    import shutil

    return shutil.which("nvcc") is not None


def _is_openblas_available() -> bool:
    """Check if OpenBLAS development libraries are installed.

    Probes the system using multiple methods in priority order so that
    the check works on both Linux and macOS (Homebrew):

    1. ``pkg-config --exists openblas`` — most reliable when pkg-config is
       present (common on Linux distros and macOS with Homebrew).
    2. Known header file locations — covers systems without pkg-config.
    3. ``ldconfig -p | grep libopenblas`` — Linux-only shared-library cache.

    Returns:
        True if OpenBLAS development files appear to be installed,
        False otherwise.
    """
    # 1. pkg-config (cross-platform)
    try:
        result = subprocess.run(
            ["pkg-config", "--exists", "openblas"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 2. Header file presence (Linux and macOS Homebrew paths)
    header_paths = [
        # Linux
        Path("/usr/include/openblas/cblas.h"),
        Path("/usr/include/cblas.h"),
        Path("/usr/local/include/openblas/cblas.h"),
        # macOS Homebrew (Apple Silicon)
        Path("/opt/homebrew/opt/openblas/include/cblas.h"),
        # macOS Homebrew (Intel)
        Path("/usr/local/opt/openblas/include/cblas.h"),
    ]
    if any(p.exists() for p in header_paths):
        return True

    # 3. ldconfig shared-library cache (Linux only)
    try:
        result = subprocess.run(
            ["ldconfig", "-p"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "libopenblas" in result.stdout:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return False


def _get_latest_release_info() -> dict:
    """Fetch the latest release information from GitHub API.

    Returns:
        dict: Release information including tag_name and assets.
    """
    api_url = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
    with urllib.request.urlopen(api_url, timeout=30) as response:
        return __import__("json").loads(response.read())


def _get_release_by_tag(tag: str) -> dict:
    """Fetch release information for a specific tag.

    Args:
        tag: The git tag of the release (e.g., "b4500").

    Returns:
        dict: Release information including assets.
    """
    api_url = (
        f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{tag}"
    )
    with urllib.request.urlopen(api_url, timeout=30) as response:
        return __import__("json").loads(response.read())


def _find_linux_binary_asset(
    assets: list, prefer_cuda: bool = False
) -> Optional[dict]:
    """Find the appropriate Linux binary asset from the release assets.

    Searches for pre-built Linux binary archives in priority order.
    Matches current llama.cpp release naming conventions (e.g. b5000+):
      llama-{tag}-bin-ubuntu-x64.tar.gz
      llama-{tag}-bin-ubuntu-cuda-cu12.4.1-x64.tar.gz
      llama-{tag}-bin-linux-x64.tar.gz

    Args:
        assets: List of asset dictionaries from the release.
        prefer_cuda: If True, prefer CUDA builds over CPU builds.

    Returns:
        The asset dictionary for the Linux binary, or None if not found.
    """
    # Priority order depends on CUDA preference
    if prefer_cuda:
        priority = [
            "ubuntu-cuda",  # Ubuntu CUDA (best for CUDA systems)
            "linux-gpu-cuda",  # Generic Linux CUDA
            "linux-cuda",  # Generic Linux CUDA (alt naming)
            "ubuntu-vulkan",  # Ubuntu with Vulkan
            "ubuntu-x64",  # Ubuntu CPU x64 (fallback)
            "linux-gpu",  # Generic Linux GPU (fallback)
            "linux-x64",  # Generic Linux CPU x64 (fallback)
            "ubuntu",  # Any Ubuntu build
            "linux",  # Any Linux build
        ]
    else:
        priority = [
            "ubuntu-x64",  # Ubuntu CPU x64 (most common)
            "ubuntu-vulkan",  # Ubuntu with Vulkan
            "linux-x64",  # Generic Linux CPU x64
            "ubuntu",  # Any Ubuntu build
            "linux",  # Any Linux build
            "linux-gpu-cuda",  # Generic Linux CUDA (fallback)
            "linux-gpu",  # Generic Linux GPU (fallback)
            "linux-cuda",  # Generic Linux CUDA (alt naming)
        ]

    def _is_binary_archive(name: str) -> bool:
        return (
            name.endswith(".tar.gz") or name.endswith(".gz")
        ) and "src" not in name.lower()

    for keyword in priority:
        for asset in assets:
            name = asset.get("name", "").lower()
            if keyword in name and _is_binary_archive(name):
                return asset

    return None


def _download_with_progress(
    url: str, dest_path: Path, description: str = "Downloading"
) -> None:
    """Download a file from a URL with a Rich progress bar.

    Args:
        url: URL to download from.
        dest_path: Local path to save the file to.
        description: Label shown in the progress bar.
    """
    import sys

    in_tty = sys.stdout.isatty()
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]{description}[/bold cyan]"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
        disable=not in_tty,
    ) as progress:
        task = progress.add_task(description, total=None)

        def _reporthook(
            block_num: int, block_size: int, total_size: int
        ) -> None:
            if total_size > 0 and progress.tasks[task].total is None:
                progress.update(task, total=total_size)
            progress.update(task, completed=block_num * block_size)

        urllib.request.urlretrieve(url, dest_path, reporthook=_reporthook)


def _download_and_extract(
    url: str, dest_dir: Path, description: str = "Downloading"
) -> list[str]:
    """Download and extract a tar.gz file with progress display.

    Args:
        url: URL to download from.
        dest_dir: Directory to extract to.
        description: Label shown in the progress bar.

    Returns:
        List of extracted file paths.
    """
    extracted_files = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_path = tmp_path / "download.tar.gz"

        _download_with_progress(url, archive_path, description)

        console.print("[cyan]  Extracting archive...[/cyan]")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(dest_dir)
            extracted_files = [
                str(Path(dest_dir) / m.name) for m in tar.getmembers()
            ]

    return extracted_files


def _download_and_extract_zip(
    url: str, dest_dir: Path, description: str = "Downloading source"
) -> Path:
    """Download and extract a zip file from a URL with progress display.

    Args:
        url: URL to download from.
        dest_dir: Directory to extract to.
        description: Label shown in the progress bar.

    Returns:
        Path to the extracted directory (first subdirectory in the zip).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / "download.zip"

        _download_with_progress(url, zip_path, description)

        console.print("[cyan]  Extracting source archive...[/cyan]")
        dest_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)

        # Return the first subdirectory (llama.cpp-{tag})
        subdirs = [d for d in dest_dir.iterdir() if d.is_dir()]
        if subdirs:
            return subdirs[0]
        return dest_dir


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


def _copy_binaries_and_libs(build_bin_dir: Path, dest_dir: Path) -> None:
    """Copy compiled binaries and shared libraries to the destination directory.

    Args:
        build_bin_dir: The build output bin/ directory.
        dest_dir: The destination directory.
    """
    for binary_name in BINARY_NAMES:
        src_binary = build_bin_dir / binary_name
        if src_binary.exists():
            dst_binary = dest_dir / binary_name
            shutil.copy2(src_binary, dst_binary)
            _make_executable(dst_binary)
            logger.info(f"Copied {binary_name} to {dest_dir}")

    for lib_pattern in SHARED_LIB_PATTERNS:
        for lib_file in build_bin_dir.glob(f"{lib_pattern}*.so*"):
            dst_lib = dest_dir / lib_file.name
            shutil.copy2(lib_file, dst_lib)
            logger.info(f"Copied {lib_file.name} to {dest_dir}")


def _test_binary(bin_dir: Path) -> None:
    """Test the installed llama-server binary.

    Args:
        bin_dir: Directory containing the binaries.
    """
    test_binary = get_llama_cpp_binary("llama-server", bin_dir)
    if test_binary:
        console.print("[cyan]  Testing binary...[/cyan]")
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


def download_llama_cpp(bin_dir: Path, version: Optional[str] = None) -> Path:
    """Download and install llama.cpp binaries.

    Installation strategy:
    - If ``nvcc`` is available: compile from source with CUDA support (produces
      a CUDA-enabled binary optimised for the local GPU architecture)
    - Otherwise on Ubuntu: download the pre-built Ubuntu binary from GitHub releases
    - Otherwise on other Linux: compile from source without CUDA

    Note: Compilation can take 10-30 minutes. Progress is streamed to the console.

    Args:
        bin_dir: Directory to install the binaries to.
        version: Specific version tag to download (e.g., "b4500").
                 If None, downloads/compiles the latest release.

    Returns:
        Path to the directory containing the binaries.

    Raises:
        RuntimeError: If download, extraction, or compilation fails.
        NotImplementedError: If running on a non-Linux OS.
    """
    logger.info("Starting llama.cpp installation")

    # Ensure bin directory exists
    bin_dir.mkdir(parents=True, exist_ok=True)

    if not _is_linux():
        raise NotImplementedError(
            "Source compilation is required for non-Linux systems. "
            "Please clone the llama.cpp repository and run cmake build manually."
        )

    # Fetch release information (needed for both download and source paths)
    try:
        if version and version.lower() != "latest":
            console.print(
                f"[cyan]  Fetching release info for tag: {version}[/cyan]"
            )
            release = _get_release_by_tag(version)
        else:
            console.print(
                "[cyan]  Fetching latest release info from GitHub...[/cyan]"
            )
            release = _get_latest_release_info()
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Failed to fetch release info from GitHub: {e}"
        ) from e

    tag = release.get("tag_name", "unknown")
    console.print(f"[green]  Found release: {tag}[/green]")

    # --- Path 1: nvcc available → compile from source with CUDA ---
    if _nvcc_available():
        console.print(
            "[cyan]  nvcc detected — compiling from source with CUDA support[/cyan]"
        )
        console.print(
            "[yellow]  This may take 10-30 minutes. Output is shown below.[/yellow]"
        )

        zip_url = f"https://github.com/ggml-org/llama.cpp/archive/refs/tags/{tag}.zip"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_dir = _download_and_extract_zip(
                zip_url,
                tmp_path / "source",
                description=f"Downloading source {tag}",
            )
            logger.info(f"Source extracted to {source_dir}")

            blas_available = _is_openblas_available()
            if blas_available:
                console.print(
                    "[cyan]  OpenBLAS detected — enabling BLAS support[/cyan]"
                )
            build_dir = install_llama_cpp_from_source(
                repo_dir=source_dir,
                build_dir=source_dir / "build",
                use_cuda=True,
                use_blas=blas_available,
                verbose=True,
            )

            _copy_binaries_and_libs(build_dir / "bin", bin_dir)
            _test_binary(bin_dir)

            console.print("[green]✓[/green] Cleaning up source directory")
            shutil.rmtree(source_dir, ignore_errors=True)

        console.print("[green]✓[/green] llama.cpp installed successfully!")
        console.print(f"  Version: {tag}")
        console.print(f"  Location: {bin_dir}")
        return bin_dir

    # --- Path 2: Ubuntu without nvcc → download pre-built binary ---
    if _is_ubuntu():
        console.print(
            "[cyan]  Ubuntu detected — downloading pre-built binary[/cyan]"
        )

        assets = release.get("assets", [])
        # Check if CUDA is available for binary selection preference
        cuda_available = _is_cuda_available()
        binary_asset = _find_linux_binary_asset(
            assets, prefer_cuda=cuda_available
        )

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
            raise RuntimeError(
                f"Could not find download URL for binary asset: {binary_asset.get('name')}"
            )

        asset_name = binary_asset.get("name", "unknown")
        console.print(f"[cyan]  Downloading: {asset_name}[/cyan]")

        try:
            with tempfile.TemporaryDirectory() as extract_tmp:
                extract_tmp_path = Path(extract_tmp)
                extracted = _download_and_extract(
                    download_url,
                    extract_tmp_path,
                    description=f"Downloading {asset_name}",
                )
                logger.info(f"Extracted {len(extracted)} files")

                # Flatten: copy binaries and shared libs directly into bin_dir
                # (the tar.gz contains a top-level dir like llama-b8089/)
                console.print("[cyan]  Installing binaries...[/cyan]")
                for binary_name in BINARY_NAMES:
                    binary_path = get_llama_cpp_binary(
                        binary_name, extract_tmp_path
                    )
                    if binary_path:
                        dst = bin_dir / binary_name
                        shutil.copy2(binary_path, dst)
                        _make_executable(dst)
                        logger.info(f"Installed {binary_name} to {bin_dir}")

                # Copy shared libraries
                for lib_pattern in SHARED_LIB_PATTERNS:
                    for lib_file in extract_tmp_path.rglob(
                        f"{lib_pattern}*.so*"
                    ):
                        dst_lib = bin_dir / lib_file.name
                        shutil.copy2(lib_file, dst_lib)
                        logger.info(f"Installed {lib_file.name} to {bin_dir}")

        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to download binary: {e}") from e

        _test_binary(bin_dir)

        console.print("[green]✓[/green] llama.cpp installed successfully!")
        console.print(f"  Version: {tag}")
        console.print(f"  Location: {bin_dir}")

        console.print("\nInstalled binaries:")
        for binary_name in BINARY_NAMES:
            binary_path = get_llama_cpp_binary(binary_name, bin_dir)
            if binary_path:
                console.print(
                    f"  - [green]{binary_name}[/green]: {binary_path}"
                )

        return bin_dir

    # --- Path 3: Non-Ubuntu Linux without nvcc → compile from source (CPU only) ---
    console.print(
        "[cyan]  Non-Ubuntu Linux without nvcc — compiling from source (CPU only)[/cyan]"
    )
    console.print(
        "[yellow]  This may take 10-30 minutes. Output is shown below.[/yellow]"
    )

    zip_url = (
        f"https://github.com/ggml-org/llama.cpp/archive/refs/tags/{tag}.zip"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        source_dir = _download_and_extract_zip(
            zip_url,
            tmp_path / "source",
            description=f"Downloading source {tag}",
        )
        logger.info(f"Source extracted to {source_dir}")

        build_dir = install_llama_cpp_from_source(
            repo_dir=source_dir,
            build_dir=source_dir / "build",
            use_cuda=False,
            use_blas=False,
            verbose=True,
        )

        _copy_binaries_and_libs(build_dir / "bin", bin_dir)
        _test_binary(bin_dir)

        console.print("[green]✓[/green] Cleaning up source directory")
        shutil.rmtree(source_dir, ignore_errors=True)

    console.print("[green]✓[/green] llama.cpp installed successfully!")
    console.print(f"  Version: {tag}")
    console.print(f"  Location: {bin_dir}")
    return bin_dir


def install_llama_cpp_from_source(
    repo_dir: Path,
    build_dir: Optional[Path] = None,
    use_cuda: bool = True,
    use_blas: bool = False,
    verbose: bool = True,
) -> Path:
    """Install llama.cpp from source.

    Compiles llama.cpp from source using CMake. Used when nvcc is available
    (CUDA build) or when running on non-Ubuntu Linux without nvcc (CPU build).

    Note: Compilation can take 10-30 minutes depending on hardware.

    Args:
        repo_dir: Directory containing the llama.cpp source code.
        build_dir: Build directory (defaults to repo_dir/build).
        use_cuda: Enable CUDA compilation (requires nvcc).
        use_blas: Enable OpenBLAS compilation.
        verbose: Stream cmake/make output to the console (default True).

    Returns:
        Path to the build directory containing binaries.

    Raises:
        RuntimeError: If compilation fails.
    """
    if build_dir is None:
        build_dir = repo_dir / "build"

    logger.info("Compiling llama.cpp from source")

    # Check dependencies
    dependencies = ["cmake", "make"]
    for dep in dependencies:
        result = subprocess.run(["which", dep], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Required dependency '{dep}' not found. "
                f"Install it with your package manager "
                f"(e.g. 'pacman -S cmake make' on Arch, 'apt install cmake make' on Debian)."
            )

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
            "-DCMAKE_BUILD_TYPE=Release",
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

        console.print(
            f"[cyan]  cmake configure: {' '.join(cmake_args)}[/cyan]"
        )

        if verbose:
            subprocess.run(cmake_args, cwd=str(repo_dir), check=True)
        else:
            subprocess.run(
                cmake_args,
                cwd=str(repo_dir),
                check=True,
                capture_output=True,
                text=True,
            )

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

        console.print(
            f"[cyan]  cmake build ({threads} parallel jobs)...[/cyan]"
        )

        if verbose:
            subprocess.run(build_args, cwd=str(repo_dir), check=True)
        else:
            result = subprocess.run(
                build_args,
                cwd=str(repo_dir),
                check=True,
                capture_output=True,
                text=True,
            )

        console.print("[green]✓[/green] llama.cpp compiled successfully!")
        console.print(f"  Location: {build_dir}")

        return build_dir

    except subprocess.CalledProcessError as e:
        error_console.print(f"[red]Command failed: {e}[/red]")
        raise RuntimeError(f"Compilation failed: {e}") from e
    except Exception as e:
        error_console.print(f"[red]Error: {e}[/red]")
        raise
