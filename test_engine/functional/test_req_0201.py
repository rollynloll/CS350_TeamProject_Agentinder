"""
REQ-0201 — Compatibility Score Formula
Source: model_requirements.md > ScoreManager > Compatibility Score
Formula: S = 0.50*Cap + 0.20*Style + 0.30*Trust (experienced agent)
Weights: _W_CAP=0.50, _W_STYLE=0.20, _W_TRUST=0.30 (score_manager.py:88-94)
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import (
    make_profile, make_score_manager, add_n_trust_points,
    assert_close, assert_equal, run_suite
)

REQ_ID = "REQ-0201"


def test_cap_weight():
    """Happy path: Cap component accounts for 50% of score."""
    # SRS REQ-0201: _W_CAP = 0.50
    sm = make_score_manager()
    # A has tags {a,b,c}, B has tags {a,b,c} → Cap=1.0 (Jaccard=1)
    pa = make_profile(capability_tags=["a","b","c"], style_vector={"f":0.5}, date_count=10)
    pb = make_profile(capability_tags=["a","b","c"], style_vector={"f":0.5}, date_count=10)
    add_n_trust_points(sm, pb.agent_id, n=5, stars=5)
    score = sm.getCompatibility(pa, pb)
    # Cap=1.0, Style=1/(1+0)=1.0, Trust=computed
    # total = 0.50*1.0 + 0.20*1.0 + 0.30*trust
    trust = sm.getTrust(pb.agent_id)
    expected = 0.50 * 1.0 + 0.20 * 1.0 + 0.30 * trust
    return assert_close("Cap=1 + Style=1 gives correct weighted total", score.total, expected)


def test_jaccard_cap():
    """Boundary: Cap is computed as Jaccard similarity."""
    # SRS REQ-0202: Cap = |A∩B| / |A∪B|
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a","b","c","d"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["a","b","e","f"], style_vector={}, date_count=10)
    score = sm.getCompatibility(pa, pb)
    # intersection={a,b}=2, union={a,b,c,d,e,f}=6 → Jaccard=2/6=0.333
    expected_cap = 2/6
    return assert_close("Jaccard Cap = intersection/union", score.capability_score, expected_cap)


def test_no_common_tags():
    """Edge case: No common tags → Cap=0."""
    # SRS REQ-0202: Cap = 0 when intersection is empty
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a","b"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["c","d"], style_vector={}, date_count=10)
    score = sm.getCompatibility(pa, pb)
    return assert_close("No common tags → Cap=0", score.capability_score, 0.0)


def test_style_weight():
    """Boundary: Style uses inverse Euclidean distance."""
    # SRS REQ-0203: Style = 1/(1+dist)
    sm = make_score_manager()
    pa = make_profile(capability_tags=["x"], style_vector={"formality": 1.0}, date_count=10)
    pb = make_profile(capability_tags=["x"], style_vector={"formality": 0.0}, date_count=10)
    score = sm.getCompatibility(pa, pb)
    # dist = sqrt((1.0-0.0)^2) = 1.0 → Style = 1/(1+1) = 0.5
    return assert_close("Style with dist=1 → style_score=0.5", score.style_score, 0.5)


def test_trust_weight():
    """Happy path: Trust accounts for 30% when agent is experienced."""
    # SRS REQ-0201: _W_TRUST = 0.30 for experienced agents
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    add_n_trust_points(sm, pb.agent_id, n=5, stars=5)
    score = sm.getCompatibility(pa, pb)
    trust = sm.getTrust(pb.agent_id)
    # Cap=1, Style=1/(1+0)=1, total=0.5*1+0.2*1+0.3*trust
    expected = min(1.0, 0.50 + 0.20 + 0.30 * trust)
    return assert_close("Trust weight = 30% for experienced agent", score.total, expected)


def test_score_clamped_to_one():
    """Boundary: Total score is clamped to [0.0, 1.0]."""
    # SRS REQ-0201: max(0.0, min(1.0, total))
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    add_n_trust_points(sm, pb.agent_id, n=5, stars=5)
    score = sm.getCompatibility(pa, pb)
    ok = (0.0 <= score.total <= 1.0)
    return assert_equal("Total clamped to [0,1]", ok, True)


def test_asymmetric_score():
    """Edge case: Score is asymmetric S(A→B) ≠ S(B→A)."""
    # SRS REQ-0205: Trust of candidate differs by direction
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a","b"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["a","b"], style_vector={}, date_count=10)
    add_n_trust_points(sm, pb.agent_id, n=5, stars=5)
    # pa has no trust data → getTrust(pa)=None
    score_ab = sm.getCompatibility(pa, pb)
    score_ba = sm.getCompatibility(pb, pa)
    # trust_of_b is set; trust_of_a is None → different totals
    ok = (score_ab.total != score_ba.total)
    return assert_equal("S(A→B) ≠ S(B→A) when trust differs", ok, True)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Compatibility Score Formula ===")
    tests = [
        ("cap_weight", test_cap_weight),
        ("jaccard_cap", test_jaccard_cap),
        ("no_common_tags", test_no_common_tags),
        ("style_weight", test_style_weight),
        ("trust_weight", test_trust_weight),
        ("score_clamped", test_score_clamped_to_one),
        ("asymmetric", test_asymmetric_score),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
