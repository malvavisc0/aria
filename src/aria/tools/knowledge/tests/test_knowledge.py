"""Tests for knowledge store tool."""

import json
import os
import tempfile

import pytest

from aria.tools.database import ToolsDatabase
from aria.tools.knowledge import knowledge
from aria.tools.knowledge.database import KnowledgeDatabase


@pytest.fixture(autouse=True)
def test_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_knowledge.db")

        # Reset singletons
        ToolsDatabase._instance = None
        KnowledgeDatabase._instance = None

        import aria.tools.database as db_module
        import aria.tools.knowledge.database as kdb_module

        db_module._db_instance = None
        kdb_module.KnowledgeDatabase._instance = None
        kdb_module.KnowledgeDatabase._initialized = False

        test_db = ToolsDatabase(db_path)
        test_kdb = KnowledgeDatabase()

        yield test_kdb

        # Cleanup
        test_db.close()
        ToolsDatabase._instance = None
        KnowledgeDatabase._instance = None
        db_module._db_instance = None


class TestKnowledgeStore:
    """Test suite for knowledge store tool."""

    def test_store_and_recall(self, test_db):
        """Test storing and recalling a knowledge entry."""
        result = knowledge(
            "Store user preference",
            action="store",
            key="user_language",
            value="Python",
        )
        data = json.loads(result)
        assert data["data"]["action"] == "store"
        assert data["data"]["key"] == "user_language"

        # Recall it
        result = knowledge(
            "Recall user preference",
            action="recall",
            key="user_language",
        )
        data = json.loads(result)
        assert data["data"]["found"] is True
        assert data["data"]["value"] == "Python"

    def test_recall_missing_key(self, test_db):
        """Test recalling a non-existent key."""
        result = knowledge(
            "Recall missing key",
            action="recall",
            key="nonexistent_key",
        )
        data = json.loads(result)
        assert data["data"]["found"] is False

    def test_store_with_tags(self, test_db):
        """Test storing with tags."""
        result = knowledge(
            "Store with tags",
            action="store",
            key="project_name",
            value="Aria",
            tags=["project", "config"],
        )
        data = json.loads(result)
        assert data["data"]["action"] == "store"

        # Recall to verify tags
        result = knowledge(
            "Recall with tags",
            action="recall",
            key="project_name",
        )
        data = json.loads(result)
        assert data["data"]["tags"] == ["project", "config"]

    def test_search_entries(self, test_db):
        """Test searching knowledge entries."""
        knowledge(
            "Store entry 1", action="store", key="api_key", value="abc123"
        )
        knowledge(
            "Store entry 2",
            action="store",
            key="api_url",
            value="https://example.com",
        )

        result = knowledge(
            "Search for api",
            action="search",
            query="api",
        )
        data = json.loads(result)
        assert data["data"]["results_count"] == 2

    def test_list_entries(self, test_db):
        """Test listing all entries."""
        knowledge("Store 1", action="store", key="key1", value="val1")
        knowledge("Store 2", action="store", key="key2", value="val2")

        result = knowledge("List all", action="list")
        data = json.loads(result)
        assert data["data"]["count"] == 2

    def test_list_by_tag(self, test_db):
        """Test listing entries filtered by tag."""
        knowledge(
            "Store tagged",
            action="store",
            key="k1",
            value="v1",
            tags=["important"],
        )
        knowledge("Store untagged", action="store", key="k2", value="v2")

        result = knowledge("List by tag", action="list", tags=["important"])
        data = json.loads(result)
        assert data["data"]["count"] == 1

    def test_update_entry(self, test_db):
        """Test updating an existing entry."""
        store_result = knowledge(
            "Store for update", action="store", key="updatable", value="old"
        )
        entry_id = json.loads(store_result)["data"]["entry_id"]

        result = knowledge(
            "Update entry",
            action="update",
            entry_id=entry_id,
            value="new",
        )
        data = json.loads(result)
        assert data["data"]["action"] == "update"

        # Verify updated value
        result = knowledge("Recall updated", action="recall", key="updatable")
        data = json.loads(result)
        assert data["data"]["value"] == "new"

    def test_delete_entry(self, test_db):
        """Test deleting an entry."""
        store_result = knowledge(
            "Store for delete", action="store", key="deletable", value="gone"
        )
        entry_id = json.loads(store_result)["data"]["entry_id"]

        result = knowledge(
            "Delete entry",
            action="delete",
            entry_id=entry_id,
        )
        data = json.loads(result)
        assert data["data"]["action"] == "delete"

        # Verify it's gone
        result = knowledge("Recall deleted", action="recall", key="deletable")
        data = json.loads(result)
        assert data["data"]["found"] is False

    def test_store_missing_key(self, test_db):
        """Test store without key returns error."""
        result = knowledge("Bad store", action="store", value="no key")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_store_missing_value(self, test_db):
        """Test store without value returns error."""
        result = knowledge("Bad store", action="store", key="no_value")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_invalid_action(self, test_db):
        """Test invalid action returns error."""
        result = knowledge("Bad action", action="explode")
        data = json.loads(result)
        assert "error" in data["data"]

    def test_multi_agent_isolation(self, test_db):
        """Test that different agents have isolated knowledge."""
        knowledge(
            "Agent 1 store",
            action="store",
            key="secret",
            value="agent1_data",
            agent_id="agent_1",
        )
        knowledge(
            "Agent 2 store",
            action="store",
            key="secret",
            value="agent2_data",
            agent_id="agent_2",
        )

        r1 = knowledge(
            "Agent 1 recall", action="recall", key="secret", agent_id="agent_1"
        )
        r2 = knowledge(
            "Agent 2 recall", action="recall", key="secret", agent_id="agent_2"
        )

        assert json.loads(r1)["data"]["value"] == "agent1_data"
        assert json.loads(r2)["data"]["value"] == "agent2_data"
