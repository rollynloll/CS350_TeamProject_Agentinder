"""Tests for DateSession, DateResult, IcebreakerGenerator, and Match helpers."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from models import (
    Agent, AgentProfile, AgentPersonality, AgentService,
    Principal, PrincipalProfile,
    ScoreManager, Rating, Match, Message,
)
from models.enums import PlanEnum, VisibilityEnum
from models.date import DateSession, DateResult, DateStatus, DateOutcome, IcebreakerGenerator


# ── helpers ───────────────────────────────────────────────────────────────────

def _new_env():
    return AgentService(), ScoreManager()


def _new_principal(svc, smgr, name="Alice"):
    profile = PrincipalProfile(email=f"{name.lower()}@test.com", name=name, plan=PlanEnum.FREE)
    return Principal(uuid4(), profile, svc, smgr)


def _profile_data(name="Bot", tags=None):
    return {
        "display_name": name,
        "visibility": VisibilityEnum.PUBLIC,
        "capability_tags": tags or ["coding"],
        "personality": {
            "surface": {
                "bio": f"{name}: test agent.",
                "style_sliders": {"formality": 0.5, "creativity": 0.5},
            },
            "deep": {
                "thinking_style": "logical",
                "values": ["accuracy"],
                "conflict_handling": "direct",
            },
            "aspiration": {
                "collaboration_goals": ["review"],
                "interest_domains": ["tech"],
            },
        },
    }


def _make_mock_llm(response: str = "test response"):
    mock = MagicMock()
    mock.generate.return_value = response
    return mock


def _make_session(
    agent_a, agent_b, score_manager,
    skip_trust_check=True, topic=None,
    min_trust_threshold=0.3,
    max_turns_per_agent=4,
) -> DateSession:
    return DateSession(
        agent_a=agent_a,
        agent_b=agent_b,
        match_id=uuid4(),
        skip_trust_check=skip_trust_check,
        topic=topic,
        score_manager=score_manager,
        min_trust_threshold=min_trust_threshold,
        max_turns_per_agent=max_turns_per_agent,
    )


# ── Match helpers ─────────────────────────────────────────────────────────────

class TestMatchHelpers:
    def test_has_agent_returns_true_for_both(self):
        a, b = uuid4(), uuid4()
        m = Match(agent_a_id=a, agent_b_id=b)
        assert m.has_agent(a) is True
        assert m.has_agent(b) is True

    def test_has_agent_returns_false_for_other(self):
        m = Match(agent_a_id=uuid4(), agent_b_id=uuid4())
        assert m.has_agent(uuid4()) is False

    def test_other_agent_id_from_a(self):
        a, b = uuid4(), uuid4()
        m = Match(agent_a_id=a, agent_b_id=b)
        assert m.other_agent_id(a) == b

    def test_other_agent_id_from_b(self):
        a, b = uuid4(), uuid4()
        m = Match(agent_a_id=a, agent_b_id=b)
        assert m.other_agent_id(b) == a

    def test_other_agent_id_raises_for_unknown(self):
        m = Match(agent_a_id=uuid4(), agent_b_id=uuid4())
        with pytest.raises(ValueError):
            m.other_agent_id(uuid4())

    def test_unmatched_at_default_is_none(self):
        m = Match(agent_a_id=uuid4(), agent_b_id=uuid4())
        assert m.unmatched_at is None

    def test_unmatched_at_can_be_set(self):
        now = datetime.now(timezone.utc)
        m = Match(agent_a_id=uuid4(), agent_b_id=uuid4(), unmatched_at=now)
        assert m.unmatched_at == now


# ── IcebreakerGenerator ───────────────────────────────────────────────────────

class TestIcebreakerGenerator:
    def _make_agent(self, tags):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data("Bot", tags=tags))
        return agent

    def test_common_tags_used_in_topic(self):
        a = self._make_agent(["coding", "analysis"])
        b = self._make_agent(["coding", "design"])
        topic = IcebreakerGenerator().generate(a, b)
        assert "coding" in topic

    def test_no_common_tags_falls_back_to_union(self):
        a = self._make_agent(["coding"])
        b = self._make_agent(["design"])
        topic = IcebreakerGenerator().generate(a, b)
        assert isinstance(topic, str) and len(topic) > 0

    def test_no_tags_returns_generic_prompt(self):
        a = self._make_agent([])
        b = self._make_agent([])
        topic = IcebreakerGenerator().generate(a, b)
        assert isinstance(topic, str) and len(topic) > 0


# ── DateSession: handshake ────────────────────────────────────────────────────

class TestHandshake:
    def test_skip_trust_check_always_passes(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        session = _make_session(a, b, smgr, skip_trust_check=True)
        # No LLM, so date() will fail — just test handshake result via status
        a.setLLMClient(_make_mock_llm())
        b.setLLMClient(_make_mock_llm())
        result = session.run()
        assert result.status != DateStatus.CANCELLED

    def test_new_agent_none_trust_passes_threshold(self):
        """getTrust() == None인 신규 에이전트는 임계값 체크를 면제한다."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        # trust is None for both (new agents)
        assert smgr.getTrust(a.agent_id) is None
        assert smgr.getTrust(b.agent_id) is None
        a.setLLMClient(_make_mock_llm())
        b.setLLMClient(_make_mock_llm())
        session = _make_session(a, b, smgr, skip_trust_check=False, min_trust_threshold=0.5)
        result = session.run()
        assert result.status != DateStatus.CANCELLED

    def test_low_trust_score_cancels(self):
        """신뢰 점수가 임계값 미만이면 CANCELLED."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))

        # 낮은 별점으로 trust 점수 채우기
        for agent in [a, b]:
            for _ in range(5):
                r = Rating(
                    date_id=uuid4(),
                    rater_principal_id=p.principal_id,
                    rated_agent_id=agent.agent_id,
                    stars=1,
                    compatibility=0.1,
                )
                p.submitRating(r.date_id, r)

        session = _make_session(a, b, smgr, skip_trust_check=False, min_trust_threshold=0.9)
        result = session.run()
        assert result.status == DateStatus.CANCELLED
        assert result.transcript == []
        assert result.ratings == []

    def test_sufficient_trust_proceeds(self):
        """신뢰 점수가 임계값 이상이면 IN_PROGRESS로 진행."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        for agent in [a, b]:
            for _ in range(5):
                r = Rating(
                    date_id=uuid4(),
                    rater_principal_id=p.principal_id,
                    rated_agent_id=agent.agent_id,
                    stars=5,
                    compatibility=1.0,
                )
                p.submitRating(r.date_id, r)
        a.setLLMClient(_make_mock_llm())
        b.setLLMClient(_make_mock_llm())
        session = _make_session(a, b, smgr, skip_trust_check=False, min_trust_threshold=0.1)
        result = session.run()
        assert result.status != DateStatus.CANCELLED


# ── DateSession: date() ───────────────────────────────────────────────────────

class TestDateStep:
    def test_transcript_has_messages(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        a.setLLMClient(_make_mock_llm("Hi from A"))
        b.setLLMClient(_make_mock_llm("Hi from B"))
        session = _make_session(a, b, smgr, max_turns_per_agent=2)
        result = session.run()
        assert len(result.transcript) == 4  # 2 agents × 2 turns

    def test_no_llm_client_sets_noshow(self):
        """LLMClient 없는 에이전트가 있으면 NO_SHOW 처리."""
        from models.agent.agent_profile import AgentProfile
        from models.agent.agent_personality import AgentPersonality
        from models.agent.agent import Agent as RawAgent
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        a.setLLMClient(_make_mock_llm())
        # agent_b은 llm_client=None으로 직접 생성
        b_id = uuid4()
        b = RawAgent(
            agent_id=b_id,
            principal_id=p.principal_id,
            profile=AgentProfile(agent_id=b_id, display_name="B"),
            personality=AgentPersonality(),
            llm_client=None,
        )
        session = _make_session(a, b, smgr)
        result = session.run()
        assert result.status == DateStatus.NO_SHOW

    def test_topic_provided_skips_icebreaker(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        mock_a = _make_mock_llm("response A")
        a.setLLMClient(mock_a)
        b.setLLMClient(_make_mock_llm("response B"))
        session = _make_session(a, b, smgr, topic="Specific project topic", max_turns_per_agent=1)
        session.run()
        # First call to agent_a's LLM should have the topic in history
        first_call_history = mock_a.generate.call_args_list[0][1]["history"]
        topic_in_history = any("Specific project topic" in m.content for m in first_call_history)
        assert topic_in_history

    def test_none_topic_uses_icebreaker(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A", tags=["coding"]))
        b, _ = p.createAgent(_profile_data("B", tags=["coding"]))
        mock_a = _make_mock_llm("response A")
        a.setLLMClient(mock_a)
        b.setLLMClient(_make_mock_llm("response B"))
        session = _make_session(a, b, smgr, topic=None, max_turns_per_agent=1)
        session.run()
        first_call_history = mock_a.generate.call_args_list[0][1]["history"]
        # IcebreakerGenerator should have produced a topic mentioning "coding"
        assert any("coding" in m.content for m in first_call_history)

    def test_imbalance_detected(self):
        """한 에이전트가 80% 이상 전송하면 is_imbalanced=True."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        # agent_b LLM always raises so only agent_a responds before NO_SHOW
        a.setLLMClient(_make_mock_llm("ok"))
        bad_llm = MagicMock()
        bad_llm.generate.side_effect = Exception("timeout")
        b.setLLMClient(bad_llm)
        # agent_a gets 1 turn in, agent_b fails → 1/1 = 100% for a
        session = _make_session(a, b, smgr, max_turns_per_agent=2)
        result = session.run()
        assert result.status == DateStatus.NO_SHOW
        assert result.is_imbalanced is True


# ── DateSession: rating() ─────────────────────────────────────────────────────

class TestRatingStep:
    def _run_full(self, turns=4, skip_trust_check=True, topic="topic"):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A", tags=["coding"]))
        b, _ = p.createAgent(_profile_data("B", tags=["coding"]))
        a.setLLMClient(_make_mock_llm("msg"))
        b.setLLMClient(_make_mock_llm("msg"))
        session = _make_session(
            a, b, smgr,
            skip_trust_check=skip_trust_check,
            topic=topic,
            max_turns_per_agent=turns // 2,
        )
        return session.run(), a, b, smgr

    def test_completed_status_after_full_run(self):
        result, *_ = self._run_full()
        assert result.status == DateStatus.COMPLETED

    def test_async_produces_two_ratings(self):
        """비동기 매칭은 양쪽 각자 Rating을 생성한다."""
        result, a, b, _ = self._run_full(skip_trust_check=True)
        assert len(result.ratings) == 2
        rated_ids = {r.rated_agent_id for r in result.ratings}
        assert a.agent_id in rated_ids
        assert b.agent_id in rated_ids

    def test_sync_produces_one_rating(self):
        """동기 매칭은 agent_a의 principal이 agent_b를 평가하는 Rating 1개."""
        result, a, b, _ = self._run_full(skip_trust_check=False)
        assert len(result.ratings) == 1
        r = result.ratings[0]
        assert r.rated_agent_id == b.agent_id
        assert r.rater_principal_id == a.principal_id

    def test_successful_outcome_high_completion(self):
        """전체 턴의 80% 이상 완주하면 SUCCESSFUL."""
        result, *_ = self._run_full(turns=4)
        # 4 turns total, max=4 → 100% ≥ 80%
        assert result.outcome == DateOutcome.SUCCESSFUL

    def test_rating_stars_match_outcome(self):
        result, *_ = self._run_full(turns=4)
        assert result.outcome == DateOutcome.SUCCESSFUL
        for r in result.ratings:
            assert r.stars == 5

    def test_trust_delta_is_float(self):
        result, *_ = self._run_full()
        assert isinstance(result.trust_delta, float)

    def test_trust_data_points_added_to_score_manager(self):
        """run() 후 양쪽 에이전트에 TrustDataPoint가 추가된다."""
        result, a, b, smgr = self._run_full()
        assert len(smgr._trust_data.get(a.agent_id, [])) > 0
        assert len(smgr._trust_data.get(b.agent_id, [])) > 0

    def test_noshow_trust_data_added(self):
        """NO_SHOW 종료 시 양쪽 모두 noshow 데이터 포인트가 추가된다."""
        from models.agent.agent_profile import AgentProfile
        from models.agent.agent_personality import AgentPersonality
        from models.agent.agent import Agent as RawAgent
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        a.setLLMClient(_make_mock_llm())
        # agent_b은 llm_client=None으로 직접 생성 → NO_SHOW
        b_id = uuid4()
        b = RawAgent(
            agent_id=b_id,
            principal_id=p.principal_id,
            profile=AgentProfile(agent_id=b_id, display_name="B"),
            personality=AgentPersonality(),
            llm_client=None,
        )
        session = _make_session(a, b, smgr)
        result = session.run()
        assert result.status == DateStatus.NO_SHOW
        # both agents get noshow data points
        a_dps = smgr._trust_data.get(a.agent_id, [])
        b_dps = smgr._trust_data.get(b.agent_id, [])
        assert any(dp.is_noshow for dp in a_dps)
        assert any(dp.is_noshow for dp in b_dps)

    def test_date_id_stable_across_run(self):
        """DateSession.date_id는 run() 전후 동일하게 유지된다."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        a.setLLMClient(_make_mock_llm())
        b.setLLMClient(_make_mock_llm())
        session = _make_session(a, b, smgr)
        did_before = session.date_id
        result = session.run()
        assert session.date_id == did_before
        # ratings reference the same date_id
        for r in result.ratings:
            assert r.date_id == did_before


# ── DateSession: outcome thresholds ──────────────────────────────────────────

class TestOutcomeThresholds:
    def _session_with_turns(self, turns_per_agent, skip_trust_check=True):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        a.setLLMClient(_make_mock_llm("ok"))
        b.setLLMClient(_make_mock_llm("ok"))
        session = _make_session(
            a, b, smgr,
            skip_trust_check=skip_trust_check,
            topic="topic",
            max_turns_per_agent=turns_per_agent,
        )
        return session.run()

    def test_full_completion_is_successful(self):
        result = self._session_with_turns(4)
        assert result.outcome == DateOutcome.SUCCESSFUL

    def test_partial_completion_is_neutral(self):
        """_determine_outcome에서 40%~80% 구간은 NEUTRAL."""
        # max = 4*2 = 8, neutral if len in [3,6]
        # We need to craft a partial transcript.
        # The simplest way: use max_turns_per_agent=10, run truncated.
        # Since we can't easily truncate mid-run, test _determine_outcome directly.
        from models.date.date_session import DateSession as DS
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        session = DS(
            agent_a=a,
            agent_b=b,
            match_id=uuid4(),
            skip_trust_check=True,
            topic="t",
            score_manager=smgr,
            max_turns_per_agent=10,
        )
        # max_possible = 20, 40% = 8, 80% = 16
        outcome, stars = session._determine_outcome(8)
        assert outcome == DateOutcome.NEUTRAL
        assert stars == 3

    def test_minimal_completion_is_unsuccessful(self):
        from models.date.date_session import DateSession as DS
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        session = DS(
            agent_a=a,
            agent_b=b,
            match_id=uuid4(),
            skip_trust_check=True,
            topic="t",
            score_manager=smgr,
            max_turns_per_agent=10,
        )
        outcome, stars = session._determine_outcome(3)  # < 40% of 20
        assert outcome == DateOutcome.UNSUCCESSFUL
        assert stars == 1
