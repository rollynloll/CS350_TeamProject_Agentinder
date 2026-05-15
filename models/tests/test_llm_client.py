"""Tests for LLMClient — generate flow and stub behavior."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from models.llm.llm_client import LLMClient
from models.agent.agent import Agent
from models.agent.agent_profile import AgentProfile
from models.agent.agent_personality import AgentPersonality
from models.types import Message


def _make_agent():
    agent_id = uuid4()
    profile = AgentProfile(
        agent_id=agent_id,
        display_name="TestBot",
        capability_tags=["coding"],
        style_vector={"formality": 0.5},
    )
    personality = AgentPersonality(
        surface={"bio": "Test bot.", "style_sliders": {"formality": 0.5}},
        deep={"thinking_style": "logical", "values": ["precision"], "conflict_handling": "direct"},
        aspiration={"collaboration_goals": [], "interest_domains": []},
    )
    return Agent(
        agent_id=agent_id,
        principal_id=uuid4(),
        profile=profile,
        personality=personality,
    )


class TestLLMClientCreation:
    def test_default_model(self):
        client = LLMClient()
        assert client.model == "gpt-4o"

    def test_custom_model(self):
        client = LLMClient(model="gpt-4-turbo")
        assert client.model == "gpt-4-turbo"

    def test_consistency_manager_attached(self):
        from models.llm.personality_consistency_manager import PersonalityConsistencyManager
        client = LLMClient()
        assert isinstance(client.consistency_manager, PersonalityConsistencyManager)


class TestGenerate:
    def test_no_agent_raises(self):
        client = LLMClient()
        with pytest.raises(RuntimeError, match="no agent"):
            client.generate(history=[], turn_count=1)

    def test_stub_response_when_no_api_key(self):
        client = LLMClient()
        agent = _make_agent()
        client.agent = agent
        # No OPENAI_API_KEY set — should return stub string
        history = [Message(role="user", content="Hello")]
        response = client.generate(history=history, turn_count=1)
        assert isinstance(response, str)
        assert "stub" in response.lower() or len(response) > 0

    def test_calls_build_messages(self):
        client = LLMClient()
        agent = _make_agent()
        client.agent = agent
        with patch.object(client.consistency_manager, "buildMessages", wraps=client.consistency_manager.buildMessages) as mock_build:
            client.generate(history=[Message(role="user", content="Hi")], turn_count=1)
            mock_build.assert_called_once()

    def test_check_not_called_on_non_check_turn(self):
        client = LLMClient(anchor_interval=5)
        agent = _make_agent()
        client.agent = agent
        with patch.object(client.consistency_manager, "check") as mock_check:
            # turn 1 is not anchor+1
            client.generate(history=[Message(role="user", content="Hi")], turn_count=1)
            mock_check.assert_not_called()

    def test_check_called_on_check_turn(self):
        client = LLMClient(anchor_interval=5)
        agent = _make_agent()
        client.agent = agent
        # is_check_turn(6) = True (5 is anchor, 6 is anchor+1)
        with patch.object(client.consistency_manager, "check", return_value=True) as mock_check:
            client.generate(history=[Message(role="user", content="Hi")], turn_count=6)
            mock_check.assert_called_once()

    def test_fail_triggers_retry(self):
        client = LLMClient(anchor_interval=5)
        agent = _make_agent()
        client.agent = agent
        call_count = {"n": 0}

        def mock_call(messages):
            call_count["n"] += 1
            return f"response_{call_count['n']}"

        client._call_llm = mock_call
        # Always FAIL → should call _call_llm twice (original + retry)
        client.consistency_manager.set_checker(lambda p: "FAIL")
        client.generate(history=[Message(role="user", content="Hi")], turn_count=6)
        assert call_count["n"] == 2

    def test_fail_then_pass_returns_retry_response(self):
        client = LLMClient(anchor_interval=5)
        agent = _make_agent()
        client.agent = agent
        responses = iter(["bad_response", "good_response"])
        client._call_llm = lambda _: next(responses)

        check_calls = {"n": 0}
        def checker(prompt):
            check_calls["n"] += 1
            return "PASS" if check_calls["n"] > 1 else "FAIL"

        client.consistency_manager.set_checker(checker)
        result = client.generate(history=[Message(role="user", content="Hi")], turn_count=6)
        assert result == "good_response"

    def test_double_fail_returns_original(self):
        client = LLMClient(anchor_interval=5)
        agent = _make_agent()
        client.agent = agent
        responses = iter(["original", "retry"])
        client._call_llm = lambda _: next(responses)
        # Always FAIL
        client.consistency_manager.set_checker(lambda p: "FAIL")
        result = client.generate(history=[Message(role="user", content="Hi")], turn_count=6)
        assert result == "original"
