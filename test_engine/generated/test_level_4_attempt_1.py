# TEST GENERATION EXPERIMENT
# Level: 4  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0401 — Relationship Tier Upgrade Conditions
# Prompt info: REQ text only (no setup code, no expected values given)
# Model must derive: threshold values (1/3/10 dates, 4.0 rating), TierEnum names, freeze behavior

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager
from models.enums import TierEnum
from uuid import uuid4


def test_happy_path_stranger_to_acquaintance():
    # REQ-0401: 1 successful date → STRANGER upgrades to ACQUAINTANCE
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    result = sm.checkUpgrade(a, b)
    if result == TierEnum.ACQUAINTANCE:
        print("PASS test_happy_path_stranger_to_acquaintance")
    else:
        print(f"FAIL test_happy_path_stranger_to_acquaintance: expected ACQUAINTANCE, got {result}")


def test_boundary_exact_threshold():
    # REQ-0402: exactly 3 dates → COLLEAGUE; REQ-0401 requires exactly 1 for ACQUAINTANCE
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    for _ in range(3):
        sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    result = sm.checkUpgrade(a, b)  # → COLLEAGUE
    if result == TierEnum.COLLEAGUE:
        print("PASS test_boundary_exact_threshold_colleague")
    else:
        print(f"FAIL test_boundary_exact_threshold_colleague: expected COLLEAGUE, got {result}")


def test_boundary_trusted_partner_requires_rating():
    # REQ-0403: 10 dates + avg_rating>=4.0 → TRUSTED_PARTNER
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    result = sm.checkUpgrade(a, b)  # → TRUSTED_PARTNER
    if result == TierEnum.TRUSTED_PARTNER:
        print("PASS test_boundary_trusted_partner_requires_rating")
    else:
        print(f"FAIL test_boundary_trusted_partner_requires_rating: expected TRUSTED_PARTNER, got {result}")


def test_exception_freeze_blocks_upgrade():
    # REQ-0404: freeze prevents upgrade
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    sm.recordSuccessfulDate(a, b, rating=4.0)
    sm.freeze(a, b)
    result = sm.checkUpgrade(a, b)
    if result is None:
        print("PASS test_exception_freeze_blocks_upgrade")
    else:
        print(f"FAIL test_exception_freeze_blocks_upgrade: expected None, got {result}")


def test_exception_zero_dates_no_upgrade():
    # No dates → stays STRANGER
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    result = sm.checkUpgrade(a, b)
    if result is None:
        print("PASS test_exception_zero_dates_no_upgrade")
    else:
        print(f"FAIL test_exception_zero_dates_no_upgrade: expected None, got {result}")


test_happy_path_stranger_to_acquaintance()
test_boundary_exact_threshold()
test_boundary_trusted_partner_requires_rating()
test_exception_freeze_blocks_upgrade()
test_exception_zero_dates_no_upgrade()
