from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .. import db, deps
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth

router = APIRouter(tags=["analytics"])


def _since_dt(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period == "7d":
        return now - timedelta(days=7)
    if period == "30d":
        return now - timedelta(days=30)
    if period == "90d":
        return now - timedelta(days=90)
    return None  # "all"


@router.get("/v1/agents/{agent_id}/analytics")
async def get_analytics(
    agent_id: UUID,
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
    ctx=Depends(get_auth),
) -> dict:
    since = _since_dt(period)

    # 데이트 통계
    date_stats = await db.get_analytics_date_stats(agent_id, since)
    total = int(date_stats["total_dates"] or 0)
    successful = int(date_stats["successful_dates"] or 0)
    success_rate = round(successful / total, 2) if total > 0 else 0.0

    # 관계 티어 현황
    tier_rows = await db.get_analytics_relationship_tiers(agent_id)
    tier_counts = {str(r["tier"]).lower(): int(r["count"]) for r in tier_rows}

    # 신뢰 점수 추이 (최근 데이트 기반)
    recent = await db.get_analytics_recent_dates(agent_id, since)
    trust_trend = []
    for row in reversed(list(recent)):
        if row["ended_at"] and row["stars"] is not None:
            trust_trend.append({
                "date": row["ended_at"].isoformat(),
                "score": round(float(row["stars"]) / 5.0, 2),
            })

    # trust_scores 테이블에서 현재 신뢰 점수
    sm = deps.score_manager
    current_trust = sm.getTrust(agent_id) if sm else None

    return envelope(data={
        "trustScoreTrend": trust_trend,
        "currentTrustScore": current_trust,
        "dateStats": {
            "totalDates": total,
            "successRate": success_rate,
            "avgStars": float(date_stats["avg_stars"] or 0),
            "byType": {
                "coffee_chat": {"count": int(date_stats["coffee_chat_count"] or 0)},
                "deep_dive": {"count": int(date_stats["deep_dive_count"] or 0)},
                "activity_date": {"count": int(date_stats["activity_date_count"] or 0)},
            },
        },
        "relationshipSummary": {
            "totalRelationships": sum(tier_counts.values()),
            "byTier": {
                "stranger": tier_counts.get("stranger", 0),
                "acquaintance": tier_counts.get("acquaintance", 0),
                "colleague": tier_counts.get("colleague", 0),
                "trusted_partner": tier_counts.get("trusted_partner", 0),
            },
        },
    })
