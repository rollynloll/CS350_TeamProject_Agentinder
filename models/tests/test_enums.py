"""Tests for all Enum definitions."""
import pytest
from models.enums import SwipeEnum, TierEnum, VisibilityEnum, PlanEnum, IssueEnum


class TestSwipeEnum:
    def test_members(self):
        assert SwipeEnum.RIGHT == "RIGHT"
        assert SwipeEnum.LEFT == "LEFT"
        assert SwipeEnum.UP == "UP"

    def test_all_members(self):
        assert set(SwipeEnum) == {SwipeEnum.RIGHT, SwipeEnum.LEFT, SwipeEnum.UP}


class TestTierEnum:
    def test_order_values(self):
        assert TierEnum.STRANGER == "STRANGER"
        assert TierEnum.ACQUAINTANCE == "ACQUAINTANCE"
        assert TierEnum.COLLEAGUE == "COLLEAGUE"
        assert TierEnum.TRUSTED_PARTNER == "TRUSTED_PARTNER"

    def test_count(self):
        assert len(TierEnum) == 4


class TestVisibilityEnum:
    def test_members(self):
        assert VisibilityEnum.PUBLIC == "PUBLIC"
        assert VisibilityEnum.RESTRICTED == "RESTRICTED"
        assert VisibilityEnum.HIDDEN == "HIDDEN"


class TestPlanEnum:
    def test_members(self):
        assert PlanEnum.FREE == "FREE"
        assert PlanEnum.PREMIUM == "PREMIUM"


class TestIssueEnum:
    def test_members(self):
        expected = {"HALLUCINATION", "LATENCY", "UNRESPONSIVE", "UNAUTHORIZED"}
        assert {e.value for e in IssueEnum} == expected
