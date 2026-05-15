"""Tests for PersonalityConsistencyManager."""
import pytest
from models.llm.personality_consistency_manager import PersonalityConsistencyManager
from models.agent.agent_personality import AgentPersonality
from models.types import Message


def _make_personality():
    return AgentPersonality(
        surface={"bio": "Test agent.", "style_sliders": {"formality": 0.7}},
        deep={"thinking_style": "logical", "values": ["precision"], "conflict_handling": "direct"},
        aspiration={"collaboration_goals": ["review"], "interest_domains": ["tech"]},
    )


def _make_history(n=2):
    return [Message(role="user" if i % 2 == 0 else "assistant", content=f"msg{i}") for i in range(n)]


class TestBuildMessages:
    def test_first_message_is_system(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        personality = _make_personality()
        history = _make_history(2)
        messages = mgr.buildMessages(personality, history, turn_count=1)
        assert messages[0].role == "system"

    def test_history_appended_after_system(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        personality = _make_personality()
        history = _make_history(2)
        messages = mgr.buildMessages(personality, history, turn_count=1)
        # History messages appear at the end
        for h_msg in history:
            assert any(m.content == h_msg.content for m in messages)

    def test_anchor_injected_on_anchor_turn(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        personality = _make_personality()
        messages = mgr.buildMessages(personality, [], turn_count=5)
        # Should have system prompt + anchor system message
        system_messages = [m for m in messages if m.role == "system"]
        assert len(system_messages) == 2
        assert "PERSONALITY REMINDER" in system_messages[1].content

    def test_no_anchor_on_non_anchor_turn(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        personality = _make_personality()
        messages = mgr.buildMessages(personality, [], turn_count=3)
        system_messages = [m for m in messages if m.role == "system"]
        assert len(system_messages) == 1

    def test_anchor_contains_personality_summary(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        personality = _make_personality()
        messages = mgr.buildMessages(personality, [], turn_count=5)
        anchor = next(m for m in messages if "REMINDER" in m.content)
        assert "Test agent" in anchor.content or "logical" in anchor.content

    def test_system_prompt_comes_from_personality(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        personality = _make_personality()
        messages = mgr.buildMessages(personality, [], turn_count=1)
        assert "Test agent" in messages[0].content or "personality" in messages[0].content.lower()


class TestIsCheckTurn:
    def test_check_turn_at_anchor_plus_one(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        assert mgr.is_check_turn(6) is True   # anchor=5, check=6

    def test_not_check_turn_at_anchor(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        assert mgr.is_check_turn(5) is False

    def test_not_check_turn_at_random_turn(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        assert mgr.is_check_turn(3) is False
        assert mgr.is_check_turn(4) is False

    def test_check_turn_repeats(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        assert mgr.is_check_turn(11) is True   # anchor=10, check=11

    def test_no_check_turn_when_interval_zero(self):
        mgr = PersonalityConsistencyManager(anchor_interval=0)
        for t in range(1, 20):
            assert mgr.is_check_turn(t) is False

    def test_first_turn_never_check(self):
        mgr = PersonalityConsistencyManager(anchor_interval=5)
        assert mgr.is_check_turn(1) is False


class TestCheck:
    def test_returns_true_when_no_checker(self):
        mgr = PersonalityConsistencyManager()
        personality = _make_personality()
        assert mgr.check(personality, "some response") is True

    def test_returns_true_when_checker_returns_pass(self):
        mgr = PersonalityConsistencyManager()
        mgr.set_checker(lambda prompt: "PASS")
        personality = _make_personality()
        assert mgr.check(personality, "response") is True

    def test_returns_false_when_checker_returns_fail(self):
        mgr = PersonalityConsistencyManager()
        mgr.set_checker(lambda prompt: "FAIL")
        personality = _make_personality()
        assert mgr.check(personality, "response") is False

    def test_case_insensitive_pass(self):
        mgr = PersonalityConsistencyManager()
        mgr.set_checker(lambda prompt: "pass")
        assert mgr.check(_make_personality(), "response") is True

    def test_checker_exception_returns_true_fail_open(self):
        mgr = PersonalityConsistencyManager()
        def bad_checker(prompt):
            raise RuntimeError("API down")
        mgr.set_checker(bad_checker)
        assert mgr.check(_make_personality(), "response") is True


class TestFailLog:
    def test_log_fail_appends(self):
        mgr = PersonalityConsistencyManager()
        mgr.log_fail(turn_count=6, response="bad response")
        log = mgr.get_fail_log()
        assert len(log) == 1
        assert log[0]["turn"] == 6
        assert "bad response" in log[0]["response"]

    def test_get_fail_log_returns_copy(self):
        mgr = PersonalityConsistencyManager()
        mgr.log_fail(turn_count=6, response="bad")
        log1 = mgr.get_fail_log()
        log1.clear()
        log2 = mgr.get_fail_log()
        assert len(log2) == 1

    def test_multiple_failures_logged(self):
        mgr = PersonalityConsistencyManager()
        mgr.log_fail(1, "r1")
        mgr.log_fail(2, "r2")
        mgr.log_fail(3, "r3")
        assert len(mgr.get_fail_log()) == 3
