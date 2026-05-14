"""Tests for AgentService — create, update, get."""
import pytest
from uuid import uuid4

from models.agent.agent_service import AgentService
from models.agent.agent import Agent
from models.agent.agent_personality import AgentPersonality
from models.enums import PlanEnum, VisibilityEnum


def _profile_data(name="TestBot", tags=None, llm_model=None):
    data = {
        "display_name": name,
        "capability_tags": tags or ["coding"],
        "personality": {
            "surface": {"bio": "Test bot.", "style_sliders": {"formality": 0.5}},
            "deep": {"thinking_style": "logical", "values": ["accuracy"], "conflict_handling": "direct"},
            "aspiration": {"collaboration_goals": ["review"], "interest_domains": ["tech"]},
        },
    }
    if llm_model:
        data["llm_model"] = llm_model
    return data


class TestCreate:
    def test_returns_agent_and_key(self):
        svc = AgentService()
        agent, key = svc.create(uuid4(), _profile_data())
        assert isinstance(agent, Agent)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_agent_has_correct_display_name(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data(name="MyBot"))
        assert agent.getProfile().display_name == "MyBot"

    def test_agent_has_personality(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data())
        assert isinstance(agent.getPersonality(), AgentPersonality)

    def test_system_prompt_cached_on_create(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data())
        assert agent.getPersonality().system_prompt_cache is not None

    def test_style_vector_synced_from_personality(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data())
        assert agent.getProfile().style_vector.get("formality") == 0.5

    def test_llm_client_created(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data())
        assert agent.getLLMClient() is not None

    def test_plaintext_key_not_stored(self):
        svc = AgentService()
        agent, key = svc.create(uuid4(), _profile_data())
        stored_hash = svc._credentials[agent.agent_id]
        assert stored_hash != key  # hash ≠ plaintext

    def test_free_plan_limit_5(self):
        svc = AgentService()
        pid = uuid4()
        for i in range(5):
            svc.create(pid, _profile_data(name=f"Bot{i}"), plan=PlanEnum.FREE)
        with pytest.raises(PermissionError, match="limit"):
            svc.create(pid, _profile_data(name="Bot6"), plan=PlanEnum.FREE)

    def test_premium_plan_limit_20(self):
        svc = AgentService()
        pid = uuid4()
        for i in range(20):
            svc.create(pid, _profile_data(name=f"Bot{i}"), plan=PlanEnum.PREMIUM)
        with pytest.raises(PermissionError, match="limit"):
            svc.create(pid, _profile_data(name="Bot21"), plan=PlanEnum.PREMIUM)

    def test_duplicate_name_raises(self):
        svc = AgentService()
        pid = uuid4()
        svc.create(pid, _profile_data(name="DupBot"))
        with pytest.raises(ValueError, match="DupBot"):
            svc.create(pid, _profile_data(name="DupBot"))

    def test_different_principals_can_share_name(self):
        svc = AgentService()
        svc.create(uuid4(), _profile_data(name="SharedName"))
        svc.create(uuid4(), _profile_data(name="SharedName"))  # should not raise

    def test_agent_stored_and_retrievable(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data())
        retrieved = svc.get(agent.agent_id)
        assert retrieved is agent


class TestGet:
    def test_get_existing_agent(self):
        svc = AgentService()
        agent, _ = svc.create(uuid4(), _profile_data())
        assert svc.get(agent.agent_id) is agent

    def test_get_missing_agent_raises(self):
        svc = AgentService()
        with pytest.raises(KeyError):
            svc.get(uuid4())


class TestUpdate:
    def test_update_display_name(self):
        svc = AgentService()
        pid = uuid4()
        agent, _ = svc.create(pid, _profile_data(name="OldName"))
        svc.update(agent.agent_id, pid, {"display_name": "NewName"})
        assert svc.get(agent.agent_id).getProfile().display_name == "NewName"

    def test_update_wrong_principal_raises(self):
        svc = AgentService()
        pid = uuid4()
        agent, _ = svc.create(pid, _profile_data())
        with pytest.raises(PermissionError):
            svc.update(agent.agent_id, uuid4(), {"display_name": "Hack"})

    def test_update_personality_regenerates_prompt_cache(self):
        svc = AgentService()
        pid = uuid4()
        agent, _ = svc.create(pid, _profile_data())
        old_cache = agent.getPersonality().system_prompt_cache
        svc.update(agent.agent_id, pid, {
            "personality": {"surface": {"bio": "Completely different bio."}}
        })
        new_cache = agent.getPersonality().system_prompt_cache
        assert new_cache != old_cache
        assert "Completely different bio" in new_cache

    def test_update_capability_tags(self):
        svc = AgentService()
        pid = uuid4()
        agent, _ = svc.create(pid, _profile_data(tags=["coding"]))
        svc.update(agent.agent_id, pid, {"capability_tags": ["coding", "design"]})
        assert "design" in agent.getProfile().capability_tags

    def test_update_llm_model_rebuilds_client(self):
        svc = AgentService()
        pid = uuid4()
        agent, _ = svc.create(pid, _profile_data())
        old_client = agent.getLLMClient()
        svc.update(agent.agent_id, pid, {"llm_model": "gpt-4-turbo"})
        new_client = agent.getLLMClient()
        assert new_client is not old_client
        assert new_client.model == "gpt-4-turbo"

    def test_update_returns_agent(self):
        svc = AgentService()
        pid = uuid4()
        agent, _ = svc.create(pid, _profile_data())
        returned = svc.update(agent.agent_id, pid, {"display_name": "Updated"})
        assert isinstance(returned, Agent)
