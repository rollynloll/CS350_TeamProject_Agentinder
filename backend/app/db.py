from __future__ import annotations

import json as _json
from typing import Any
from uuid import UUID

import asyncpg

from .config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised")
    return _pool


# ── Swipes ────────────────────────────────────────────────────────────────

async def insert_swipe(agent_id: UUID, target_id: UUID, direction: str) -> None:
    await get_pool().execute(
        "INSERT INTO swipes (agent_id, target_id, direction)"
        " VALUES ($1, $2, $3::swipe_enum) ON CONFLICT (agent_id, target_id) DO NOTHING",
        agent_id, target_id, direction,
    )


async def get_counter_swipe(agent_id: UUID, target_id: UUID) -> asyncpg.Record | None:
    """target_id 가 agent_id 를 오른쪽/위로 스와이프한 기록이 있으면 반환."""
    return await get_pool().fetchrow(
        "SELECT * FROM swipes WHERE agent_id = $1 AND target_id = $2 AND direction != 'left'",
        target_id, agent_id,
    )


# ── Matches ───────────────────────────────────────────────────────────────

async def insert_match(agent_a_id: UUID, agent_b_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "INSERT INTO matches (agent_a_id, agent_b_id) VALUES ($1, $2)"
        " ON CONFLICT (agent_a_id, agent_b_id) DO NOTHING RETURNING *",
        agent_a_id, agent_b_id,
    )


async def get_match(match_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT * FROM matches WHERE match_id = $1", match_id
    )


async def get_match_by_agents(agent_a_id: UUID, agent_b_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT * FROM matches"
        " WHERE (agent_a_id = $1 AND agent_b_id = $2)"
        "    OR (agent_a_id = $2 AND agent_b_id = $1)",
        agent_a_id, agent_b_id,
    )


async def get_matches_for_agent(agent_id: UUID, status: str | None = None) -> list[asyncpg.Record]:
    base = (
        "SELECT m.*,"
        " CASE WHEN m.agent_a_id = $1 THEN m.agent_b_id ELSE m.agent_a_id END AS counterpart_id,"
        " ap.display_name AS counterpart_name, ap.avatar_url AS counterpart_avatar,"
        " ap.tier_badge AS counterpart_tier_badge, ap.trust_score AS counterpart_trust_score"
        " FROM matches m"
        " JOIN agent_profiles ap"
        "   ON ap.agent_id = CASE WHEN m.agent_a_id = $1 THEN m.agent_b_id ELSE m.agent_a_id END"
        " WHERE (m.agent_a_id = $1 OR m.agent_b_id = $1)"
    )
    if status:
        return await get_pool().fetch(
            base + " AND m.status = $2::match_status_enum ORDER BY m.created_at DESC",
            agent_id, status,
        )
    return await get_pool().fetch(base + " ORDER BY m.created_at DESC", agent_id)


async def update_match_status(match_id: UUID, status: str) -> None:
    await get_pool().execute(
        "UPDATE matches SET status = $1::match_status_enum WHERE match_id = $2",
        status, match_id,
    )


# ── Dates ─────────────────────────────────────────────────────────────────

async def insert_date(match_id: UUID, date_type: str | None = None, scheduled_at: Any = None) -> asyncpg.Record:
    return await get_pool().fetchrow(
        "INSERT INTO dates (match_id, type, scheduled_at) VALUES ($1, $2, $3) RETURNING *",
        match_id, date_type, scheduled_at,
    )


async def get_date(date_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT * FROM dates WHERE date_id = $1", date_id
    )


async def get_dates_for_match(match_id: UUID) -> list[asyncpg.Record]:
    return await get_pool().fetch(
        "SELECT * FROM dates WHERE match_id = $1 ORDER BY created_at DESC", match_id
    )


async def start_date(date_id: UUID) -> None:
    await get_pool().execute(
        "UPDATE dates SET started_at = now() WHERE date_id = $1", date_id
    )


async def end_date(date_id: UUID, outcome: str | None, is_noshow: bool = False) -> None:
    await get_pool().execute(
        "UPDATE dates SET ended_at = now(), outcome = $2, is_noshow = $3 WHERE date_id = $1",
        date_id, outcome, is_noshow,
    )


# ── Messages ──────────────────────────────────────────────────────────────

async def insert_message(match_id: UUID, sender_agent_id: UUID, content: str) -> asyncpg.Record:
    return await get_pool().fetchrow(
        "INSERT INTO messages (match_id, sender_agent_id, content) VALUES ($1, $2, $3) RETURNING *",
        match_id, sender_agent_id, content,
    )


async def get_messages(
    match_id: UUID, limit: int = 50, before_id: UUID | None = None
) -> list[asyncpg.Record]:
    if before_id:
        cursor_row = await get_pool().fetchrow(
            "SELECT created_at FROM messages WHERE message_id = $1", before_id
        )
        if cursor_row:
            return await get_pool().fetch(
                "SELECT * FROM messages WHERE match_id = $1 AND created_at < $2"
                " ORDER BY created_at DESC LIMIT $3",
                match_id, cursor_row["created_at"], limit,
            )
    return await get_pool().fetch(
        "SELECT * FROM messages WHERE match_id = $1 ORDER BY created_at DESC LIMIT $2",
        match_id, limit,
    )


async def mark_messages_read(match_id: UUID, reader_agent_id: UUID) -> None:
    await get_pool().execute(
        "UPDATE messages SET is_read = true"
        " WHERE match_id = $1 AND sender_agent_id != $2 AND is_read = false",
        match_id, reader_agent_id,
    )


# ── Agents / Principals (B 소유 테이블 — 읽기 전용) ───────────────────────

async def get_agent_row(agent_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.available_timezones,"
        " ap.capability_embedding IS NOT NULL AS has_embedding,"
        " aper.bio, aper.style_formal, aper.style_verbose, aper.style_bold,"
        " COALESCE(array_agg(cv.name) FILTER (WHERE cv.name IS NOT NULL), '{}') AS capability_tags"
        " FROM agents a"
        " JOIN agent_profiles ap USING (agent_id)"
        " LEFT JOIN agent_personalities aper USING (agent_id)"
        " LEFT JOIN agent_capability_tags act USING (agent_id)"
        " LEFT JOIN capability_vocabulary cv USING (tag_id)"
        " WHERE a.agent_id = $1"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.available_timezones, ap.capability_embedding,"
        " aper.bio, aper.style_formal, aper.style_verbose, aper.style_bold",
        agent_id,
    )


async def get_all_visible_agents(exclude_agent_id: UUID) -> list[asyncpg.Record]:
    return await get_pool().fetch(
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector,"
        " COALESCE(array_agg(cv.name) FILTER (WHERE cv.name IS NOT NULL), '{}') AS capability_tags"
        " FROM agents a JOIN agent_profiles ap USING (agent_id)"
        " LEFT JOIN agent_capability_tags act USING (agent_id)"
        " LEFT JOIN capability_vocabulary cv USING (tag_id)"
        " WHERE a.agent_id != $1 AND ap.is_suspended = false AND ap.visibility != 'hidden'"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url, ap.style_vector",
        exclude_agent_id,
    )


async def get_principal_agents(principal_id: UUID) -> list[asyncpg.Record]:
    return await get_pool().fetch(
        "SELECT a.agent_id, ap.display_name, ap.visibility, ap.tier_badge,"
        " ap.avatar_url, a.created_at"
        " FROM agents a JOIN agent_profiles ap USING (agent_id)"
        " WHERE a.principal_id = $1 ORDER BY a.created_at DESC",
        principal_id,
    )


async def get_principal_row(principal_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT p.principal_id, p.created_at, pp.email, pp.name, pp.plan, pp.mfa_enabled"
        " FROM principals p JOIN principal_profiles pp USING (principal_id)"
        " WHERE p.principal_id = $1",
        principal_id,
    )


async def get_principal_agents_full(principal_id: UUID) -> list[asyncpg.Record]:
    """principal의 모든 에이전트를 Agent 객체 재구성에 필요한 전체 필드와 함께 반환."""
    return await get_pool().fetch(
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.available_timezones, ap.llm_model,"
        " aper.bio, aper.style_formal, aper.style_verbose, aper.style_bold,"
        " aper.thinking_style, aper.values, aper.conflict_style,"
        " aper.collaboration_goal, aper.domain_interest, aper.system_prompt_cache,"
        " COALESCE(array_agg(cv.name) FILTER (WHERE cv.name IS NOT NULL), '{}') AS capability_tags"
        " FROM agents a"
        " JOIN agent_profiles ap USING (agent_id)"
        " LEFT JOIN agent_personalities aper USING (agent_id)"
        " LEFT JOIN agent_capability_tags act USING (agent_id)"
        " LEFT JOIN capability_vocabulary cv USING (tag_id)"
        " WHERE a.principal_id = $1"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.available_timezones, ap.llm_model,"
        " aper.bio, aper.style_formal, aper.style_verbose, aper.style_bold,"
        " aper.thinking_style, aper.values, aper.conflict_style,"
        " aper.collaboration_goal, aper.domain_interest, aper.system_prompt_cache",
        principal_id,
    )


async def insert_agent_full(
    agent_id: UUID,
    principal_id: UUID,
    display_name: str,
    avatar_url: str,
    visibility: str,
    llm_model: str,
    style_vector: dict,
    available_timezones: list[str],
    bio: str,
    style_formal: int,
    style_verbose: int,
    style_bold: int,
    thinking_style: str | None,
    values_text: str | None,
    conflict_style: str | None,
    collaboration_goal: str | None,
    domain_interest: str | None,
    system_prompt_cache: str,
    api_key_hash: str,
) -> None:
    """에이전트 생성 시 agents, agent_profiles, agent_personalities, agent_credentials에 트랜잭션으로 삽입."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO agents (agent_id, principal_id) VALUES ($1, $2)",
                agent_id, principal_id,
            )
            await conn.execute(
                "INSERT INTO agent_profiles"
                " (agent_id, display_name, avatar_url, visibility, llm_model,"
                "  style_vector, available_timezones)"
                " VALUES ($1, $2, $3, $4::visibility_enum, $5, $6::jsonb, $7)",
                agent_id, display_name, avatar_url or None, visibility.lower(),
                llm_model, _json.dumps(style_vector), available_timezones,
            )
            await conn.execute(
                "INSERT INTO agent_personalities"
                " (agent_id, bio, style_formal, style_verbose, style_bold,"
                "  thinking_style, values, conflict_style,"
                "  collaboration_goal, domain_interest, system_prompt_cache)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
                agent_id, bio, style_formal, style_verbose, style_bold,
                thinking_style, values_text, conflict_style,
                collaboration_goal, domain_interest, system_prompt_cache,
            )
            await conn.execute(
                "INSERT INTO agent_credentials (agent_id, api_key_hash) VALUES ($1, $2)",
                agent_id, api_key_hash,
            )


async def upsert_agent_profile_row(
    agent_id: UUID,
    display_name: str,
    avatar_url: str,
    visibility: str,
    llm_model: str,
    style_vector: dict,
    available_timezones: list[str],
    bio: str,
    style_formal: int,
    style_verbose: int,
    style_bold: int,
    thinking_style: str | None,
    values_text: str | None,
    conflict_style: str | None,
    collaboration_goal: str | None,
    domain_interest: str | None,
    system_prompt_cache: str,
) -> None:
    """에이전트 수정 시 agent_profiles + agent_personalities를 트랜잭션으로 갱신."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE agent_profiles"
                " SET display_name=$2, avatar_url=$3, visibility=$4::visibility_enum,"
                "     llm_model=$5, style_vector=$6::jsonb, available_timezones=$7, updated_at=now()"
                " WHERE agent_id=$1",
                agent_id, display_name, avatar_url or None, visibility.lower(),
                llm_model, _json.dumps(style_vector), available_timezones,
            )
            await conn.execute(
                "UPDATE agent_personalities"
                " SET bio=$2, style_formal=$3, style_verbose=$4, style_bold=$5,"
                "     thinking_style=$6, values=$7, conflict_style=$8,"
                "     collaboration_goal=$9, domain_interest=$10, system_prompt_cache=$11"
                " WHERE agent_id=$1",
                agent_id, bio, style_formal, style_verbose, style_bold,
                thinking_style, values_text, conflict_style,
                collaboration_goal, domain_interest, system_prompt_cache,
            )


async def sync_capability_tags(agent_id: UUID, tag_names: list[str]) -> None:
    """에이전트의 capability_tags를 통제 어휘 기반으로 교체. 미등록 태그는 어휘에 자동 추가."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            if tag_names:
                await conn.executemany(
                    "INSERT INTO capability_vocabulary (name) VALUES ($1) ON CONFLICT (name) DO NOTHING",
                    [(name,) for name in tag_names],
                )
                tag_rows = await conn.fetch(
                    "SELECT tag_id FROM capability_vocabulary WHERE name = ANY($1)",
                    tag_names,
                )
                tag_ids = [r["tag_id"] for r in tag_rows]
            else:
                tag_ids = []

            await conn.execute(
                "DELETE FROM agent_capability_tags WHERE agent_id = $1", agent_id
            )
            if tag_ids:
                await conn.executemany(
                    "INSERT INTO agent_capability_tags (agent_id, tag_id) VALUES ($1, $2)",
                    [(agent_id, tid) for tid in tag_ids],
                )
