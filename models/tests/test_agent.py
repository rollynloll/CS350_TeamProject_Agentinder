"""Tests for Agent — getters, setters, business logic."""
import pytest
from uuid import uuid4

from models.agent.agent import Agent
from models.agent.agent_profile import AgentProfile
from models.agent.agent_personality import AgentPersonality
from models.enums import SwipeEnum, VisibilityEnum
from models.types import Match


def _make_agent(visibility=VisibilityEnum.PUBLIC, date_count=0):
    agent_id = uuid4()
    principal_id = uuid4()
    profile = AgentProfile(
        agent_id=agent_id,
        display_name="TestBot",
        visibility=visibility,
        capability_tags=["coding"],
        style_vector={"formality": 0.5},
        date_count=date_count,
    )
    personality = AgentPersonality(
        surface={"bio": "Test bot.", "style_sliders": {"formality": 0.5}},
        deep={"thinking_style": "logical", "values": ["accuracy"], "conflict_handling": "direct"},
        aspiration={"collaboration_goals": [], "interest_domains": []},
    )
    return Agent(agent_id=agent_id, principal_id=principal_id, profile=profile, personality=personality)


class TestGetters:
    def test_agent_id_immutable(self):
        agent = _make_agent()
        aid = agent.agent_id
        assert aid == agent.agent_id

    def test_principal_id(self):
        agent = _make_agent()
        assert agent.principal_id == agent.getPrincipalId()

    def test_get_profile_full(self):
        agent = _make_agent()
        p = agent.getProfile()
        assert isinstance(p, AgentProfile)
        assert p.display_name == "TestBot"

    def test_get_profile_fields_subset(self):
        agent = _make_agent()
        result = agent.getProfile(fields=["display_name"])
        assert isinstance(result, dict)
        assert "display_name" in result
        assert "visibility" not in result

    def test_get_personality_full(self):
        agent = _make_agent()
        p = agent.getPersonality()
        assert isinstance(p, AgentPersonality)

    def test_get_personality_fields_subset(self):
        agent = _make_agent()
        result = agent.getPersonality(fields=["surface"])
        assert isinstance(result, dict)
        assert "surface" in result

    def test_get_trust_score_initially_none(self):
        agent = _make_agent()
        assert agent.getTrustScore() is None

    def test_get_llm_client_initially_none(self):
        agent = _make_agent()
        assert agent.getLLMClient() is None


class TestSetters:
    def test_set_profile(self):
        agent = _make_agent()
        agent.setProfile({"display_name": "UpdatedBot"})
        assert agent.getProfile().display_name == "UpdatedBot"

    def test_set_personality_syncs_style_vector(self):
        agent = _make_agent()
        agent.setPersonality({"surface": {"bio": "New bio", "style_sliders": {"formality": 0.9}}})
        assert agent.getProfile().style_vector["formality"] == 0.9

    def test_set_personality_without_sliders_no_crash(self):
        agent = _make_agent()
        agent.setPersonality({"surface": {"bio": "No sliders"}})
        # Should not raise

    def test_update_trust_score(self):
        agent = _make_agent()
        agent.updateTrustScore(0.75)
        assert agent.getTrustScore() == 0.75

    def test_set_llm_client(self):
        from unittest.mock import MagicMock
        agent = _make_agent()
        mock_client = MagicMock()
        agent.setLLMClient(mock_client)
        assert agent.getLLMClient() is mock_client


class TestIsActive:
    def test_not_active_initially(self):
        agent = _make_agent()
        assert agent.isActive() is False

    def test_active_after_join_date(self):
        agent = _make_agent()
        agent.joinDate(uuid4())
        assert agent.isActive() is True

    def test_not_active_after_leave_date(self):
        agent = _make_agent()
        date_id = uuid4()
        agent.joinDate(date_id)
        agent.leaveDate(date_id)
        assert agent.isActive() is False

    def test_join_same_date_id_twice_no_duplicate(self):
        agent = _make_agent()
        date_id = uuid4()
        agent.joinDate(date_id)
        agent.joinDate(date_id)
        agent.leaveDate(date_id)
        assert agent.isActive() is False


class TestIsVisibleTo:
    def test_public_always_visible(self):
        agent = _make_agent(visibility=VisibilityEnum.PUBLIC)
        assert agent.isVisibleTo(0.0) is True
        assert agent.isVisibleTo(0.9) is True

    def test_restricted_visible_above_threshold(self):
        agent = _make_agent(visibility=VisibilityEnum.RESTRICTED)
        assert agent.isVisibleTo(0.5) is True
        assert agent.isVisibleTo(0.9) is True

    def test_restricted_invisible_below_threshold(self):
        agent = _make_agent(visibility=VisibilityEnum.RESTRICTED)
        assert agent.isVisibleTo(0.49) is False
        assert agent.isVisibleTo(0.0) is False

    def test_hidden_never_visible(self):
        agent = _make_agent(visibility=VisibilityEnum.HIDDEN)
        assert agent.isVisibleTo(0.0) is False
        assert agent.isVisibleTo(1.0) is False


class TestIsNewAgent:
    def test_new_agent_below_5_dates(self):
        for count in range(5):
            agent = _make_agent(date_count=count)
            assert agent.isNewAgent() is True

    def test_not_new_agent_at_5_dates(self):
        agent = _make_agent(date_count=5)
        assert agent.isNewAgent() is False


class TestDateLifecycle:
    def test_leave_date_increments_date_count(self):
        agent = _make_agent(date_count=0)
        date_id = uuid4()
        agent.joinDate(date_id)
        agent.leaveDate(date_id)
        assert agent.getProfile().date_count == 1

    def test_tier_badge_below_5(self):
        agent = _make_agent(date_count=0)
        date_id = uuid4()
        agent.joinDate(date_id)
        agent.leaveDate(date_id)
        assert agent.getProfile().tier_badge == "new_agent"

    def test_tier_badge_at_5(self):
        agent = _make_agent(date_count=4)
        date_id = uuid4()
        agent.joinDate(date_id)
        agent.leaveDate(date_id)
        assert agent.getProfile().tier_badge == "5"


class TestSwipe:
    def test_swipe_left_returns_none(self):
        agent = _make_agent()
        result = agent.swipe(uuid4(), SwipeEnum.LEFT)
        assert result is None

    def test_swipe_right_returns_match(self):
        agent = _make_agent()
        target = uuid4()
        result = agent.swipe(target, SwipeEnum.RIGHT)
        assert isinstance(result, Match)
        assert result.agent_a_id == agent.agent_id
        assert result.agent_b_id == target

    def test_swipe_up_returns_match(self):
        agent = _make_agent()
        result = agent.swipe(uuid4(), SwipeEnum.UP)
        assert isinstance(result, Match)


class TestSendMessage:
    def test_send_message_without_llm_client_raises(self):
        agent = _make_agent()
        with pytest.raises(RuntimeError):
            agent.sendMessage(uuid4(), "Hello")

    def test_send_message_delegates_to_llm_client(self):
        from unittest.mock import MagicMock
        agent = _make_agent()
        mock_client = MagicMock()
        mock_client.generate.return_value = "Hello back!"
        agent.setLLMClient(mock_client)
        response = agent.sendMessage(uuid4(), "Hello")
        assert response == "Hello back!"
        mock_client.generate.assert_called_once()
