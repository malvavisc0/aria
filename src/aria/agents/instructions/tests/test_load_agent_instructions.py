"""Tests for load_agent_instructions utility."""

from pathlib import Path

from aria.agents.instructions import (
    ALL_BASE_SECTIONS,
    load_agent_instructions,
)


class TestLoadAgentInstructions:
    """Tests for the load_agent_instructions function."""

    def test_loads_aria_instructions(self):
        """Aria instructions should be loaded."""
        result = load_agent_instructions("aria")
        assert "Aria" in result

    def test_loads_core_sections_within_aria(self):
        """Shared and role-specific sections should load for Aria."""
        result = load_agent_instructions("aria")
        assert "Core Rules" in result
        assert "Identity" in result
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
        """Unknown agent name should return empty string."""
        result = load_agent_instructions("nonexistent_agent")
        assert result == ""

    def test_all_agents_load_successfully(self):
        """Every known agent should load without error."""
        agents = ["aria", "prompt_enhancer"]
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

    def test_worker_includes_base_sections(self):
        """Worker should include core, tools, and failure sections."""
        result = load_agent_instructions("worker")
        assert "Core Rules" in result
        assert "Execution discipline" in result

    def test_prompt_enhancer_no_response_style(self):
        """PromptEnhancer should remain specialized."""
        result = load_agent_instructions("prompt_enhancer")
        assert "Response Style" not in result
        assert "Prompt Enhancer" in result
        assert "Aria Operating Model" in result

    def test_variables_substituted(self):
        """Template variables should be replaced when present."""
        result = load_agent_instructions(
            "aria",
            extras="Value: {{TEST_KEY}}",
            variables={"TEST_KEY": "replaced_value"},
        )
        assert "replaced_value" in result
        assert "{{TEST_KEY}}" not in result

    def test_base_sections_selective_loading(self):
        """Only requested base sections should be included."""
        result = load_agent_instructions("aria", base_sections=["core"])
        assert "Core Rules" in result
        assert "Direct Tools" not in result
        assert "Evidence" not in result

    def test_base_sections_default_loads_all(self):
        """Default (None) should load all base sections."""
        result = load_agent_instructions("aria")
        base_dir = Path(__file__).parent.parent / "base"
        for section in ALL_BASE_SECTIONS:
            section_path = base_dir / f"{section}.md"
            if section_path.exists():
                content = section_path.read_text()
                first_heading = next(
                    (
                        line
                        for line in content.splitlines()
                        if line.startswith("## ")
                    ),
                    None,
                )
                if first_heading:
                    assert first_heading.lstrip("# ") in result

    def test_base_sections_empty_list(self):
        """Empty list should load no base sections."""
        result = load_agent_instructions("aria", base_sections=[])
        assert "Core Rules" not in result
        assert "Identity" in result  # agent-specific still loads
