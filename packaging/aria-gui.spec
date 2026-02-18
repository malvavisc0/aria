# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for the Aria GUI standalone build.
#
# Entry point: aria.gui:main  (PySide6 Qt window)
#
# Usage (from project root):
#   uv run pyinstaller packaging/aria-gui.spec
#
# Output:
#   dist/aria-gui/          ← one-folder bundle (Linux / Windows / macOS)
#
# To build an AppImage from the output (Linux only):
#   ./packaging/build-appimage.sh
#
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Project root (one level above this spec file) ────────────────────────────
ROOT = Path(SPECPATH).parent

# ── Collect Chainlit's React frontend and translation assets ──────────────────
# Chainlit serves a built React app from its own package directory.
# Without these files the web UI will be a blank page.
chainlit_datas = collect_data_files(
    "chainlit",
    includes=["frontend/**/*", "translations/**/*", "data/**/*", "copilot/**/*"],
)

# ── Collect ChromaDB's native data (ONNX models, etc.) ───────────────────────
chromadb_datas = collect_data_files("chromadb")

# ── Hidden imports ────────────────────────────────────────────────────────────
# Packages that are imported dynamically (via importlib, plugins, etc.) and
# that PyInstaller's static analysis would otherwise miss.
hidden_imports = [
    # Chainlit internals loaded at runtime
    *collect_submodules("chainlit"),
    # LlamaIndex extensions
    *collect_submodules("llama_index"),
    # ChromaDB backends
    *collect_submodules("chromadb"),
    # SQLAlchemy dialects
    "sqlalchemy.dialects.sqlite",
    # Aria packages
    "aria",
    "aria.gui",
    "aria.gui.main_window",
    "aria.gui.dialogs",
    "aria.gui.ui",
    "aria.cli",
    "aria.config",
    "aria.db",
    "aria.server",
    "aria.agents",
    "aria.tools",
    "aria.helpers",
    "aria.scripts",
]

# ── Application data files ────────────────────────────────────────────────────
app_datas = [
    # Aria's own public assets (Chainlit CSS, theme, logos, avatars)
    (str(ROOT / "public"), "aria/public"),
    # Chainlit welcome page
    (str(ROOT / "chainlit.md"), "aria/chainlit.md"),
    # Default configuration template (copied to cwd on first run)
    (str(ROOT / "src" / "aria" / ".env.example"), "aria/.env.example"),
    # Agent and tool system prompt files
    (str(ROOT / "src" / "aria" / "agents" / "instructions"), "aria/agents/instructions"),
    (str(ROOT / "src" / "aria" / "tools" / "instructions"), "aria/tools/instructions"),
    # Chainlit assets
    *chainlit_datas,
    # ChromaDB assets
    *chromadb_datas,
]

# ── GUI entry point script ────────────────────────────────────────────────────
# We use a tiny bootstrap script so PyInstaller has a plain .py file to
# analyse, rather than pointing at the package __init__.py directly.
# The bootstrap is generated inline below.
BOOTSTRAP = ROOT / "packaging" / "_gui_bootstrap.py"
BOOTSTRAP.write_text(
    "from aria.gui import main\n"
    "if __name__ == '__main__':\n"
    "    main()\n"
)

# ─────────────────────────────────────────────────────────────────────────────

a = Analysis(
    [str(BOOTSTRAP)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=app_datas,
    hiddenimports=hidden_imports,
    hookspath=[str(ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test frameworks from the bundle
        "pytest",
        "pytest_asyncio",
        "pytest_cov",
        "_pytest",
        # Exclude build tools
        "pyinstaller",
        "black",
        "flake8",
        "isort",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="aria-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # console=True keeps a terminal window open alongside the Qt window.
    # Set to False on Windows if you want a pure GUI app with no console.
    console=False,
    icon=str(ROOT / "public" / "favicon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="aria-gui",
)
