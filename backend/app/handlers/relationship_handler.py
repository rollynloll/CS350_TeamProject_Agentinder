from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .. import db
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth

router = APIRouter(tags=["relationships"])


@router.get("/v1/agents/{agent_id}/relationships")
async def get_relationships(
    agent_id: UUID,
    tier: str | None = Query(None),
    ctx=Depends(get_auth),
) -> dict:
    rows = await db.get_relationships_for_agent(agent_id)

    tier_order = {"trusted_partner": 0, "colleague": 1, "acquaintance": 2, "stranger": 3}
    groups: dict[str, list] = {}

    for row in rows:
        t = str(row["tier"]).lower()
        if tier and t != tier.lower():
            continue
        if t not in groups:
            groups[t] = []
        groups[t].append({
            "partnerId": str(row["partner_id"]),
            "matchId": str(row["match_id"]) if row["match_id"] is not None else None,
            "partnerName": row["partner_name"] or "",
            "partnerAvatar": row["partner_avatar"] or "",
            "partnerTrustScore": row["partner_trust_score"],
            "tier": t,
            "successfulDates": row["successful_dates"],
            "avgRating": float(row["avg_rating"]) if row["avg_rating"] is not None else None,
            "isFrozen": row["is_frozen"],
            "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
        })

    sorted_groups = sorted(groups.items(), key=lambda x: tier_order.get(x[0], 99))
    result = [
        {"tier": t, "count": len(items), "relationships": items}
        for t, items in sorted_groups
    ]

    return envelope(data={
        "groups": result,
        "totalRelationships": sum(len(g["relationships"]) for g in result),
    })
