"""Pytest configuration and fixtures for aria tests."""

import importlib

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
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
    """Redirect all tool output directories to tmp_path so tests never pollute production data/."""
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


def _reset_all_db_singletons():
    """Reset all database singletons so the next call creates fresh ones."""
    from aria.tools.database import ToolsDatabase
    from aria.tools.knowledge.database import KnowledgeDatabase
    from aria.tools.planner.database import PlannerDatabase
    from aria.tools.reasoning.database import ReasoningDatabase
    from aria.tools.scratchpad.database import ScratchpadDatabase

    ToolsDatabase._instance = None
    ReasoningDatabase._instance = None
    PlannerDatabase._instance = None
    ScratchpadDatabase._instance = None
    KnowledgeDatabase._instance = None

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
