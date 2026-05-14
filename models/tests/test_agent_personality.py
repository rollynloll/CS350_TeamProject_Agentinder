"""Tests for AgentPersonality."""
import pytest
from models.agent.agent_personality import AgentPersonality


def _full_personality():
    return AgentPersonality(
        surface={
            "bio": "A sharp analytical agent.",
            "style_sliders": {"formality": 0.8, "creativity": 0.4},
        },
        deep={
            "thinking_style": "systematic",
            "values": ["accuracy", "clarity"],
            "conflict_handling": "reason-first",
        },
        aspiration={
            "collaboration_goals": ["pair-review"],
            "interest_domains": ["software", "data"],
        },
    )


class TestAgentPersonalityCreation:
    def test_default_empty(self):
        p = AgentPersonality()
        assert p.surface == {}
        assert p.deep == {}
        assert p.aspiration == {}
        assert p.system_prompt_cache is None

    def test_full_creation(self):
        p = _full_personality()
        assert p.surface["bio"] == "A sharp analytical agent."
        assert "accuracy" in p.deep["values"]
        assert "software" in p.aspiration["interest_domains"]


class TestToSummary:
    def test_includes_bio(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "sharp analytical" in summary

    def test_includes_style_sliders(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "formality" in summary

    def test_includes_thinking_style(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "systematic" in summary

    def test_includes_values(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "accuracy" in summary

    def test_includes_conflict_handling(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "reason-first" in summary

    def test_includes_goals(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "pair-review" in summary

    def test_includes_domains(self):
        p = _full_personality()
        summary = p.toSummary()
        assert "software" in summary

    def test_empty_personality_no_crash(self):
        p = AgentPersonality()
        summary = p.toSummary()
        assert isinstance(summary, str)


class TestToPrompt:
    def test_builds_and_caches(self):
        p = _full_personality()
        assert p.system_prompt_cache is None
        prompt = p.toPrompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert p.system_prompt_cache == prompt  # cached

    def test_returns_cached_on_second_call(self):
        p = _full_personality()
        first = p.toPrompt()
        p.system_prompt_cache = "overridden"
        second = p.toPrompt()
        assert second == "overridden"

    def test_prompt_contains_bio(self):
        p = _full_personality()
        prompt = p.toPrompt()
        assert "sharp analytical" in prompt

    def test_prompt_contains_values(self):
        p = _full_personality()
        prompt = p.toPrompt()
        assert "accuracy" in prompt

    def test_prompt_instructs_to_stay_in_character(self):
        p = _full_personality()
        prompt = p.toPrompt()
        assert "character" in prompt.lower() or "personality" in prompt.lower()


class TestUpdate:
    def test_update_surface_regenerates_cache(self):
        p = _full_personality()
        old_prompt = p.toPrompt()
        p.update({"surface": {"bio": "A new bio."}})
        assert p.system_prompt_cache != old_prompt
        assert "new bio" in p.system_prompt_cache

    def test_update_deep_regenerates_cache(self):
        p = _full_personality()
        p.toPrompt()
        p.update({"deep": {"thinking_style": "creative", "values": [], "conflict_handling": ""}})
        assert "creative" in p.system_prompt_cache

    def test_update_aspiration_regenerates_cache(self):
        p = _full_personality()
        p.toPrompt()
        p.update({"aspiration": {"collaboration_goals": ["mentoring"], "interest_domains": []}})
        assert "mentoring" in p.system_prompt_cache

    def test_update_ignores_unknown_fields(self):
        p = _full_personality()
        old_cache = p.toPrompt()
        p.update({"unknown_field": "value"})
        # cache should not have changed since no valid field was updated
        assert p.system_prompt_cache == old_cache

    def test_updated_at_changes(self):
        p = _full_personality()
        before = p.updated_at
        p.update({"surface": {"bio": "Updated"}})
        assert p.updated_at >= before
