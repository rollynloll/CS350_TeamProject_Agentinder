"""
REQ-0501 — Trust Score Weight Composition
Source: model_requirements.md > ScoreManager > TrustScore
Formula: composite = 0.50*peer_ratings_avg + 0.30*task_completion_rate + 0.20*other
V1: other=0.0, so composite = 0.50*peer_avg + 0.30*task_rate
Code: score_manager.py lines 88-89, 143-157
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import (
    make_score_manager, make_trust_data_point,
    assert_close, assert_equal, run_suite
)
from uuid import uuid4

REQ_ID = "REQ-0501"


def test_peer_weight_50_percent():
    """Happy path: peer_ratings_avg contributes 50% to composite."""
    # SRS REQ-0501: _W_PEER = 0.50
    sm = make_score_manager()
    agent_id = uuid4()
    # 5 data points, all stars=5 (peer_avg=1.0), all task_completed=True (task_rate=1.0)
    for _ in range(5):
        dp = make_trust_data_point(agent_id, stars=5, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)
    bd = sm.getTrustBreakdown(agent_id)
    # composite = 0.50*1.0 + 0.30*1.0 = 0.80
    return assert_close("All 5★ + all complete → composite=0.80", bd.composite, 0.80)


def test_task_weight_30_percent():
    """Happy path: task_completion_rate contributes 30%."""
    # SRS REQ-0501: _W_TASK = 0.30
    sm = make_score_manager()
    agent_id = uuid4()
    # 10 data points: peer_avg = some value, task_rate = 0.5
    for i in range(10):
        dp = make_trust_data_point(
            agent_id, stars=4, task_completed=(i < 5)
        )
        sm.addTrustDataPoint(agent_id, dp)
    bd = sm.getTrustBreakdown(agent_id)
    expected = 0.50 * (4/5) + 0.30 * 0.5
    return assert_close("peer_avg=0.8, task_rate=0.5 → formula verified", bd.composite, expected)


def test_peer_avg_calculation():
    """Boundary: peer_ratings_avg = mean(stars/5.0) across rated points."""
    # SRS REQ-0501
    sm = make_score_manager()
    agent_id = uuid4()
    stars_list = [5, 4, 3, 4, 5]
    for stars in stars_list:
        dp = make_trust_data_point(agent_id, stars=stars, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)
    bd = sm.getTrustBreakdown(agent_id)
    expected_avg = sum(s/5.0 for s in stars_list) / len(stars_list)
    return assert_close("peer_ratings_avg = mean(stars/5)", bd.peer_ratings_avg, expected_avg)


def test_task_completion_rate():
    """Boundary: task_completion_rate = completed/total."""
    sm = make_score_manager()
    agent_id = uuid4()
    # 7 completed, 3 not
    for i in range(10):
        dp = make_trust_data_point(agent_id, stars=3, task_completed=(i < 7))
        sm.addTrustDataPoint(agent_id, dp)
    bd = sm.getTrustBreakdown(agent_id)
    return assert_close("task_completion_rate = 7/10 = 0.7", bd.task_completion_rate, 0.7)


def test_composite_clamped():
    """Boundary: composite clamped to [0.0, 1.0] — REQ-0507."""
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        dp = make_trust_data_point(agent_id, stars=5, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)
    trust = sm.getTrust(agent_id)
    return assert_equal("composite in [0,1]", 0.0 <= trust <= 1.0, True)


def test_new_agent_no_trust():
    """Edge case: Fewer than 5 data points → getTrust returns None."""
    # SRS REQ-0502
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(4):
        dp = make_trust_data_point(agent_id, stars=5, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)
    return assert_equal("4 data points → getTrust returns None", sm.getTrust(agent_id), None)


def test_exactly_5_points_gives_trust():
    """Boundary: Exactly 5 data points → composite calculated."""
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        dp = make_trust_data_point(agent_id, stars=4, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)
    trust = sm.getTrust(agent_id)
    return assert_equal("5 data points → trust not None", trust is not None, True)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Trust Score Weight Composition ===")
    tests = [
        ("peer_weight_50pct", test_peer_weight_50_percent),
        ("task_weight_30pct", test_task_weight_30_percent),
        ("peer_avg_calc", test_peer_avg_calculation),
        ("task_rate", test_task_completion_rate),
        ("composite_clamped", test_composite_clamped),
        ("new_agent_no_trust", test_new_agent_no_trust),
        ("exactly_5_gives_trust", test_exactly_5_points_gives_trust),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
