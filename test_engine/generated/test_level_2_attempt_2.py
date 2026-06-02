# TEST GENERATION EXPERIMENT
# Level: 2  Attempt: 2  Result: (evaluated after run)
# Target REQ: REQ-0201
# Fix from Attempt 1: "stars=0" is invalid (Rating requires 1-5).
# To achieve peer_avg=0: use TrustDataPoint(peer_rating=None) so peer_vals=[] → peer_avg=0.
# Corrected expected value derivation.

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager, TrustDataPoint
from models.agent.agent_profile import AgentProfile
from models.rating.rating import Rating
from uuid import uuid4


def _make_profile(tags, style, date_count):
    return AgentProfile(agent_id=uuid4(), display_name="Bot",
                        capability_tags=tags, style_vector=style, date_count=date_count)


def test_happy_path():
    # 5 data points with NO peer_rating (peer_rating=None) → peer_vals=[], peer_avg=0.0
    # task_completed=True for all 5 → task_rate=1.0
    # composite_b = 0.50*0.0 + 0.30*1.0 = 0.30
    # total = 0.50*1.0 + 0.20*1.0 + 0.30*0.30 = 0.79
    sm = ScoreManager()
    pa = _make_profile(["a","b"], {}, 10)
    pb = _make_profile(["a","b"], {}, 10)
    for _ in range(5):
        dp = TrustDataPoint(
            agent_id=pb.agent_id, date_id=uuid4(),
            peer_rating=None, task_completed=True
        )
        sm.addTrustDataPoint(pb.agent_id, dp)
    score = sm.getCompatibility(pa, pb)
    expected = 0.50 * 1.0 + 0.20 * 1.0 + 0.30 * 0.30
    if abs(score.total - expected) < 0.001:
        print("PASS test_happy_path")
    else:
        print(f"FAIL test_happy_path: expected={expected:.4f}, got={score.total:.4f}")


def test_boundary_no_common_tags_style_dist():
    # cap=0 (no overlap), style dist=1.0 → style=0.5
    # 5 data points stars=5, task=True → peer_avg=1.0, task_rate=1.0
    # composite_b = 0.50*1.0 + 0.30*1.0 = 0.80
    # total = 0.50*0.0 + 0.20*0.5 + 0.30*0.80 = 0.34
    sm = ScoreManager()
    pa = _make_profile(["x"], {"f": 1.0}, 10)
    pb = _make_profile(["y"], {"f": 0.0}, 10)
    for _ in range(5):
        r = Rating(date_id=uuid4(), rater_principal_id=uuid4(),
                   rated_agent_id=pb.agent_id, stars=5, compatibility=1.0)
        dp = TrustDataPoint(agent_id=pb.agent_id, date_id=uuid4(),
                             peer_rating=r, task_completed=True)
        sm.addTrustDataPoint(pb.agent_id, dp)
    score = sm.getCompatibility(pa, pb)
    expected = 0.34
    if abs(score.total - expected) < 0.001:
        print("PASS test_boundary_no_common_tags_style_dist")
    else:
        print(f"FAIL test_boundary_no_common_tags_style_dist: expected={expected}, got={score.total:.4f}")


test_happy_path()
test_boundary_no_common_tags_style_dist()
