"""Pytest configuration and fixtures for aria tests."""

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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
    ToolsDatabase pointing at a temp file, and cleans up afterwards.
    The temp file is automatically deleted by pytest's ``tmp_path``.

    Usage in test modules::

        def test_something(test_tools_db):
            ...
    """
    from aria.tools.database import ToolsDatabase

    _reset_all_db_singletons()

    db_path = str(tmp_path / "test_tools.db")
    test_db = ToolsDatabase(db_path)
    test_db.create_tables()

    yield test_db

    test_db.close()
    _reset_all_db_singletons()
