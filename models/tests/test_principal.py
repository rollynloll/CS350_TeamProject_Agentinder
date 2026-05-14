"""Tests for Principal — agent management, match, rating submission."""
import pytest
from uuid import uuid4

from models.principal.principal import Principal
from models.principal.principal_profile import PrincipalProfile
from models.agent.agent_service import AgentService
from models.agent.agent import Agent
from models.score.score_manager import ScoreManager
from models.rating.rating import Rating
from models.enums import PlanEnum, IssueEnum


def _make_principal(plan=PlanEnum.FREE):
    profile = PrincipalProfile(email="test@example.com", name="Alice", plan=plan)
    svc = AgentService()
    score_mgr = ScoreManager()
    return Principal(uuid4(), profile, svc, score_mgr), svc, score_mgr


def _profile_data(name="TestBot"):
    return {
        "display_name": name,
        "capability_tags": ["coding"],
        "personality": {
            "surface": {"bio": "Test.", "style_sliders": {"formality": 0.5}},
            "deep": {"thinking_style": "logical", "values": [], "conflict_handling": "direct"},
            "aspiration": {"collaboration_goals": [], "interest_domains": []},
        },
    }


class TestCreateAgent:
    def test_creates_agent(self):
        principal, _, _ = _make_principal()
        agent, key = principal.createAgent(_profile_data())
        assert isinstance(agent, Agent)
        assert isinstance(key, str)

    def test_agent_appears_in_agents_list(self):
        principal, _, _ = _make_principal()
        agent, _ = principal.createAgent(_profile_data())
        assert agent in principal.agents

    def test_free_plan_limit_5(self):
        principal, _, _ = _make_principal(plan=PlanEnum.FREE)
        for i in range(5):
            principal.createAgent(_profile_data(name=f"Bot{i}"))
        with pytest.raises(PermissionError):
            principal.createAgent(_profile_data(name="Bot6"))

    def test_premium_plan_allows_up_to_20(self):
        principal, _, _ = _make_principal(plan=PlanEnum.PREMIUM)
        for i in range(20):
            principal.createAgent(_profile_data(name=f"Bot{i}"))
        with pytest.raises(PermissionError):
            principal.createAgent(_profile_data(name="Bot21"))


class TestUpdateAgent:
    def test_update_returns_agent(self):
        principal, _, _ = _make_principal()
        agent, _ = principal.createAgent(_profile_data())
        updated = principal.updateAgent(agent.agent_id, {"display_name": "Renamed"})
        assert isinstance(updated, Agent)
        assert updated.getProfile().display_name == "Renamed"

    def test_update_wrong_principal_raises(self):
        # Both principals must share the same AgentService so the agent_id is found
        svc = AgentService()
        score_mgr = ScoreManager()
        p1 = Principal(uuid4(), PrincipalProfile(email="a@b.com", name="Alice"), svc, score_mgr)
        p2 = Principal(uuid4(), PrincipalProfile(email="b@b.com", name="Bob"), svc, score_mgr)
        agent, _ = p1.createAgent(_profile_data())
        with pytest.raises(PermissionError):
            p2.updateAgent(agent.agent_id, {"display_name": "Hack"})


class TestMatchApproval:
    def test_approve_match_does_not_raise(self):
        principal, _, _ = _make_principal()
        principal.approveMatch(uuid4())  # stub — should not raise

    def test_reject_match_does_not_raise(self):
        principal, _, _ = _make_principal()
        principal.rejectMatch(uuid4())  # stub — should not raise


class TestSubmitRating:
    def test_submit_rating_adds_data_point(self):
        principal, _, score_mgr = _make_principal()
        agent, _ = principal.createAgent(_profile_data())

        for _ in range(5):
            r = Rating(
                date_id=uuid4(),
                rater_principal_id=principal.principal_id,
                rated_agent_id=agent.agent_id,
                stars=5,
                compatibility=1.0,
            )
            principal.submitRating(r.date_id, r)

        trust = score_mgr.getTrust(agent.agent_id)
        assert trust is not None
        assert trust > 0.0

    def test_submit_rating_updates_agent_trust_cache(self):
        principal, _, score_mgr = _make_principal()
        agent, _ = principal.createAgent(_profile_data())

        for _ in range(5):
            r = Rating(
                date_id=uuid4(),
                rater_principal_id=principal.principal_id,
                rated_agent_id=agent.agent_id,
                stars=4,
                compatibility=0.8,
            )
            principal.submitRating(r.date_id, r)

        assert agent.getTrustScore() is not None

    def test_hallucination_issue_reflected_in_trust(self):
        principal, _, score_mgr = _make_principal()
        agent_clean, _ = principal.createAgent(_profile_data("CleanBot"))
        agent_halluc, _ = principal.createAgent(_profile_data("HallucBot"))

        # 5 clean ratings for clean bot
        for _ in range(5):
            r = Rating(
                date_id=uuid4(),
                rater_principal_id=principal.principal_id,
                rated_agent_id=agent_clean.agent_id,
                stars=4,
                compatibility=0.8,
            )
            principal.submitRating(r.date_id, r)

        # 5 ratings + 1 hallucination for halluc bot
        for _ in range(5):
            r = Rating(
                date_id=uuid4(),
                rater_principal_id=principal.principal_id,
                rated_agent_id=agent_halluc.agent_id,
                stars=4,
                compatibility=0.8,
            )
            principal.submitRating(r.date_id, r)
        r_h = Rating(
            date_id=uuid4(),
            rater_principal_id=principal.principal_id,
            rated_agent_id=agent_halluc.agent_id,
            stars=4,
            compatibility=0.8,
            issues=[IssueEnum.HALLUCINATION],
        )
        principal.submitRating(r_h.date_id, r_h)

        assert score_mgr.getTrust(agent_halluc.agent_id) < score_mgr.getTrust(agent_clean.agent_id)


class TestProfileUpdate:
    def test_update_profile(self):
        principal, _, _ = _make_principal()
        principal.updateProfile({"name": "Bob", "email": "bob@example.com"})
        assert principal.profile.name == "Bob"
        assert principal.profile.email == "bob@example.com"
