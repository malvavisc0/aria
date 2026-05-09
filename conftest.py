"""Pytest configuration and fixtures for aria tests."""

import atexit
import importlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Global test sandbox
#
# This MUST happen before any project module import so import-time path
# constants never resolve to the real ~/.aria tree.
# ---------------------------------------------------------------------------

_SESSION_SANDBOX = Path(tempfile.mkdtemp(prefix="aria-pytest-"))
_SESSION_ARIA_HOME = _SESSION_SANDBOX / "aria_home"
_SESSION_WORKSPACE = _SESSION_ARIA_HOME / "workspace"
_SESSION_ARIA_HOME.mkdir(parents=True, exist_ok=True)
_SESSION_WORKSPACE.mkdir(parents=True, exist_ok=True)

os.environ["ARIA_HOME"] = str(_SESSION_ARIA_HOME)
os.environ["TOOLS_DATA_FOLDER"] = str(_SESSION_WORKSPACE)


@atexit.register
def _cleanup_session_sandbox() -> None:
    shutil.rmtree(_SESSION_SANDBOX, ignore_errors=True)


# Load environment variables from .env file, but keep the sandbox overrides.
load_dotenv()

# Modules containing a DOWNLOADS_DIR binding that must be redirected in tests.
_DOWNLOADS_DIR_MODULES = (
    "aria.tools.constants",
    "aria.tools.search.constants",
    "aria.tools.search.download",
    "aria.tools.search.youtube",
)


@pytest.fixture(autouse=True)
def _isolate_data_dirs(tmp_path, monkeypatch):
    """Redirect all data directories to tmp_path so tests never touch production data/.

    Isolates:
    - Tool output directories (http, downloads)
    - Main SQLite database (aria.db)
    - ChromaDB path
    - Tools database (tools.db)
    - CLI engine (lazy — picks up patched paths)
    """
    http_dir = tmp_path / "http"
    http_dir.mkdir()
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    monkeypatch.setattr("aria.tools.http.functions.HTTP_OUTPUT_DIR", http_dir)

    for mod_name in _DOWNLOADS_DIR_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "DOWNLOADS_DIR"):
                monkeypatch.setattr(mod, "DOWNLOADS_DIR", downloads_dir)
        except ImportError:
            pass

    # ── Isolate ~/.aria root so tests never touch production data ──
    aria_home = tmp_path / "aria_home"
    aria_home.mkdir()
    monkeypatch.setenv("ARIA_HOME", str(aria_home))
    monkeypatch.setenv("TOOLS_DATA_FOLDER", str(aria_home / "workspace"))

    import aria.config.folders as _folders

    monkeypatch.setattr(_folders.Data, "path", aria_home)
    monkeypatch.setattr(_folders.Workspace, "path", aria_home / "workspace")
    monkeypatch.setattr(_folders.Bin, "path", aria_home / "bin")
    monkeypatch.setattr(_folders.Debug, "path", aria_home / "logs")
    monkeypatch.setattr(
        _folders.Debug, "logs_path", aria_home / "logs" / "debug.log"
    )
    monkeypatch.setattr(_folders.Storage, "path", aria_home / "storage")
    monkeypatch.setattr(_folders.Uploads, "path", aria_home / "uploads")
    monkeypatch.setattr(_folders.DB, "path", aria_home / "db")
    monkeypatch.setattr(_folders.Models, "path", aria_home / "models")

    # ── Isolate workspace / BASE_DIR for file + shell tools ────
    workspace_dir = aria_home / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    import aria.tools.constants as _tools_const

    monkeypatch.setattr(_tools_const, "BASE_DIR", workspace_dir)

    # Derived directories that tools.constants creates at import time
    for attr in ("CODE_DIR", "DOWNLOADS_DIR", "REPORTS_DIR"):
        if hasattr(_tools_const, attr):
            d = workspace_dir / attr.replace("_DIR", "").lower()
            d.mkdir(exist_ok=True)
            monkeypatch.setattr(_tools_const, attr, d)

    import aria.tools.shell.constants as _shell_const

    monkeypatch.setattr(_shell_const, "BASE_DIR", workspace_dir)

    # Also patch BASE_DIR in modules that imported it via `from ... import`
    # (local bindings are not updated by patching the source module)
    import aria.tools.files._internals as _file_internals

    monkeypatch.setattr(_file_internals, "BASE_DIR", workspace_dir)

    import aria.tools.shell.validation as _shell_valid

    monkeypatch.setattr(_shell_valid, "BASE_DIR", workspace_dir)

    # ── Patch modules with import-time cached runtime paths ─────────
    process_state = aria_home / "processes.json"
    process_logs = aria_home / "logs" / "processes"
    process_logs.mkdir(parents=True, exist_ok=True)

    try:
        import aria.tools.process.functions as _process_funcs

        monkeypatch.setattr(_process_funcs, "_STATE_FILE", process_state)
        monkeypatch.setattr(_process_funcs, "_LOG_DIR", process_logs)

        # Some tests import these module-level constants directly during test
        # collection, so patch their local bindings as well.
        try:
            import aria.tools.process.tests.test_process as _test_process

            monkeypatch.setattr(_test_process, "_STATE_FILE", process_state)
        except ImportError:
            pass
    except ImportError:
        pass

    try:
        import aria.server.manager as _server_manager

        monkeypatch.setattr(
            _server_manager.ServerManager,
            "PID_FILE",
            aria_home / "server.json",
        )
    except ImportError:
        pass

    try:
        import aria.server.vllm as _server_vllm

        monkeypatch.setattr(
            _server_vllm.VllmServerManager,
            "PID_FILE",
            aria_home / "vllm_servers.json",
        )
    except ImportError:
        pass

    browser_dir = workspace_dir / "browser"
    browser_dir.mkdir(parents=True, exist_ok=True)

    try:
        import aria.tools.browser.constants as _browser_constants

        monkeypatch.setattr(
            _browser_constants, "BROWSER_CONTENT_DIR", browser_dir
        )
    except ImportError:
        pass

    try:
        import aria.tools.browser.manager as _browser_manager

        monkeypatch.setattr(
            _browser_manager, "BROWSER_CONTENT_DIR", browser_dir
        )
    except ImportError:
        pass

    # ── Isolate main database (SQLite + ChromaDB) ──────────────
    db_dir = tmp_path / "db"
    db_dir.mkdir()

    import aria.config.database as _db_cfg

    monkeypatch.setattr(_db_cfg, "DB", type("DB", (), {"path": db_dir}))
    aria_db = db_dir / "aria.db"
    monkeypatch.setattr(_db_cfg, "_ARIA_DB_FILE_PATH", aria_db)
    monkeypatch.setattr(_db_cfg.SQLite, "file_path", aria_db)
    monkeypatch.setattr(_db_cfg.SQLite, "db_url", f"sqlite:///{aria_db}")
    monkeypatch.setattr(
        _db_cfg.SQLite, "conn_info", f"sqlite+aiosqlite:///{aria_db}"
    )
    monkeypatch.setattr(_db_cfg.ChromaDB, "db_path", db_dir / "chromadb")

    # ── Isolate tools database default path ────────────────────
    import aria.tools.database as _tools_db_mod

    monkeypatch.setattr(
        _tools_db_mod, "_DEFAULT_DB_PATH", str(tmp_path / "tools.db")
    )

    # ── Reset CLI engine so it picks up the patched SQLite path ─
    import aria.cli as _cli_mod

    _cli_mod._engine = None


def _reset_all_db_singletons():
    """Reset all database singletons so the next call creates fresh ones."""
    from aria.tools.database import ToolsDatabase
    from aria.tools.knowledge.database import KnowledgeDatabase
    from aria.tools.planner.database import PlannerDatabase
    from aria.tools.reasoning.database import ReasoningDatabase
    from aria.tools.scratchpad.database import ScratchpadDatabase

    setattr(ToolsDatabase, "_instance", None)
    setattr(ReasoningDatabase, "_instance", None)
    setattr(PlannerDatabase, "_instance", None)
    setattr(ScratchpadDatabase, "_instance", None)
    setattr(KnowledgeDatabase, "_instance", None)

    import aria.tools.database as db_module

    db_module._db_instance = None

    # Reset lazy module-level caches
    import aria.tools.planner.registry as planner_reg
    import aria.tools.reasoning.registry as reasoning_reg

    reasoning_reg._db = None
    planner_reg._db = None


@pytest.fixture()
def test_tools_db(tmp_path):
    """Create a temporary ToolsDatabase for test isolation.

    This fixture resets all database singletons, creates a fresh
    ToolsDatabase pointing at a temp file, and registers it as the
    global instance so that downstream code (e.g. KnowledgeDatabase,
    ScratchpadDatabase) uses the same temp DB.
    The temp file is automatically deleted by pytest's ``tmp_path``.

    Usage in test modules::

        def test_something(test_tools_db):
            ...
    """
    import aria.tools.database as db_module
    from aria.tools.database import ToolsDatabase

    _reset_all_db_singletons()

    db_path = str(tmp_path / "test_tools.db")
    test_db = ToolsDatabase(db_path)
    test_db.create_tables()

    # Register as the global singleton so get_tools_database() returns it
    db_module._db_instance = test_db

    yield test_db

    test_db.close()
    _reset_all_db_singletons()
