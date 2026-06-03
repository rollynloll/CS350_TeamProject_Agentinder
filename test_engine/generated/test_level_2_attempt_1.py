# TEST GENERATION EXPERIMENT
# Level: 2  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0201 — Compatibility Score Formula
# Prompt info: REQ text + setup + expected values (happy + boundary cases given)

import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager, TrustDataPoint
from models.agent.agent_profile import AgentProfile
from models.rating.rating import Rating
from uuid import uuid4


def _make_profile(tags, style, date_count):
    return AgentProfile(
        agent_id=uuid4(), display_name="Bot",
        capability_tags=tags, style_vector=style, date_count=date_count
    )


def _add_trust(sm, agent_id, n, stars):
    for _ in range(n):
        r = Rating(date_id=uuid4(), rater_principal_id=uuid4(),
                   rated_agent_id=agent_id, stars=stars, compatibility=stars/5.0)
        dp = TrustDataPoint(agent_id=agent_id, date_id=uuid4(),
                             peer_rating=r, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)


def test_happy_path():
    # agent_a: tags=["a","b"], style={}, date_count=10
    # agent_b: tags=["a","b"], style={}, date_count=10, 5 pts stars=0→ peer_avg=0, task_rate=1.0
    # composite_b = 0.50*0 + 0.30*1.0 = 0.30
    # total = 0.50*1.0 + 0.20*1.0 + 0.30*0.30 = 0.79
    sm = ScoreManager()
    pa = _make_profile(["a","b"], {}, 10)
    pb = _make_profile(["a","b"], {}, 10)
    for _ in range(5):
        r = Rating(date_id=uuid4(), rater_principal_id=uuid4(),
                   rated_agent_id=pb.agent_id, stars=1, compatibility=0.2)
        dp = TrustDataPoint(agent_id=pb.agent_id, date_id=uuid4(),
                             peer_rating=r, task_completed=True)
        sm.addTrustDataPoint(pb.agent_id, dp)
    score = sm.getCompatibility(pa, pb)
    expected = 0.79
    if abs(score.total - expected) < 0.001:
        print("PASS test_happy_path")
    else:
        print(f"FAIL test_happy_path: expected={expected}, got={score.total:.4f}")


def test_boundary_no_common_tags_style_dist():
    # agent_a: tags=["x"], style={"f":1.0}, date_count=10
    # agent_b: tags=["y"], style={"f":0.0}, date_count=10, 5 pts stars=5, task_rate=1.0
    # Cap = 0/2 = 0.0
    # style dist = sqrt((1.0-0.0)^2) = 1.0 → style = 1/(1+1) = 0.5
    # composite_b = 0.50*(5/5) + 0.30*1.0 = 0.50+0.30 = 0.80
    # total = 0.50*0.0 + 0.20*0.5 + 0.30*0.80 = 0.34
    sm = ScoreManager()
    pa = _make_profile(["x"], {"f": 1.0}, 10)
    pb = _make_profile(["y"], {"f": 0.0}, 10)
    _add_trust(sm, pb.agent_id, 5, stars=5)
    score = sm.getCompatibility(pa, pb)
    expected = 0.34
    if abs(score.total - expected) < 0.001:
        print("PASS test_boundary_no_common_tags_style_dist")
    else:
        print(f"FAIL test_boundary_no_common_tags_style_dist: expected={expected}, got={score.total:.4f}")


test_happy_path()
test_boundary_no_common_tags_style_dist()
