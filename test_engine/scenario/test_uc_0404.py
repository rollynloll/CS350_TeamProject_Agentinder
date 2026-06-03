"""
UC-0404 — Relationship Freeze and Unfreeze
Goal: Trust score drops → relationship frozen (no downgrade) → trust recovers → manually unfrozen
Actor: ScoreManager, Backend (trust monitoring — stubbed)
Pre-condition: Agents A and B have an established relationship (ACQUAINTANCE or higher)
SRS Source: model_requirements.md §ScoreManager §freeze/unfreeze, §relationships table
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_score_manager, make_trust_data_point
from models.enums import TierEnum
from uuid import uuid4

UC_ID = "UC-0404"


def _reach_tier(sm, a, b, tier: TierEnum):
    """Helper: advance relationship to target tier."""
    if tier == TierEnum.STRANGER:
        return
    sm.recordSuccessfulDate(a, b, rating=5.0)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    if tier == TierEnum.ACQUAINTANCE:
        return
    sm.recordSuccessfulDate(a, b, rating=5.0)
    sm.recordSuccessfulDate(a, b, rating=5.0)
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    if tier == TierEnum.COLLEAGUE:
        return
    for _ in range(7):
        sm.recordSuccessfulDate(a, b, rating=5.0)
    sm.checkUpgrade(a, b)  # → TRUSTED_PARTNER


def test_freeze_prevents_downgrade():
    """
    Step 1: Relationship at ACQUAINTANCE.
    Step 2: Trust score drops (noshow events added — stub trigger).
    Step 3: Backend detects drop → calls freeze().
    Step 4: Tier remains ACQUAINTANCE (no downgrade).
    Step 5: checkUpgrade returns None while frozen.
    """
    print(f"\n--- {UC_ID}: Happy Path — Freeze Prevents Downgrade ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()

    # Step 1: Establish ACQUAINTANCE
    _reach_tier(sm, a, b, TierEnum.ACQUAINTANCE)
    tier = sm.getRelationship(a, b)
    if tier != TierEnum.ACQUAINTANCE:
        print(f"  FAIL  Step 1: Expected ACQUAINTANCE, got {tier}")
        return False
    print("  PASS  Step 1: Relationship at ACQUAINTANCE")

    # Step 2: Trust score drops (Backend detects this via trust monitoring)
    print("  [Step 2] Trust drop detected by Backend (stub)")

    # Step 3: Backend calls freeze
    sm.freeze(a, b)

    # Step 4: Tier unchanged
    tier_after = sm.getRelationship(a, b)
    if tier_after != TierEnum.ACQUAINTANCE:
        print(f"  FAIL  Step 4: Tier changed during freeze: {tier_after}")
        return False
    print("  PASS  Step 4: Tier preserved at ACQUAINTANCE (no downgrade)")

    # Step 5: No upgrade while frozen
    sm.recordSuccessfulDate(a, b, rating=5.0)
    sm.recordSuccessfulDate(a, b, rating=5.0)
    result = sm.checkUpgrade(a, b)
    if result is not None:
        print(f"  FAIL  Step 5: Upgrade should be blocked while frozen: {result}")
        return False
    print("  PASS  Step 5: checkUpgrade blocked by freeze")
    return True


def test_unfreeze_restores_upgrade_path():
    """
    Step 1: Relationship frozen at ACQUAINTANCE (3 dates done).
    Step 2: Trust recovers → Backend calls unfreeze().
    Step 3: checkUpgrade now succeeds → COLLEAGUE.
    """
    print(f"\n--- {UC_ID}: Unfreeze Restores Upgrade ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()

    # Setup: 3 dates, at ACQUAINTANCE, then freeze
    for _ in range(3):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.freeze(a, b)

    # Step 2: Unfreeze
    sm.unfreeze(a, b)

    # Step 3: Upgrade now proceeds
    result = sm.checkUpgrade(a, b)  # → COLLEAGUE (3 dates >= 3)
    if result != TierEnum.COLLEAGUE:
        print(f"  FAIL  Step 3: Expected COLLEAGUE, got {result}")
        return False
    print("  PASS  Step 3: COLLEAGUE after unfreeze")
    return True


def test_freeze_does_not_reset_counters():
    """
    Boundary: Freeze does not reset successful_dates or avg_rating.
    """
    print(f"\n--- {UC_ID}: Boundary — Freeze Preserves Counters ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()

    for _ in range(5):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    rel_before_freeze = sm._get_or_create_rel(a, b)
    dates_before = rel_before_freeze.successful_dates

    sm.freeze(a, b)
    rel_after_freeze = sm._get_or_create_rel(a, b)

    if rel_after_freeze.successful_dates != dates_before:
        print(f"  FAIL  Freeze reset dates: {dates_before} → {rel_after_freeze.successful_dates}")
        return False
    print(f"  PASS  Freeze preserves successful_dates = {dates_before}")
    return True


def test_double_freeze_idempotent():
    """
    Edge case: Calling freeze() twice does not cause errors.
    """
    print(f"\n--- {UC_ID}: Edge Case — Double Freeze Idempotent ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    try:
        sm.freeze(a, b)
        sm.freeze(a, b)
        rel = sm._get_or_create_rel(a, b)
        if not rel.is_frozen:
            print("  FAIL  Double freeze should keep is_frozen=True")
            return False
        print("  PASS  Double freeze is idempotent")
        return True
    except Exception as e:
        print(f"  FAIL  Double freeze raised: {e}")
        return False


def test_double_unfreeze_idempotent():
    """
    Edge case: Calling unfreeze() twice does not cause errors.
    """
    print(f"\n--- {UC_ID}: Edge Case — Double Unfreeze Idempotent ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    sm.freeze(a, b)
    try:
        sm.unfreeze(a, b)
        sm.unfreeze(a, b)
        rel = sm._get_or_create_rel(a, b)
        if rel.is_frozen:
            print("  FAIL  Double unfreeze should keep is_frozen=False")
            return False
        print("  PASS  Double unfreeze is idempotent")
        return True
    except Exception as e:
        print(f"  FAIL  Double unfreeze raised: {e}")
        return False


def main():
    tests = [
        ("freeze_prevents_downgrade", test_freeze_prevents_downgrade),
        ("unfreeze_restores", test_unfreeze_restores_upgrade_path),
        ("counters_preserved", test_freeze_does_not_reset_counters),
        ("double_freeze", test_double_freeze_idempotent),
        ("double_unfreeze", test_double_unfreeze_idempotent),
    ]
    p = f = 0
    for name, fn in tests:
        try:
            ok = fn()
            if ok: p += 1
            else: f += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            f += 1
    print(f"\n[{UC_ID}] {p} passed, {f} failed\n")
    return f


if __name__ == "__main__":
    print(f"\n=== {UC_ID}: Relationship Freeze/Unfreeze ===")
    sys.exit(0 if main() == 0 else 1)
