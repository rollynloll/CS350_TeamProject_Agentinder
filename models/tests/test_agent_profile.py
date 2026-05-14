"""Tests for AgentProfile."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from models.agent.agent_profile import AgentProfile
from models.enums import VisibilityEnum


def _make_profile(**kwargs):
    defaults = dict(
        agent_id=uuid4(),
        display_name="TestBot",
        capability_tags=["coding"],
        style_vector={"formality": 0.5},
        date_count=0,
    )
    defaults.update(kwargs)
    return AgentProfile(**defaults)


class TestAgentProfileCreation:
    def test_defaults(self):
        p = AgentProfile(agent_id=uuid4(), display_name="Bot")
        assert p.visibility == VisibilityEnum.PUBLIC
        assert p.capability_tags == []
        assert p.capability_embedding is None
        assert p.style_vector == {}
        assert p.available_timezones == []
        assert p.tier_badge == "new_agent"
        assert p.date_count == 0

    def test_custom_values(self):
        aid = uuid4()
        p = AgentProfile(
            agent_id=aid,
            display_name="Alpha",
            visibility=VisibilityEnum.RESTRICTED,
            capability_tags=["coding", "analysis"],
            style_vector={"formality": 0.8},
            date_count=3,
        )
        assert p.agent_id == aid
        assert p.visibility == VisibilityEnum.RESTRICTED
        assert len(p.capability_tags) == 2


class TestIsNewAgent:
    def test_new_agent_below_5(self):
        for count in range(5):
            p = _make_profile(date_count=count)
            assert p.is_new_agent() is True

    def test_not_new_agent_at_5(self):
        p = _make_profile(date_count=5)
        assert p.is_new_agent() is False

    def test_not_new_agent_above_5(self):
        p = _make_profile(date_count=100)
        assert p.is_new_agent() is False


class TestAgentProfileUpdate:
    def test_update_display_name(self):
        p = _make_profile(display_name="OldName")
        p.update({"display_name": "NewName"})
        assert p.display_name == "NewName"

    def test_update_visibility(self):
        p = _make_profile()
        p.update({"visibility": VisibilityEnum.HIDDEN})
        assert p.visibility == VisibilityEnum.HIDDEN

    def test_update_capability_tags(self):
        p = _make_profile(capability_tags=["coding"])
        p.update({"capability_tags": ["coding", "design"]})
        assert "design" in p.capability_tags

    def test_update_style_vector(self):
        p = _make_profile(style_vector={"formality": 0.3})
        p.update({"style_vector": {"formality": 0.9}})
        assert p.style_vector["formality"] == 0.9

    def test_update_ignores_unknown_fields(self):
        p = _make_profile()
        p.update({"nonexistent": "value"})
        assert not hasattr(p, "nonexistent")

    def test_updated_at_changes(self):
        p = _make_profile()
        before = p.updated_at
        p.update({"display_name": "Changed"})
        assert p.updated_at >= before
