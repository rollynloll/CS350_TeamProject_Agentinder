"""Tests for PrincipalProfile."""
import pytest
from models.principal.principal_profile import PrincipalProfile
from models.enums import PlanEnum


class TestPrincipalProfileCreation:
    def test_defaults(self):
        p = PrincipalProfile(email="a@b.com", name="Alice")
        assert p.plan == PlanEnum.FREE
        assert p.mfa_enabled is False

    def test_custom_plan(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.PREMIUM)
        assert p.plan == PlanEnum.PREMIUM


class TestMaxAgents:
    def test_free_plan_max_5(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.FREE)
        assert p.max_agents == 5

    def test_premium_plan_max_20(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.PREMIUM)
        assert p.max_agents == 20


class TestCanAddAgent:
    def test_can_add_when_under_limit(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.FREE)
        assert p.can_add_agent(0) is True
        assert p.can_add_agent(4) is True

    def test_cannot_add_at_limit(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.FREE)
        assert p.can_add_agent(5) is False

    def test_cannot_add_over_limit(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.FREE)
        assert p.can_add_agent(10) is False

    def test_premium_limit(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", plan=PlanEnum.PREMIUM)
        assert p.can_add_agent(19) is True
        assert p.can_add_agent(20) is False


class TestIsMfaEnabled:
    def test_mfa_disabled_by_default(self):
        p = PrincipalProfile(email="a@b.com", name="Alice")
        assert p.is_mfa_enabled() is False

    def test_mfa_enabled(self):
        p = PrincipalProfile(email="a@b.com", name="Alice", mfa_enabled=True)
        assert p.is_mfa_enabled() is True


class TestUpdate:
    def test_update_email(self):
        p = PrincipalProfile(email="old@b.com", name="Alice")
        p.update({"email": "new@b.com"})
        assert p.email == "new@b.com"

    def test_update_plan(self):
        p = PrincipalProfile(email="a@b.com", name="Alice")
        p.update({"plan": PlanEnum.PREMIUM})
        assert p.plan == PlanEnum.PREMIUM
        assert p.max_agents == 20

    def test_update_mfa(self):
        p = PrincipalProfile(email="a@b.com", name="Alice")
        p.update({"mfa_enabled": True})
        assert p.is_mfa_enabled() is True

    def test_update_ignores_unknown_fields(self):
        p = PrincipalProfile(email="a@b.com", name="Alice")
        p.update({"nonexistent": "value"})
        assert not hasattr(p, "nonexistent")

    def test_updated_at_changes(self):
        p = PrincipalProfile(email="a@b.com", name="Alice")
        before = p.updated_at
        p.update({"name": "Bob"})
        assert p.updated_at >= before
