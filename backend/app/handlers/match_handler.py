from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .. import db
from ..auth.authorization_policy import check_match_participant
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth, get_principal

router = APIRouter(prefix="/v1/matches", tags=["matches"])


@router.get("")
async def list_matches(
    agent_id: UUID | None = Query(None),
    status: str | None = Query(None),
    principal=Depends(get_principal),
) -> dict:
    if agent_id:
        row = await db.get_agent_row(agent_id)
        if row is None:
            raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
        if row["principal_id"] != principal.principal_id:
            raise PermissionError("이 에이전트의 소유자가 아닙니다.")
        rows = await db.get_matches_for_agent(agent_id, status)
    else:
        all_rows: list = []
        for agent in principal.agents:
            all_rows.extend(await db.get_matches_for_agent(agent.agent_id, status))
        rows = all_rows

    return envelope(data=[
        {k: str(v) if isinstance(v, UUID) else v for k, v in dict(r).items()}
        for r in rows
    ])


@router.post("/{match_id}/approve")
async def approve_match(
    match_id: UUID,
    principal=Depends(get_principal),
    ctx=Depends(get_auth),
) -> dict:
    await check_match_participant(ctx, match_id)
    principal.approveMatch(match_id)
    await db.update_match_status(match_id, "approved")
    return envelope(data={"match_id": str(match_id), "status": "approved"})


@router.post("/{match_id}/reject")
async def reject_match(
    match_id: UUID,
    principal=Depends(get_principal),
    ctx=Depends(get_auth),
) -> dict:
    await check_match_participant(ctx, match_id)
    principal.rejectMatch(match_id)
    await db.update_match_status(match_id, "rejected")
    return envelope(data={"match_id": str(match_id), "status": "rejected"})


@router.get("/{match_id}/dates")
async def get_date_history(match_id: UUID, ctx=Depends(get_auth)) -> dict:
    await check_match_participant(ctx, match_id)
    rows = await db.get_dates_for_match(match_id)
    return envelope(data=[
        {k: str(v) if isinstance(v, UUID) else v for k, v in dict(r).items()}
        for r in rows
    ])
