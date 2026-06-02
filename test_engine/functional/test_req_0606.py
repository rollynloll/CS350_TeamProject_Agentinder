"""
REQ-0606/0607 — Rating Validation and Edit Window
Source: model_requirements.md > Rating
REQ-0606: stars 1–5, compatibility 0.0–1.0, comment max 280 chars
REQ-0607: Rating locked 72 hours after creation; update after lock raises PermissionError
Code: models/rating/rating.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import assert_equal, assert_true, run_suite
from models.rating.rating import Rating, EDIT_WINDOW_SECONDS
from models.enums import IssueEnum
from datetime import datetime, timezone, timedelta
from uuid import uuid4

REQ_ID = "REQ-0606"


def _make_rating(stars=4, compatibility=0.8, issues=None):
    return Rating(
        date_id=uuid4(),
        rater_principal_id=uuid4(),
        rated_agent_id=uuid4(),
        stars=stars,
        compatibility=compatibility,
        issues=issues or [],
    )


def test_valid_rating_creation():
    """Happy path: Valid rating (stars=4, compatibility=0.8) created without error."""
    try:
        r = _make_rating(stars=4, compatibility=0.8)
        return assert_equal("Valid rating created", r.stars, 4)
    except Exception as e:
        print(f"  FAIL  Unexpected error: {e}")
        return False


def test_stars_boundary_low():
    """Boundary: stars=1 (minimum) is valid."""
    try:
        r = _make_rating(stars=1)
        return assert_equal("stars=1 valid", r.stars, 1)
    except Exception as e:
        print(f"  FAIL  stars=1 raised: {e}")
        return False


def test_stars_boundary_high():
    """Boundary: stars=5 (maximum) is valid."""
    try:
        r = _make_rating(stars=5)
        return assert_equal("stars=5 valid", r.stars, 5)
    except Exception as e:
        print(f"  FAIL  stars=5 raised: {e}")
        return False


def test_invalid_stars_rejected():
    """Edge case: stars=0 raises ValueError."""
    try:
        _make_rating(stars=0)
        print("  FAIL  stars=0 did not raise ValueError")
        return False
    except ValueError:
        print("  PASS  stars=0 raises ValueError")
        return True


def test_invalid_stars_6_rejected():
    """Edge case: stars=6 raises ValueError."""
    try:
        _make_rating(stars=6)
        print("  FAIL  stars=6 did not raise ValueError")
        return False
    except ValueError:
        print("  PASS  stars=6 raises ValueError")
        return True


def test_compatibility_boundary():
    """Boundary: compatibility=0.0 and 1.0 are valid."""
    try:
        r0 = _make_rating(compatibility=0.0)
        r1 = _make_rating(compatibility=1.0)
        ok = (r0.compatibility == 0.0 and r1.compatibility == 1.0)
        return assert_equal("compatibility 0.0 and 1.0 valid", ok, True)
    except Exception as e:
        print(f"  FAIL  {e}")
        return False


def test_compatibility_invalid():
    """Edge case: compatibility > 1.0 raises ValueError."""
    try:
        _make_rating(compatibility=1.1)
        print("  FAIL  compatibility=1.1 did not raise ValueError")
        return False
    except ValueError:
        print("  PASS  compatibility=1.1 raises ValueError")
        return True


def test_locked_rating_raises():
    """Edge case: Updating a locked rating raises PermissionError."""
    # SRS REQ-0607: locked after 72h
    r = _make_rating()
    r.lock()
    try:
        r.update({"stars": 5})
        print("  FAIL  update on locked rating did not raise")
        return False
    except PermissionError:
        print("  PASS  Locked rating raises PermissionError on update")
        return True


def test_edit_window_72h():
    """Boundary: Edit window constant = 72*3600 seconds."""
    return assert_equal("EDIT_WINDOW_SECONDS = 72*3600", EDIT_WINDOW_SECONDS, 72 * 3600)


def test_valid_update_within_window():
    """Happy path: Update allowed within 72h window."""
    r = _make_rating(stars=3)
    try:
        r.update({"stars": 5})
        return assert_equal("Update within window succeeds", r.stars, 5)
    except Exception as e:
        print(f"  FAIL  {e}")
        return False


def test_hallucination_issue_tracked():
    """Happy path: IssueEnum.HALLUCINATION stored in issues list."""
    r = _make_rating(issues=[IssueEnum.HALLUCINATION])
    return assert_equal("HALLUCINATION in issues", IssueEnum.HALLUCINATION in r.issues, True)


def test_to_trust_data_point_conversion():
    """Happy path: to_trust_data_point() maps stars/5 → peer_rating."""
    r = _make_rating(stars=4, issues=[IssueEnum.HALLUCINATION])
    dp = r.to_trust_data_point()
    ok = (dp.peer_rating is r) and dp.hallucination_confirmed
    return assert_equal("to_trust_data_point() correct", ok, True)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: Rating Validation and Edit Window ===")
    tests = [
        ("valid_creation", test_valid_rating_creation),
        ("stars_low", test_stars_boundary_low),
        ("stars_high", test_stars_boundary_high),
        ("stars_0_invalid", test_invalid_stars_rejected),
        ("stars_6_invalid", test_invalid_stars_6_rejected),
        ("compat_boundary", test_compatibility_boundary),
        ("compat_invalid", test_compatibility_invalid),
        ("locked_raises", test_locked_rating_raises),
        ("edit_window_72h", test_edit_window_72h),
        ("update_within_window", test_valid_update_within_window),
        ("hallucination_tracked", test_hallucination_issue_tracked),
        ("to_trust_dp", test_to_trust_data_point_conversion),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
