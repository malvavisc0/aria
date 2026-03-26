"""Tests for load_agent_instructions utility."""

from aria.agents.instructions import load_agent_instructions


class TestLoadAgentInstructions:
    """Tests for the load_agent_instructions function."""

    def test_loads_core_rules(self):
        """Core rules should be included by default."""
        result = load_agent_instructions("aria")
        assert "Core Agent Rules" in result

    def test_loads_agent_specific_instructions(self):
        """Agent-specific instructions should be loaded."""
        result = load_agent_instructions("aria")
        assert "Aria" in result

    def test_core_and_agent_combined(self):
        """Both core rules and agent instructions should appear."""
        result = load_agent_instructions("guido")
        assert "Core Agent Rules" in result
        assert "Python Developer Agent" in result

    def test_exclude_core_rules(self):
        """When include_core=False, core rules should be absent."""
        result = load_agent_instructions(
            "aria",
            include_core=False,
        )
        assert "Core Agent Rules" not in result
        assert "Aria" in result

    def test_extras_appended(self):
        """Extras should appear in the output."""
        result = load_agent_instructions(
            "aria",
            extras="Custom extra note",
        )
        assert "Custom extra note" in result
        assert "Additional Notes" in result

    def test_variable_substitution(self):
        """Template variables should be replaced."""
        result = load_agent_instructions(
            "wanderer",
            variables={"BROWSER_TOOLS_NOTE": "Tools are ready"},
        )
        assert "Tools are ready" in result
        assert "{{BROWSER_TOOLS_NOTE}}" not in result

    def test_unknown_agent_returns_core_only(self):
        """Unknown agent name should still return core rules."""
        result = load_agent_instructions("nonexistent_agent")
        assert "Core Agent Rules" in result

    def test_all_agents_load_successfully(self):
        """Every known agent should load without error."""
        agents = [
            "aria",
            "guido",
            "spielberg",
            "wanderer",
            "wizard",
            "prompt_enhancer",
        ]
        for agent in agents:
            result = load_agent_instructions(agent)
            assert len(result) > 100, (
                f"Agent '{agent}' instructions too short "
                f"({len(result)} chars) — likely not loading"
            )

    def test_result_is_nonempty_string(self):
        """Result should always be a non-empty string."""
        result = load_agent_instructions("aria")
        assert isinstance(result, str)
        assert len(result) > 0
