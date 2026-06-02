"""
REQ-0505/0506 — Noshow and Hallucination Penalties
Source: model_requirements.md > ScoreManager > TrustScore
REQ-0505: Noshow penalty = noshow_count * 0.20 / data_point_count
REQ-0506: Hallucination penalty = halluc_count * 0.15 / data_point_count
REQ-0507: composite clamped to [0.0, 1.0]
Code: score_manager.py lines 153-157
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import (
    make_score_manager, make_trust_data_point,
    assert_close, assert_equal, assert_true, run_suite
)
from models.score.score_manager import TrustDataPoint
from uuid import uuid4

REQ_ID = "REQ-0505"


def test_noshow_penalty_applied():
    """Happy path: Noshow reduces composite by 0.20/N per noshow."""
    # SRS REQ-0505: noshow_count * 0.20 / data_point_count
    sm = make_score_manager()
    agent_id = uuid4()
    # 5 normal points (stars=4, task_completed=True, no issues)
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=4))
    baseline = sm.getTrust(agent_id)
    # Add 1 noshow (no peer_rating)
    dp_noshow = TrustDataPoint(
        agent_id=agent_id, date_id=uuid4(),
        task_completed=False, is_noshow=True
    )
    sm.addTrustDataPoint(agent_id, dp_noshow)
    after = sm.getTrust(agent_id)
    # penalty = 0.20 / 6 ≈ 0.0333
    ok = after < baseline
    return assert_true("Noshow reduces composite", ok,
                        f"baseline={baseline:.4f}, after={after:.4f}")


def test_noshow_penalty_magnitude():
    """Boundary: Verify exact penalty value for 1 noshow in 5 points."""
    sm = make_score_manager()
    agent_id = uuid4()
    # All 5-star, all completed
    for _ in range(4):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    dp_noshow = TrustDataPoint(
        agent_id=agent_id, date_id=uuid4(),
        task_completed=False, is_noshow=True
    )
    sm.addTrustDataPoint(agent_id, dp_noshow)
    # peer_vals = [1.0,1.0,1.0,1.0] (noshow has no peer_rating)
    # peer_avg = 1.0, task_rate = 4/5 = 0.8
    # raw = 0.50*1.0 + 0.30*0.8 = 0.50+0.24 = 0.74
    # noshow penalty = 1*0.20/5 = 0.04
    # expected = 0.74 - 0.04 = 0.70
    bd = sm.getTrustBreakdown(agent_id)
    return assert_close("1 noshow in 5: expected 0.70", bd.composite, 0.70)


def test_hallucination_penalty_applied():
    """Happy path: Hallucination reduces composite by 0.15/N per event."""
    # SRS REQ-0506
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    baseline = sm.getTrust(agent_id)
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5, hallucination=True))
    after = sm.getTrust(agent_id)
    return assert_true("Hallucination reduces composite", after < baseline,
                        f"baseline={baseline:.4f}, after={after:.4f}")


def test_hallucination_penalty_magnitude():
    """Boundary: Verify exact hallucination penalty (1 event in 5 points)."""
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(4):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5, hallucination=True))
    # peer_avg = 1.0 (all 5★), task_rate = 5/5 = 1.0
    # raw = 0.50*1.0 + 0.30*1.0 = 0.80
    # halluc penalty = 1*0.15/5 = 0.03
    # expected = 0.80 - 0.03 = 0.77
    bd = sm.getTrustBreakdown(agent_id)
    return assert_close("1 hallucination in 5: expected 0.77", bd.composite, 0.77)


def test_composite_never_negative():
    """Edge case: Multiple penalties cannot push composite below 0.0."""
    # SRS REQ-0507
    sm = make_score_manager()
    agent_id = uuid4()
    # Add 5 points all with 1★ + noshow + hallucination
    for _ in range(5):
        dp = TrustDataPoint(
            agent_id=agent_id, date_id=uuid4(),
            task_completed=False, is_noshow=True, hallucination_confirmed=True
        )
        sm.addTrustDataPoint(agent_id, dp)
    trust = sm.getTrust(agent_id)
    return assert_true("Composite never negative under heavy penalties",
                        trust >= 0.0, f"trust={trust}")


def test_combined_penalties():
    """Edge case: Both noshow and hallucination penalties applied together."""
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(4):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    dp = TrustDataPoint(
        agent_id=agent_id, date_id=uuid4(),
        task_completed=False, is_noshow=True, hallucination_confirmed=True
    )
    sm.addTrustDataPoint(agent_id, dp)
    # peer_avg = 1.0 (4 ratings), task_rate = 4/5 = 0.80
    # raw = 0.50*1.0 + 0.30*0.80 = 0.74
    # noshow penalty = 0.20/5 = 0.04
    # halluc penalty = 0.15/5 = 0.03
    # expected = 0.74 - 0.04 - 0.03 = 0.67
    bd = sm.getTrustBreakdown(agent_id)
    return assert_close("Combined penalties: 0.74 - 0.04 - 0.03 = 0.67", bd.composite, 0.67)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Noshow and Hallucination Penalties ===")
    tests = [
        ("noshow_applied", test_noshow_penalty_applied),
        ("noshow_magnitude", test_noshow_penalty_magnitude),
        ("halluc_applied", test_hallucination_penalty_applied),
        ("halluc_magnitude", test_hallucination_penalty_magnitude),
        ("never_negative", test_composite_never_negative),
        ("combined_penalties", test_combined_penalties),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
