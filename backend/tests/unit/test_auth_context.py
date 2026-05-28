"""
test_auth_context.py — AuthContext 데이터클래스 단위 테스트.

테스트 대상: backend/app/auth/auth_context.py
호출 위치: pytest 수집 시 자동 실행.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.auth.auth_context import AuthContext


class TestAuthContextRoles:
    """role 필드 및 role 검사 메서드 테스트."""

    def test_is_principal_returns_true_when_role_is_principal(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4())
        assert ctx.is_principal() is True

    def test_is_principal_returns_false_when_role_is_agent(self) -> None:
        ctx = AuthContext(role="agent", session_id=uuid4())
        assert ctx.is_principal() is False

    def test_is_principal_returns_false_when_role_is_admin(self) -> None:
        ctx = AuthContext(role="admin", session_id=uuid4())
        assert ctx.is_principal() is False

    def test_is_agent_returns_true_when_role_is_agent(self) -> None:
        ctx = AuthContext(role="agent", session_id=uuid4())
        assert ctx.is_agent() is True

    def test_is_agent_returns_false_when_role_is_principal(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4())
        assert ctx.is_agent() is False

    def test_is_agent_returns_false_when_role_is_admin(self) -> None:
        ctx = AuthContext(role="admin", session_id=uuid4())
        assert ctx.is_agent() is False


class TestAuthContextScopes:
    """has_scope 메서드 테스트."""

    def test_has_scope_returns_true_when_scope_present(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4(), scopes=["read", "write"])
        assert ctx.has_scope("read") is True

    def test_has_scope_returns_true_for_write_scope(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4(), scopes=["read", "write"])
        assert ctx.has_scope("write") is True

    def test_has_scope_returns_false_when_scope_absent(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4(), scopes=["read"])
        assert ctx.has_scope("admin") is False

    def test_has_scope_returns_false_when_scopes_empty(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4(), scopes=[])
        assert ctx.has_scope("read") is False

    def test_has_scope_returns_false_when_scopes_default(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4())
        assert ctx.has_scope("anything") is False


class TestAuthContextOptionalFields:
    """principal_id, agent_id optional 필드 테스트."""

    def test_principal_id_defaults_to_none(self) -> None:
        ctx = AuthContext(role="principal", session_id=uuid4())
        assert ctx.principal_id is None

    def test_agent_id_defaults_to_none(self) -> None:
        ctx = AuthContext(role="agent", session_id=uuid4())
        assert ctx.agent_id is None

    def test_principal_id_set_correctly(self) -> None:
        pid = uuid4()
        ctx = AuthContext(role="principal", session_id=uuid4(), principal_id=pid)
        assert ctx.principal_id == pid

    def test_agent_id_set_correctly(self) -> None:
        aid = uuid4()
        ctx = AuthContext(role="agent", session_id=uuid4(), agent_id=aid)
        assert ctx.agent_id == aid

    def test_session_id_is_stored(self) -> None:
        sid = uuid4()
        ctx = AuthContext(role="principal", session_id=sid)
        assert ctx.session_id == sid


class TestAuthContextEdgeCases:
    """경계 케이스 테스트."""

    def test_scopes_list_is_independent_per_instance(self) -> None:
        """두 인스턴스가 같은 list 객체를 공유하지 않는다."""
        ctx1 = AuthContext(role="principal", session_id=uuid4())
        ctx2 = AuthContext(role="principal", session_id=uuid4())
        ctx1.scopes.append("read")
        assert "read" not in ctx2.scopes

    def test_has_scope_case_sensitive(self) -> None:
        """scope 검사는 대소문자를 구분한다."""
        ctx = AuthContext(role="principal", session_id=uuid4(), scopes=["Read"])
        assert ctx.has_scope("read") is False
        assert ctx.has_scope("Read") is True

    def test_admin_role_is_neither_principal_nor_agent(self) -> None:
        ctx = AuthContext(role="admin", session_id=uuid4())
        assert ctx.is_principal() is False
        assert ctx.is_agent() is False
