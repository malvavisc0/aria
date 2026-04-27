"""Tests for load_agent_instructions utility."""

from aria.agents.instructions import load_agent_instructions


class TestLoadAgentInstructions:
    """Tests for the load_agent_instructions function."""

    def test_loads_aria_instructions(self):
        """Aria instructions should be loaded."""
        result = load_agent_instructions("aria")
        assert "Aria" in result

    def test_loads_fundamental_principles_within_aria(self):
        """Fundamental principles should be embedded in aria.md."""
        result = load_agent_instructions("aria")
        assert "Fundamental Principles" in result
        assert "Response Style" in result

    def test_extras_appended(self):
        """Extras should appear in the output."""
        result = load_agent_instructions(
            "aria",
            extras="Custom extra note",
        )
        assert "Custom extra note" in result
        assert "Environment" in result

    def test_unknown_agent_returns_empty(self):
        """Unknown agent name should return empty string (no file found)."""
        result = load_agent_instructions("nonexistent_agent")
        assert result == ""

    def test_all_agents_load_successfully(self):
        """Every known agent should load without error."""
        agents = [
            "aria",
            "prompt_enhancer",
        ]
        for agent in agents:
            result = load_agent_instructions(agent)
            assert len(result) > 100, (
                f"Agent '{agent}' instructions too short "
                f"({len(result)} chars) — likely not loading"
            )

    def test_result_is_nonempty_string(self):
        """Result should always be a non-empty string for known agents."""
        result = load_agent_instructions("aria")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_prompt_enhancer_no_fundamental_principles(self):
        """PromptEnhancer should NOT contain fundamental principles."""
        result = load_agent_instructions("prompt_enhancer")
        assert "Fundamental Principles" not in result
        assert "Response Style" not in result
        assert "Prompt Enhancer" in result

    def test_variables_substituted(self):
        """Template variables should be replaced when present."""
        result = load_agent_instructions(
            "aria",
            extras="Value: {{TEST_KEY}}",
            variables={"TEST_KEY": "replaced_value"},
        )
        assert "replaced_value" in result
        assert "{{TEST_KEY}}" not in result
