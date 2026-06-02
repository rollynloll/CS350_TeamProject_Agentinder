# TEST GENERATION EXPERIMENT
# Level: 1  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0201 — Compatibility Score Formula
# Prompt info: REQ text + full setup + expected value given (0.88)
# System: "You are a software test engineer. Write Python test code..."

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager, TrustDataPoint
from models.agent.agent_profile import AgentProfile
from models.rating.rating import Rating
from models.enums import IssueEnum
from uuid import uuid4


def test_req_0201_happy_path():
    sm = ScoreManager()

    agent_a_id = uuid4()
    agent_b_id = uuid4()

    profile_a = AgentProfile(
        agent_id=agent_a_id,
        display_name="AgentA",
        capability_tags=["coding", "research"],
        style_vector={"formality": 0.8},
        date_count=10,
    )
    profile_b = AgentProfile(
        agent_id=agent_b_id,
        display_name="AgentB",
        capability_tags=["coding", "research"],
        style_vector={"formality": 0.8},
        date_count=10,
    )

    # Add 5 trust data points to agent_b: stars=3, task_completed=True
    # peer_avg = 3/5 = 0.6, task_rate = 5/5 = 1.0
    # composite = 0.50*0.6 + 0.30*1.0 = 0.60
    for _ in range(5):
        rating = Rating(
            date_id=uuid4(),
            rater_principal_id=uuid4(),
            rated_agent_id=agent_b_id,
            stars=3,
            compatibility=0.6,
        )
        dp = TrustDataPoint(
            agent_id=agent_b_id,
            date_id=uuid4(),
            peer_rating=rating,
            task_completed=True,
        )
        sm.addTrustDataPoint(agent_b_id, dp)

    score = sm.getCompatibility(profile_a, profile_b)

    # Expected: Cap=1.0 (identical tags), Style=1.0 (identical style)
    # Trust_b = 0.60
    # total = 0.50*1.0 + 0.20*1.0 + 0.30*0.60 = 0.88
    expected = 0.88
    if abs(score.total - expected) < 0.001:
        print("PASS test_req_0201_happy_path")
    else:
        print(f"FAIL test_req_0201_happy_path: expected {expected}, got {score.total:.4f}")


test_req_0201_happy_path()
