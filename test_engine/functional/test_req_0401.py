"""
REQ-0401/0402/0403 — Relationship Tier Upgrade Conditions
Source: model_requirements.md > ScoreManager > TierEnum
REQ-0401: STRANGER → ACQUAINTANCE: successful_dates >= 1
REQ-0402: ACQUAINTANCE → COLLEAGUE: successful_dates >= 3
REQ-0403: COLLEAGUE → TRUSTED_PARTNER: successful_dates >= 10 AND avg_rating >= 4.0
REQ-0404: Freeze prevents upgrade; unfreeze re-enables
REQ-0406: One step at a time (no skipping tiers)
Code: score_manager.py lines 261-286
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_score_manager, assert_equal, assert_true, run_suite
from models.enums import TierEnum
from uuid import uuid4

REQ_ID = "REQ-0401"


def _make_pair():
    return uuid4(), uuid4()


def test_stranger_to_acquaintance():
    """Happy path: 1 successful date upgrades STRANGER → ACQUAINTANCE."""
    # SRS REQ-0401
    sm = make_score_manager()
    a, b = _make_pair()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    result = sm.checkUpgrade(a, b)
    return assert_equal("1 date → ACQUAINTANCE", result, TierEnum.ACQUAINTANCE)


def test_stranger_zero_dates_no_upgrade():
    """Boundary: 0 dates → no upgrade from STRANGER."""
    sm = make_score_manager()
    a, b = _make_pair()
    result = sm.checkUpgrade(a, b)
    return assert_equal("0 dates → no upgrade", result, None)


def test_acquaintance_to_colleague():
    """Happy path: 3 successful dates upgrades ACQUAINTANCE → COLLEAGUE."""
    # SRS REQ-0402
    sm = make_score_manager()
    a, b = _make_pair()
    for _ in range(3):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.checkUpgrade(a, b)  # STRANGER → ACQUAINTANCE
    result = sm.checkUpgrade(a, b)  # ACQUAINTANCE → COLLEAGUE
    return assert_equal("3 dates → COLLEAGUE", result, TierEnum.COLLEAGUE)


def test_colleague_to_trusted_partner():
    """Happy path: 10 dates + avg_rating >= 4.0 → TRUSTED_PARTNER."""
    # SRS REQ-0403
    sm = make_score_manager()
    a, b = _make_pair()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    result = sm.checkUpgrade(a, b)  # → TRUSTED_PARTNER
    return assert_equal("10 dates + rating>=4 → TRUSTED_PARTNER", result, TierEnum.TRUSTED_PARTNER)


def test_trusted_partner_requires_rating():
    """Boundary: 10 dates but avg_rating < 4.0 → no upgrade from COLLEAGUE."""
    # SRS REQ-0403: AND condition
    sm = make_score_manager()
    a, b = _make_pair()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=3.5)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    result = sm.checkUpgrade(a, b)  # should NOT upgrade
    return assert_equal("10 dates + rating<4 → no upgrade from COLLEAGUE", result, None)


def test_freeze_blocks_upgrade():
    """Edge case: Frozen relationship → checkUpgrade returns None."""
    # SRS REQ-0404
    sm = make_score_manager()
    a, b = _make_pair()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.freeze(a, b)
    result = sm.checkUpgrade(a, b)
    return assert_equal("Frozen → no upgrade", result, None)


def test_unfreeze_allows_upgrade():
    """Edge case: Unfreezing restores upgrade eligibility."""
    # SRS REQ-0405
    sm = make_score_manager()
    a, b = _make_pair()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.freeze(a, b)
    sm.unfreeze(a, b)
    result = sm.checkUpgrade(a, b)
    return assert_equal("After unfreeze → upgrade works", result, TierEnum.ACQUAINTANCE)


def test_one_step_at_a_time():
    """Edge case: 10 dates does NOT jump from STRANGER to TRUSTED_PARTNER in one call."""
    # SRS REQ-0406
    sm = make_score_manager()
    a, b = _make_pair()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=5.0)
    result = sm.checkUpgrade(a, b)  # first call upgrades one step
    return assert_equal("One step at a time: first upgrade → ACQUAINTANCE", result, TierEnum.ACQUAINTANCE)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Tier Upgrade Conditions ===")
    tests = [
        ("stranger_to_acquaintance", test_stranger_to_acquaintance),
        ("zero_dates_no_upgrade", test_stranger_zero_dates_no_upgrade),
        ("acquaintance_to_colleague", test_acquaintance_to_colleague),
        ("colleague_to_trusted_partner", test_colleague_to_trusted_partner),
        ("trusted_partner_requires_rating", test_trusted_partner_requires_rating),
        ("freeze_blocks_upgrade", test_freeze_blocks_upgrade),
        ("unfreeze_allows_upgrade", test_unfreeze_allows_upgrade),
        ("one_step_at_a_time", test_one_step_at_a_time),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
