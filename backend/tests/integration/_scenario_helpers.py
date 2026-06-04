"""
_scenario_helpers.py — 7대 테스트 시나리오 공용 픽스처/빌더.

깊이: 핸들러 통합 (httpx.AsyncClient + ASGITransport, DB는 AsyncMock).
실제 Postgres 불필요. 도메인 객체(Principal/Agent/ScoreManager)는 진짜를 쓰고
DB I/O 경계만 mock 한다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI

from app.auth.auth_context import AuthContext
from app.pubsub.event_bus import EventBus


# ── 도메인 객체 빌더 ────────────────────────────────────────────────────────

def make_principal(principal_id: UUID | None = None, plan: str = "PREMIUM"):
    """진짜 Principal 도메인 객체. (DB 없이 인메모리 구성)"""
    from models import AgentService, Principal, PrincipalProfile
    from models.enums import PlanEnum
    from models.score.score_manager import ScoreManager

    pid = principal_id or uuid4()
    profile = PrincipalProfile(
        email="user@example.com",
        name="Test User",
        plan=PlanEnum(plan),
    )
    return Principal(
        principal_id=pid,
        profile=profile,
        agent_service=AgentService(),
        score_manager=ScoreManager(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_auth_ctx(principal_id: UUID, email: str = "user@example.com") -> AuthContext:
    return AuthContext(
        role="principal",
        session_id=uuid4(),
        principal_id=principal_id,
        email=email,
    )


def make_agent_request(display_name: str = "Agent A", tags=None) -> dict:
    """POST /v1/agents 바디 (CreateAgentRequest 호환)."""
    return {
        "display_name": display_name,
        "visibility": "PUBLIC",
        "capability_tags": tags if tags is not None else ["python", "ml"],
        "available_timezones": ["UTC"],
        "personality": {
            "surface": {"bio": "hello", "style_sliders": {"formal": 0.5}},
            "deep": {},
            "aspiration": {},
        },
        "llm_model": "gpt-4o",
    }


# ── DB row 픽스처 ──────────────────────────────────────────────────────────

def make_principal_row(principal_id: UUID, email="user@example.com",
                       name="user", plan="premium") -> dict:
    return {
        "principal_id": principal_id,
        "email": email,
        "name": name,
        "plan": plan,
        "mfa_enabled": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


def make_agent_row(agent_id: UUID, principal_id: UUID, visibility="public") -> dict:
    return {
        "agent_id": agent_id,
        "principal_id": principal_id,
        "display_name": "Test Agent",
        "visibility": visibility,
        "trust_score": 0.8,
        "tier_badge": "gold",
        "date_count": 3,
        "avatar_url": None,
        "has_embedding": True,
        "llm_model": "gpt-4o",
    }


def make_match_row(match_id: UUID, agent_a_id: UUID, agent_b_id: UUID) -> dict:
    return {
        "match_id": match_id,
        "agent_a_id": agent_a_id,
        "agent_b_id": agent_b_id,
        "status": "active",
    }


def make_date_row(date_id: UUID, match_id: UUID, *, type="async",
                  scheduled_at=None, started_at=None, ended_at=None,
                  outcome=None) -> dict:
    return {
        "date_id": date_id,
        "match_id": match_id,
        "type": type,
        "scheduled_at": scheduled_at,
        "started_at": started_at,
        "ended_at": ended_at,
        "outcome": outcome,
        "is_noshow": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


# ── 앱 빌더 ────────────────────────────────────────────────────────────────

def build_app(router, *, principal=None, auth_ctx=None, event_bus=None) -> FastAPI:
    """라우터 + Depends 오버라이드로 테스트 앱 구성."""
    from app.deps import get_auth, get_event_bus, get_principal

    app = FastAPI()
    app.include_router(router)

    if principal is not None:
        app.dependency_overrides[get_principal] = lambda: principal
    if auth_ctx is not None:
        app.dependency_overrides[get_auth] = lambda: auth_ctx
    app.dependency_overrides[get_event_bus] = lambda: event_bus or EventBus()
    return app
