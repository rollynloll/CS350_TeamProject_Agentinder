"""
test_authorization_policy.py — check_agent_actor 권한 분기 단위 테스트.

테스트 대상: backend/app/auth/authorization_policy.py::check_agent_actor
호출 위치: pytest 수집 시 자동 실행. DB 연결 없이 dict 픽스처로 검증.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.auth.auth_context import AuthContext
from app.auth.authorization_policy import check_agent_actor


def _agent_ctx(agent_id, principal_id):
    return AuthContext(
        role="agent", session_id=agent_id, agent_id=agent_id, principal_id=principal_id
    )


def _principal_ctx(principal_id):
    return AuthContext(role="principal", session_id=principal_id, principal_id=principal_id)


class TestCheckAgentActorAsAgent:
    """role == 'agent' (X-Agent-Key) 인증 분기."""

    def test_agent_acting_as_self_passes(self) -> None:
        aid = uuid4()
        ctx = _agent_ctx(aid, uuid4())
        # agent_row 의 소유자와 무관하게 본인 agent_id 면 통과
        check_agent_actor(ctx, aid, {"principal_id": uuid4()})

    def test_agent_acting_as_other_rejected(self) -> None:
        aid = uuid4()
        other = uuid4()
        ctx = _agent_ctx(aid, uuid4())
        with pytest.raises(PermissionError):
            check_agent_actor(ctx, other, {"principal_id": uuid4()})


class TestCheckAgentActorAsPrincipal:
    """role == 'principal' (JWT) 인증 분기 — 기존 소유자 검사."""

    def test_owner_passes(self) -> None:
        pid = uuid4()
        aid = uuid4()
        ctx = _principal_ctx(pid)
        check_agent_actor(ctx, aid, {"principal_id": pid})

    def test_non_owner_rejected(self) -> None:
        pid = uuid4()
        aid = uuid4()
        ctx = _principal_ctx(pid)
        with pytest.raises(PermissionError):
            check_agent_actor(ctx, aid, {"principal_id": uuid4()})
