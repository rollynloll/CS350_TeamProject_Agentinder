from __future__ import annotations

import os
import sys
from uuid import UUID

from fastapi import Request

# models/ 는 프로젝트 루트에 위치 — sys.path 에 추가
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from models import AgentService, Principal, PrincipalProfile, ScoreManager
from models.enums import PlanEnum

from . import db
from .auth.auth_context import AuthContext
from .gateway.ws_gateway import WSGateway
from .pubsub.event_bus import EventBus

# ── 앱 전역 싱글톤 ────────────────────────────────────────────────────────
agent_service: AgentService | None = None
score_manager: ScoreManager | None = None
event_bus: EventBus | None = None
ws_gateway: WSGateway | None = None

# V1 인메모리 Principal 캐시 (결정 #5: lazy 재구성 + 캐시)
_principal_cache: dict[UUID, Principal] = {}


def init_singletons() -> None:
    global agent_service, score_manager, event_bus, ws_gateway
    agent_service = AgentService()
    score_manager = ScoreManager()
    event_bus = EventBus()
    ws_gateway = WSGateway()

    event_bus.subscribe("MatchCreated", ws_gateway.on_domain_event)
    event_bus.subscribe("DateProposed", ws_gateway.on_domain_event)
    event_bus.subscribe("DateStarted", ws_gateway.on_domain_event)
    event_bus.subscribe("DateEnded", ws_gateway.on_domain_event)
    event_bus.subscribe("MessageCreated", ws_gateway.on_domain_event)


# ── FastAPI Depends 헬퍼 ─────────────────────────────────────────────────

def get_event_bus() -> EventBus:
    assert event_bus is not None
    return event_bus


def get_ws_gateway() -> WSGateway:
    assert ws_gateway is not None
    return ws_gateway


def get_auth(request: Request) -> AuthContext:
    return request.state.auth


async def get_principal(request: Request) -> Principal:
    ctx: AuthContext = request.state.auth
    pid = ctx.principal_id
    assert pid is not None

    if pid in _principal_cache:
        return _principal_cache[pid]

    # DB에서 Principal 재구성 (결정 #5)
    row = await db.get_principal_row(pid)
    if row is None:
        raise KeyError(f"Principal을 찾을 수 없습니다: {pid}")

    profile = PrincipalProfile(
        email=row["email"],
        name=row["name"],
        plan=PlanEnum(row["plan"]),
    )
    principal = Principal(
        principal_id=pid,
        profile=profile,
        agent_service=agent_service,
        score_manager=score_manager,
        created_at=row["created_at"],
    )
    _principal_cache[pid] = principal
    return principal
