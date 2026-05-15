"""Tests for Rating."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from models.rating.rating import Rating
from models.enums import IssueEnum
from models.score.score_manager import TrustDataPoint


def _make_rating(**kwargs):
    defaults = dict(
        date_id=uuid4(),
        rater_principal_id=uuid4(),
        rated_agent_id=uuid4(),
        stars=4,
        compatibility=0.8,
    )
    defaults.update(kwargs)
    return Rating(**defaults)


class TestRatingCreation:
    def test_valid_creation(self):
        r = _make_rating(stars=5, compatibility=1.0)
        assert r.stars == 5
        assert r.compatibility == 1.0
        assert r.is_locked is False

    def test_invalid_stars_zero(self):
        with pytest.raises(ValueError, match="stars"):
            _make_rating(stars=0)

    def test_invalid_stars_six(self):
        with pytest.raises(ValueError, match="stars"):
            _make_rating(stars=6)

    def test_invalid_compatibility_negative(self):
        with pytest.raises(ValueError, match="compatibility"):
            _make_rating(compatibility=-0.1)

    def test_invalid_compatibility_over_one(self):
        with pytest.raises(ValueError, match="compatibility"):
            _make_rating(compatibility=1.01)

    def test_default_issues_empty(self):
        r = _make_rating()
        assert r.issues == []

    def test_with_issues(self):
        r = _make_rating(issues=[IssueEnum.HALLUCINATION, IssueEnum.LATENCY])
        assert IssueEnum.HALLUCINATION in r.issues
        assert IssueEnum.LATENCY in r.issues


class TestRatingUpdate:
    def test_update_within_window(self):
        r = _make_rating(stars=3)
        r.update({"stars": 5, "comments": "updated"})
        assert r.stars == 5
        assert r.comments == "updated"

    def test_update_disallows_unknown_fields(self):
        r = _make_rating()
        r.update({"nonexistent_field": "value"})
        assert not hasattr(r, "nonexistent_field")

    def test_update_locked_raises(self):
        r = _make_rating()
        r.lock()
        with pytest.raises(PermissionError):
            r.update({"stars": 5})

    def test_update_after_72h_raises(self):
        r = _make_rating()
        r.created_at = datetime.now(timezone.utc) - timedelta(hours=73)
        with pytest.raises(PermissionError):
            r.update({"stars": 5})

    def test_update_after_72h_auto_locks(self):
        r = _make_rating()
        r.created_at = datetime.now(timezone.utc) - timedelta(hours=73)
        try:
            r.update({"stars": 5})
        except PermissionError:
            pass
        assert r.is_locked is True

    def test_updated_at_changes(self):
        r = _make_rating()
        before = r.updated_at
        r.update({"comments": "hello"})
        assert r.updated_at >= before


class TestRatingToTrustDataPoint:
    def test_basic_conversion(self):
        agent_id = uuid4()
        date_id = uuid4()
        r = Rating(
            date_id=date_id,
            rater_principal_id=uuid4(),
            rated_agent_id=agent_id,
            stars=4,
            compatibility=0.8,
        )
        dp = r.to_trust_data_point()
        assert isinstance(dp, TrustDataPoint)
        assert dp.agent_id == agent_id
        assert dp.date_id == date_id
        assert dp.peer_rating is r
        assert dp.task_completed is True
        assert dp.is_noshow is False
        assert dp.hallucination_confirmed is False

    def test_hallucination_issue_sets_flag(self):
        r = _make_rating(issues=[IssueEnum.HALLUCINATION])
        dp = r.to_trust_data_point()
        assert dp.hallucination_confirmed is True

    def test_other_issues_do_not_set_hallucination_flag(self):
        r = _make_rating(issues=[IssueEnum.LATENCY, IssueEnum.UNRESPONSIVE])
        dp = r.to_trust_data_point()
        assert dp.hallucination_confirmed is False
