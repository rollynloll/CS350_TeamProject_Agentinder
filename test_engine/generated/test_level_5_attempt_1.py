# TEST GENERATION EXPERIMENT
# Level: 5  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0501 + REQ-0502 — Trust Score Formula + Minimum Data Points
# Prompt info: REQ text only; model must derive composite formula and None-return rule
# FAILURE MODE RISK: Forgetting stars/5.0 scaling; wrong weight; missing None case

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager, TrustDataPoint
from models.agent.agent_profile import AgentProfile
from models.rating.rating import Rating
from uuid import uuid4


def _make_dp(agent_id, stars, task_completed=True):
    r = Rating(
        date_id=uuid4(), rater_principal_id=uuid4(), rated_agent_id=agent_id,
        stars=stars, compatibility=stars / 5.0
    )
    return TrustDataPoint(
        agent_id=agent_id, date_id=uuid4(),
        peer_rating=r, task_completed=task_completed
    )


def test_happy_path_correct_composite():
    # 5 data points: stars=4, task_completed=True
    # peer_avg = 4/5 = 0.80, task_rate = 5/5 = 1.0
    # composite = 0.50*0.80 + 0.30*1.0 = 0.40 + 0.30 = 0.70
    sm = ScoreManager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, _make_dp(agent_id, stars=4))
    trust = sm.getTrust(agent_id)
    expected = 0.50 * (4/5) + 0.30 * 1.0
    if trust is not None and abs(trust - expected) < 0.001:
        print("PASS test_happy_path_correct_composite")
    else:
        print(f"FAIL test_happy_path_correct_composite: expected={expected:.4f}, got={trust}")


def test_boundary_4_points_returns_none():
    # REQ-0502: 4 data points → None
    sm = ScoreManager()
    agent_id = uuid4()
    for _ in range(4):
        sm.addTrustDataPoint(agent_id, _make_dp(agent_id, stars=5))
    trust = sm.getTrust(agent_id)
    if trust is None:
        print("PASS test_boundary_4_points_returns_none")
    else:
        print(f"FAIL test_boundary_4_points_returns_none: expected None, got {trust}")


def test_boundary_5_points_returns_float():
    # REQ-0502: exactly 5 data points → composite returned
    sm = ScoreManager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, _make_dp(agent_id, stars=5))
    trust = sm.getTrust(agent_id)
    if trust is not None:
        print(f"PASS test_boundary_5_points_returns_float (trust={trust:.4f})")
    else:
        print("FAIL test_boundary_5_points_returns_float: expected float, got None")


def test_exception_mixed_task_completion():
    # 5 points: 3 completed, 2 not; all stars=5
    # peer_avg = 1.0, task_rate = 3/5 = 0.60
    # composite = 0.50*1.0 + 0.30*0.60 = 0.68
    sm = ScoreManager()
    agent_id = uuid4()
    for i in range(5):
        sm.addTrustDataPoint(agent_id, _make_dp(agent_id, stars=5, task_completed=(i < 3)))
    trust = sm.getTrust(agent_id)
    expected = 0.50 * 1.0 + 0.30 * (3/5)
    if trust is not None and abs(trust - expected) < 0.001:
        print("PASS test_exception_mixed_task_completion")
    else:
        print(f"FAIL test_exception_mixed_task_completion: expected={expected:.4f}, got={trust}")


test_happy_path_correct_composite()
test_boundary_4_points_returns_none()
test_boundary_5_points_returns_float()
test_exception_mixed_task_completion()
