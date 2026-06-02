"""
REQ-0206 — New Agent Trust Exclusion and Weight Re-normalization
Source: model_requirements.md > ScoreManager > CompatibilityScore
Rule: New agent (date_count < 5) → Trust excluded; Cap/Style re-normalized.
  cap_weight = 0.50 / (0.50 + 0.20) = 5/7 ≈ 0.7143
  style_weight = 0.20 / (0.50 + 0.20) = 2/7 ≈ 0.2857
Code reference: score_manager.py lines 209-213
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import (
    make_profile, make_score_manager, add_n_trust_points,
    assert_close, assert_equal, run_suite
)

REQ_ID = "REQ-0206"

_CAP_W_NEW = 0.50 / (0.50 + 0.20)   # ≈ 0.714286
_STY_W_NEW = 0.20 / (0.50 + 0.20)   # ≈ 0.285714


def test_new_agent_trust_is_zero():
    """Happy path: New agent (date_count < 5) has trust_score=0.0 in result."""
    # SRS REQ-0206: Trust excluded for new agents
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["a"], style_vector={}, date_count=0)  # new agent
    add_n_trust_points(sm, pb.agent_id, n=5, stars=5)  # trust data exists but ignored
    score = sm.getCompatibility(pa, pb)
    return assert_close("New agent: trust_score field = 0.0", score.trust_score, 0.0)


def test_new_agent_formula():
    """Happy path: Score = cap_weight*Cap + style_weight*Style with re-normalized weights."""
    # SRS REQ-0207
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a","b"], style_vector={"f": 0.6}, date_count=10)
    pb = make_profile(capability_tags=["a","b"], style_vector={"f": 0.6}, date_count=4)  # new
    score = sm.getCompatibility(pa, pb)
    # Cap = 1.0 (identical tags), Style = 1/(1+0) = 1.0
    expected = _CAP_W_NEW * 1.0 + _STY_W_NEW * 1.0
    return assert_close("New agent re-normalized weights sum to 1", score.total, expected)


def test_boundary_date_count_4():
    """Boundary: date_count=4 is still new agent (threshold is < 5)."""
    # SRS: _NEW_AGENT_THRESHOLD = 5 means date_count < 5
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    pb4 = make_profile(capability_tags=["a"], style_vector={}, date_count=4)
    pb5 = make_profile(capability_tags=["a"], style_vector={}, date_count=5)
    score4 = sm.getCompatibility(pa, pb4)
    score5 = sm.getCompatibility(pa, pb5)
    ok4 = (score4.trust_score == 0.0)
    ok5 = (score5.trust_score == 0.0)  # no trust data → getTrust returns None → 0.0
    return assert_equal("date_count=4 → new agent (trust excluded)", ok4, True)


def test_experienced_uses_full_weights():
    """Boundary: date_count=5 uses full S=0.50*Cap+0.20*Style+0.30*Trust."""
    # SRS REQ-0201
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a"], style_vector={}, date_count=10)
    pb = make_profile(capability_tags=["a"], style_vector={}, date_count=5)
    add_n_trust_points(sm, pb.agent_id, n=5, stars=4)
    score = sm.getCompatibility(pa, pb)
    trust = sm.getTrust(pb.agent_id)
    expected = 0.50 * 1.0 + 0.20 * 1.0 + 0.30 * trust
    return assert_close("Experienced agent: full weights applied", score.total, expected)


def test_new_agent_cap_style_sum_to_one():
    """Boundary: Re-normalized cap_weight + style_weight = 1.0."""
    ok = abs(_CAP_W_NEW + _STY_W_NEW - 1.0) < 1e-9
    return assert_equal("cap_weight + style_weight = 1.0 for new agent", ok, True)


def test_new_agent_zero_tags():
    """Edge case: New agent with no tags → Cap=0, only Style contributes."""
    sm = make_score_manager()
    pa = make_profile(capability_tags=["a","b"], style_vector={"f": 0.5}, date_count=10)
    pb = make_profile(capability_tags=[], style_vector={"f": 0.5}, date_count=2)
    score = sm.getCompatibility(pa, pb)
    expected = _STY_W_NEW * 1.0  # Style=1/(1+0)=1.0, Cap=0.0
    return assert_close("New agent + no tags → only style contributes", score.total, expected)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: New Agent Trust Exclusion ===")
    tests = [
        ("trust_is_zero", test_new_agent_trust_is_zero),
        ("new_agent_formula", test_new_agent_formula),
        ("date_count_4", test_boundary_date_count_4),
        ("experienced_full_weights", test_experienced_uses_full_weights),
        ("weights_sum_1", test_new_agent_cap_style_sum_to_one),
        ("new_agent_zero_tags", test_new_agent_zero_tags),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
