"""
REQ-0609 — Relationship Key Ordering (agent_a_id < agent_b_id)
Source: model_requirements.md > ScoreManager > relationships table
Rule: Always stored as (min_uuid_str, max_uuid_str) to prevent duplicate rows.
      ScoreManager._key() enforces this ordering.
Code: score_manager.py lines 113-115
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_score_manager, assert_equal, assert_true, run_suite
from models.enums import TierEnum
from uuid import uuid4

REQ_ID = "REQ-0609"


def test_key_ordering():
    """Happy path: _key() returns (smaller, larger) regardless of argument order."""
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    key_ab = sm._key(a, b)
    key_ba = sm._key(b, a)
    return assert_equal("_key(a,b) == _key(b,a)", key_ab, key_ba)


def test_key_is_sorted():
    """Boundary: key[0] < key[1] by string comparison."""
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    key = sm._key(a, b)
    return assert_true("key[0] <= key[1] in string order",
                        str(key[0]) <= str(key[1]),
                        f"key={key}")


def test_relationship_deduplication():
    """Happy path: recordSuccessfulDate(a,b) and (b,a) affect same record."""
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.recordSuccessfulDate(b, a, rating=4.0)
    rel = sm._get_or_create_rel(a, b)
    return assert_equal("Two directional calls → successful_dates=2", rel.successful_dates, 2)


def test_upgrade_symmetric():
    """Boundary: checkUpgrade(a,b) and checkUpgrade(b,a) see same tier."""
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.checkUpgrade(a, b)
    tier_ab = sm.getRelationship(a, b)
    tier_ba = sm.getRelationship(b, a)
    return assert_equal("getRelationship is symmetric", tier_ab, tier_ba)


def test_freeze_is_symmetric():
    """Edge case: freeze(a,b) also freezes (b,a) direction."""
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.freeze(a, b)
    result_ba = sm.checkUpgrade(b, a)
    return assert_equal("freeze(a,b) blocks checkUpgrade(b,a)", result_ba, None)


def test_default_tier_is_stranger():
    """Boundary: First getRelationship call returns STRANGER."""
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    tier = sm.getRelationship(a, b)
    return assert_equal("Default tier = STRANGER", tier, TierEnum.STRANGER)


def test_multiple_pairs_independent():
    """Edge case: Two unrelated pairs have independent records."""
    sm = make_score_manager()
    a1, b1 = uuid4(), uuid4()
    a2, b2 = uuid4(), uuid4()
    sm.recordSuccessfulDate(a1, b1, rating=4.0)
    sm.checkUpgrade(a1, b1)
    tier_pair1 = sm.getRelationship(a1, b1)
    tier_pair2 = sm.getRelationship(a2, b2)
    ok = (tier_pair1 == TierEnum.ACQUAINTANCE and tier_pair2 == TierEnum.STRANGER)
    return assert_equal("Independent pairs have independent tiers", ok, True)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Relationship Key Ordering ===")
    tests = [
        ("key_ordering", test_key_ordering),
        ("key_sorted", test_key_is_sorted),
        ("deduplication", test_relationship_deduplication),
        ("upgrade_symmetric", test_upgrade_symmetric),
        ("freeze_symmetric", test_freeze_is_symmetric),
        ("default_stranger", test_default_tier_is_stranger),
        ("independent_pairs", test_multiple_pairs_independent),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
