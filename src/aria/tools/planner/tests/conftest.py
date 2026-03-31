"""Shared fixtures for planner tests."""

import os
import tempfile

import pytest

from aria.tools.database import ToolsDatabase
from aria.tools.planner.database import PlannerDatabase


@pytest.fixture(autouse=True)
def test_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tools.db")

        # Reset singletons
        ToolsDatabase._instance = None
        PlannerDatabase._instance = None

        # Reset the module-level _db_instance in get_tools_database
        import aria.tools.database as db_module

        db_module._db_instance = None

        test_tools_db = ToolsDatabase(db_path)
        test_planner_db = PlannerDatabase()

        import aria.tools.planner.registry as reg_module

        reg_module._db = test_planner_db

        yield test_planner_db

        test_tools_db.close()
        ToolsDatabase._instance = None
        PlannerDatabase._instance = None
        db_module._db_instance = None
        reg_module._db = None
