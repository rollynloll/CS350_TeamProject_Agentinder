"""Shared fixtures for all model tests."""
import sys
import os

# Ensure the project root is on sys.path so `from models import ...` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from uuid import uuid4

from models.enums import PlanEnum, VisibilityEnum, IssueEnum
from models.agent.agent_profile import AgentProfile
from models.agent.agent_personality import AgentPersonality
from models.agent.agent import Agent
from models.agent.agent_service import AgentService
from models.score.score_manager import ScoreManager, TrustDataPoint
from models.rating.rating import Rating
from models.principal.principal_profile import PrincipalProfile
from models.principal.principal import Principal


# ── Reusable IDs ──────────────────────────────────────────────────────────────

@pytest.fixture
def principal_id():
    return uuid4()


@pytest.fixture
def agent_id_a():
    return uuid4()


@pytest.fixture
def agent_id_b():
    return uuid4()


# ── AgentProfile fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def profile_a(agent_id_a):
    return AgentProfile(
        agent_id=agent_id_a,
        display_name="AlphaBot",
        capability_tags=["coding", "analysis", "writing"],
        style_vector={"formality": 0.8, "creativity": 0.4},
    )


@pytest.fixture
def profile_b(agent_id_b):
    return AgentProfile(
        agent_id=agent_id_b,
        display_name="BetaBot",
        capability_tags=["coding", "testing"],
        style_vector={"formality": 0.5, "creativity": 0.9},
    )


# ── AgentPersonality fixture ──────────────────────────────────────────────────

@pytest.fixture
def personality():
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


# ── Full Agent fixture ────────────────────────────────────────────────────────

@pytest.fixture
def agent(agent_id_a, principal_id, profile_a, personality):
    return Agent(
        agent_id=agent_id_a,
        principal_id=principal_id,
        profile=profile_a,
        personality=personality,
    )


# ── AgentService / ScoreManager ───────────────────────────────────────────────

@pytest.fixture
def svc():
    return AgentService()


@pytest.fixture
def score_mgr():
    return ScoreManager()


# ── Minimal profile_data dict (for AgentService.create) ──────────────────────

def make_profile_data(name="TestBot", tags=None):
    return {
        "display_name": name,
        "capability_tags": tags or ["coding"],
        "personality": {
            "surface": {"bio": "Test agent.", "style_sliders": {"formality": 0.5}},
            "deep": {"thinking_style": "logical", "values": ["precision"], "conflict_handling": "direct"},
            "aspiration": {"collaboration_goals": ["review"], "interest_domains": ["tech"]},
        },
    }


# ── Rating helper ─────────────────────────────────────────────────────────────

def make_rating(rated_agent_id, rater_principal_id, stars=4, issues=None):
    return Rating(
        date_id=uuid4(),
        rater_principal_id=rater_principal_id,
        rated_agent_id=rated_agent_id,
        stars=stars,
        compatibility=0.8,
        issues=issues or [],
    )
