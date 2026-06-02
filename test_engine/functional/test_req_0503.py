"""
REQ-0503 — Trust Score Recalculation within 60 Seconds
Source: model_requirements.md > ScoreManager > TrustScore
Rule: New data point added → trust recalculated immediately (synchronous in V1)
Code: score_manager.py > addTrustDataPoint() calls _recalculate_trust() synchronously
Note: V1 implementation is synchronous; 60s SLA is satisfied trivially.
      Tests verify recalculation happens immediately after addTrustDataPoint.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import (
    make_score_manager, make_trust_data_point,
    assert_close, assert_equal, assert_true, run_suite
)
from uuid import uuid4

REQ_ID = "REQ-0503"


def test_trust_recalculated_immediately():
    """Happy path: getTrust updated synchronously after addTrustDataPoint."""
    # SRS REQ-0503: recalculate within 60s (V1 is synchronous)
    sm = make_score_manager()
    agent_id = uuid4()
    # Add 4 points — not enough yet
    for _ in range(4):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=4))
    before = sm.getTrust(agent_id)  # None
    # Add 5th point — triggers recalculation
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=4))
    after = sm.getTrust(agent_id)
    ok = (before is None) and (after is not None)
    return assert_equal("Trust becomes non-None immediately after 5th point", ok, True)


def test_trust_updated_after_new_point():
    """Happy path: Score changes when new data point is added (incremental update)."""
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=3))
    trust_before = sm.getTrust(agent_id)
    # Add a perfect-score point → avg rises
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    trust_after = sm.getTrust(agent_id)
    return assert_true("Score increases after adding high-star point",
                        trust_after > trust_before,
                        f"before={trust_before:.4f}, after={trust_after:.4f}")


def test_recalculation_speed():
    """Boundary: Recalculation completes in < 1 second (well under 60s SLA)."""
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=4))
    start = time.monotonic()
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    sm.getTrust(agent_id)
    elapsed = time.monotonic() - start
    return assert_true("Recalculation < 1s (SLA: 60s)", elapsed < 1.0,
                        f"elapsed={elapsed:.4f}s")


def test_noshow_reflected_immediately():
    """Edge case: Noshow penalty immediately reflected in trust score."""
    # SRS REQ-0505
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    trust_clean = sm.getTrust(agent_id)
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5, is_noshow=True))
    trust_after = sm.getTrust(agent_id)
    return assert_true("Noshow penalty reflected immediately",
                        trust_after < trust_clean,
                        f"clean={trust_clean:.4f}, after_noshow={trust_after:.4f}")


def test_hallucination_reflected_immediately():
    """Edge case: Hallucination penalty immediately reflected."""
    # SRS REQ-0506
    sm = make_score_manager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5))
    trust_clean = sm.getTrust(agent_id)
    sm.addTrustDataPoint(agent_id, make_trust_data_point(agent_id, stars=5, hallucination=True))
    trust_after = sm.getTrust(agent_id)
    return assert_true("Hallucination penalty reflected immediately",
                        trust_after < trust_clean,
                        f"clean={trust_clean:.4f}, after_halluc={trust_after:.4f}")


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Trust Recalculation Timing ===")
    tests = [
        ("immediate_on_5th", test_trust_recalculated_immediately),
        ("updated_incrementally", test_trust_updated_after_new_point),
        ("speed_under_60s", test_recalculation_speed),
        ("noshow_immediate", test_noshow_reflected_immediately),
        ("hallucination_immediate", test_hallucination_reflected_immediately),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
