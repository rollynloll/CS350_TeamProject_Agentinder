from __future__ import annotations

import json as _json
from typing import Any
from uuid import UUID

import asyncpg

from .config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    # Supabase(Supavisor) pooler 호환:
    #   - statement_cache_size=0: prepared statement 캐시 비활성
    #     (Transaction pooler 6543 사용 시 필수, Session pooler 5432 에서도 안전)
    #   - ssl="require": Supabase 는 TLS 를 강제하므로 암호화 연결을 요구
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
        statement_cache_size=0,
        ssl="require",
    )


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
        " ap.tier_badge AS counterpart_tier_badge, ap.trust_score AS counterpart_trust_score,"
        " ld.date_id AS latest_date_id,"
        " ld.started_at AS latest_date_started_at,"
        " ld.ended_at AS latest_date_ended_at"
        " FROM matches m"
        " JOIN agent_profiles ap"
        "   ON ap.agent_id = CASE WHEN m.agent_a_id = $1 THEN m.agent_b_id ELSE m.agent_a_id END"
        " LEFT JOIN LATERAL ("
        "   SELECT date_id, started_at, ended_at FROM dates"
        "   WHERE match_id = m.match_id ORDER BY created_at DESC LIMIT 1"
        " ) ld ON true"
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


# ── Agent credentials (API key 인증) ──────────────────────────────────────

async def get_agent_by_api_key_hash(key_hash: str) -> asyncpg.Record | None:
    """API key 해시로 에이전트를 조회한다. 매칭 시 (agent_id, principal_id) 반환.

    해시는 발급 시점과 동일한 sha256 hex (AgentService._hash_key)를 전제로 한다.
    """
    return await get_pool().fetchrow(
        "SELECT ac.agent_id, a.principal_id"
        " FROM agent_credentials ac"
        " JOIN agents a USING (agent_id)"
        " WHERE ac.api_key_hash = $1",
        key_hash,
    )


# ── Agents / Principals (B 소유 테이블 — 읽기 전용) ───────────────────────

async def get_agent_row(agent_id: UUID) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.available_timezones, ap.llm_model,"
        " ap.auto_match, ap.task_description,"
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
        " ap.style_vector, ap.available_timezones, ap.llm_model,"
        " ap.auto_match, ap.task_description, ap.capability_embedding,"
        " aper.bio, aper.style_formal, aper.style_verbose, aper.style_bold",
        agent_id,
    )


async def get_all_visible_agents(exclude_agent_id: UUID, exclude_principal_id: UUID) -> list[asyncpg.Record]:
    return await get_pool().fetch(
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.auto_match, ap.task_description,"
        " COALESCE(array_agg(cv.name) FILTER (WHERE cv.name IS NOT NULL), '{}') AS capability_tags"
        " FROM agents a JOIN agent_profiles ap USING (agent_id)"
        " LEFT JOIN agent_capability_tags act USING (agent_id)"
        " LEFT JOIN capability_vocabulary cv USING (tag_id)"
        " WHERE a.agent_id != $1 AND a.principal_id != $2"
        " AND ap.is_suspended = false AND ap.visibility != 'hidden'"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.auto_match, ap.task_description",
        exclude_agent_id,
        exclude_principal_id,
    )


async def get_auto_match_agents() -> list[asyncpg.Record]:
    """auto_match=true인 활성 에이전트 목록 반환 (자율 스와이프 엔진용)."""
    return await get_pool().fetch(
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.auto_match, ap.task_description,"
        " COALESCE(array_agg(cv.name) FILTER (WHERE cv.name IS NOT NULL), '{}') AS capability_tags"
        " FROM agents a JOIN agent_profiles ap USING (agent_id)"
        " LEFT JOIN agent_capability_tags act USING (agent_id)"
        " LEFT JOIN capability_vocabulary cv USING (tag_id)"
        " WHERE ap.auto_match = true AND ap.is_suspended = false AND ap.visibility != 'hidden'"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.auto_match, ap.task_description",
    )


async def get_agents_by_filters(
    exclude_agent_id: UUID,
    *,
    capability_tags: list[str] | None = None,
    trust_min: float | None = None,
    trust_max: float | None = None,
    style: str | None = None,
    domain: str | None = None,
    availability: str | None = None,
    search_q: str | None = None,
) -> list[asyncpg.Record]:
    """필터 조건에 맞는 visible 에이전트를 조회한다 (Discover 검색).

    get_all_visible_agents 의 확장판. 모든 필터는 AND 로 결합되며,
    None 인 필터는 적용하지 않는다. 컬럼명은 하드코딩, 값은 파라미터 바인딩한다.

    - capability_tags: 명시된 모든 태그를 보유한 에이전트만 (AND 매칭)
    - trust_min/max:   agent_profiles.trust_score 범위
    - style:           verbose|concise|formal|casual → style_verbose/style_formal(0~100) 임계값 매핑
    - domain:          agent_personalities.domain_interest 부분일치
    - search_q:        display_name / bio / domain_interest 부분일치
    - availability:    'available' 이면 agent_availability 레코드 존재로 판정(best-effort).
                       busy/offline 은 데이터 모델 부재로 필터링하지 않는다.
    """
    conditions = [
        "a.agent_id != $1",
        "ap.is_suspended = false",
        "ap.visibility != 'hidden'",
    ]
    params: list[Any] = [exclude_agent_id]

    def _ph() -> str:
        """다음에 append 될 파라미터의 플레이스홀더 번호를 반환한다."""
        return f"${len(params) + 1}"

    if trust_min is not None:
        conditions.append(f"ap.trust_score >= {_ph()}")
        params.append(trust_min)
    if trust_max is not None:
        conditions.append(f"ap.trust_score <= {_ph()}")
        params.append(trust_max)

    if style:
        style_map = {
            "verbose": "aper.style_verbose >= 50",
            "concise": "aper.style_verbose < 50",
            "formal": "aper.style_formal >= 50",
            "casual": "aper.style_formal < 50",
        }
        cond = style_map.get(style.lower())
        if cond:
            conditions.append(cond)

    if domain:
        conditions.append(f"aper.domain_interest ILIKE {_ph()}")
        params.append(f"%{domain}%")

    if search_q:
        ph = _ph()
        conditions.append(
            f"(ap.display_name ILIKE {ph} OR aper.bio ILIKE {ph}"
            f" OR aper.domain_interest ILIKE {ph})"
        )
        params.append(f"%{search_q}%")

    if availability and availability.lower() == "available":
        conditions.append(
            "EXISTS (SELECT 1 FROM agent_availability aa WHERE aa.agent_id = a.agent_id)"
        )

    if capability_tags:
        ph = _ph()
        conditions.append(
            "a.agent_id IN ("
            " SELECT act2.agent_id FROM agent_capability_tags act2"
            " JOIN capability_vocabulary cv2 USING (tag_id)"
            f" WHERE cv2.name = ANY({ph})"
            " GROUP BY act2.agent_id"
            f" HAVING COUNT(DISTINCT cv2.name) = array_length({ph}, 1))"
        )
        params.append(capability_tags)

    where_clause = " AND ".join(conditions)
    query = (
        "SELECT a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector,"
        " COALESCE(array_agg(cv.name) FILTER (WHERE cv.name IS NOT NULL), '{}') AS capability_tags"
        " FROM agents a"
        " JOIN agent_profiles ap USING (agent_id)"
        " LEFT JOIN agent_personalities aper USING (agent_id)"
        " LEFT JOIN agent_capability_tags act USING (agent_id)"
        " LEFT JOIN capability_vocabulary cv USING (tag_id)"
        f" WHERE {where_clause}"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url, ap.style_vector"
    )
    return await get_pool().fetch(query, *params)


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


async def upsert_principal(principal_id: UUID, email: str, name: str) -> asyncpg.Record:
    """principals + principal_profiles 에 한 트랜잭션으로 멱등 INSERT 후 레코드 반환."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO principals (principal_id) VALUES ($1)"
                " ON CONFLICT (principal_id) DO NOTHING",
                principal_id,
            )
            await conn.execute(
                "INSERT INTO principal_profiles (principal_id, email, name)"
                " VALUES ($1, $2, $3)"
                " ON CONFLICT (principal_id) DO NOTHING",
                principal_id, email, name,
            )
    return await get_principal_row(principal_id)


async def get_agent_full(agent_id: UUID) -> asyncpg.Record | None:
    """단일 에이전트를 Agent 객체 재구성에 필요한 전체 personality 필드와 함께 반환."""
    return await get_pool().fetchrow(
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
        " WHERE a.agent_id = $1"
        " GROUP BY a.agent_id, a.principal_id, ap.display_name, ap.visibility,"
        " ap.trust_score, ap.tier_badge, ap.date_count, ap.avatar_url,"
        " ap.style_vector, ap.available_timezones, ap.llm_model,"
        " aper.bio, aper.style_formal, aper.style_verbose, aper.style_bold,"
        " aper.thinking_style, aper.values, aper.conflict_style,"
        " aper.collaboration_goal, aper.domain_interest, aper.system_prompt_cache",
        agent_id,
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
    auto_match: bool = False,
    task_description: str = "",
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
                "  style_vector, available_timezones, auto_match, task_description)"
                " VALUES ($1, $2, $3, $4::visibility_enum, $5, $6::jsonb, $7, $8, $9)",
                agent_id, display_name, avatar_url or None, visibility.lower(),
                llm_model, _json.dumps(style_vector), available_timezones,
                auto_match, task_description,
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
    auto_match: bool = False,
    task_description: str = "",
) -> None:
    """에이전트 수정 시 agent_profiles + agent_personalities를 트랜잭션으로 갱신."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE agent_profiles"
                " SET display_name=$2, avatar_url=$3, visibility=$4::visibility_enum,"
                "     llm_model=$5, style_vector=$6::jsonb, available_timezones=$7,"
                "     auto_match=$8, task_description=$9, updated_at=now()"
                " WHERE agent_id=$1",
                agent_id, display_name, avatar_url or None, visibility.lower(),
                llm_model, _json.dumps(style_vector), available_timezones,
                auto_match, task_description,
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


# ── Ratings ───────────────────────────────────────────────────────────────

async def insert_rating(
    date_id: UUID,
    rater_principal_id: UUID,
    rated_agent_id: UUID,
    stars: int,
    compatibility: float,
) -> None:
    # compatibility는 0~1 float → DB는 smallint 1~5이므로 변환
    compat_int = max(1, min(5, round(compatibility * 5)))
    await get_pool().execute(
        "INSERT INTO ratings (date_id, rater_principal_id, rated_agent_id, stars, compatibility)"
        " VALUES ($1, $2, $3, $4, $5)"
        " ON CONFLICT (date_id, rater_principal_id, rated_agent_id) DO NOTHING",
        date_id, rater_principal_id, rated_agent_id, stars, compat_int,
    )


# ── Relationships ─────────────────────────────────────────────────────────

async def upsert_relationship(
    agent_a_id: UUID,
    agent_b_id: UUID,
    successful_dates: int,
    avg_rating: float,
    tier: str,
) -> None:
    # CHECK 제약: agent_a_id < agent_b_id
    a, b = (agent_a_id, agent_b_id) if str(agent_a_id) < str(agent_b_id) else (agent_b_id, agent_a_id)
    await get_pool().execute(
        "INSERT INTO relationships (agent_a_id, agent_b_id, successful_dates, avg_rating, tier)"
        " VALUES ($1, $2, $3, $4, $5::tier_enum)"
        " ON CONFLICT (agent_a_id, agent_b_id) DO UPDATE"
        "   SET successful_dates = $3, avg_rating = $4, tier = $5::tier_enum, updated_at = now()",
        a, b, successful_dates, avg_rating, tier.lower(),
    )


async def upsert_trust_score(
    agent_id: UUID,
    composite: float | None,
    peer_ratings_avg: float,
    data_point_count: int,
) -> None:
    await get_pool().execute(
        "INSERT INTO trust_scores (agent_id, composite, peer_ratings_avg, data_point_count)"
        " VALUES ($1, $2, $3, $4)"
        " ON CONFLICT (agent_id) DO UPDATE"
        "   SET composite = $2, peer_ratings_avg = $3,"
        "       data_point_count = $4, last_calculated_at = now()",
        agent_id, composite, peer_ratings_avg, data_point_count,
    )


async def update_agent_tier(agent_id: UUID, tier: str) -> None:
    await get_pool().execute(
        "UPDATE agent_profiles SET tier_badge = $1::tier_enum WHERE agent_id = $2",
        tier.lower(), agent_id,
    )


async def insert_date_with_id(
    date_id: UUID,
    match_id: UUID,
    date_type: str | None = None,
) -> asyncpg.Record:
    """DateSession이 내부적으로 생성한 date_id를 그대로 DB에 삽입한다."""
    return await get_pool().fetchrow(
        "INSERT INTO dates (date_id, match_id, type) VALUES ($1, $2, $3) RETURNING *",
        date_id, match_id, date_type,
    )


async def get_relationships_for_agent(agent_id: UUID) -> list[asyncpg.Record]:
    return await get_pool().fetch(
        "SELECT r.*,"
        " CASE WHEN r.agent_a_id = $1 THEN r.agent_b_id ELSE r.agent_a_id END AS partner_id,"
        " ap.display_name AS partner_name, ap.avatar_url AS partner_avatar,"
        " ap.trust_score AS partner_trust_score,"
        " m.match_id"
        " FROM relationships r"
        " JOIN agent_profiles ap"
        "   ON ap.agent_id = CASE WHEN r.agent_a_id = $1 THEN r.agent_b_id ELSE r.agent_a_id END"
        " LEFT JOIN matches m"
        "   ON (m.agent_a_id = r.agent_a_id AND m.agent_b_id = r.agent_b_id)"
        "   OR (m.agent_a_id = r.agent_b_id AND m.agent_b_id = r.agent_a_id)"
        " WHERE r.agent_a_id = $1 OR r.agent_b_id = $1"
        " ORDER BY r.tier DESC, r.updated_at DESC",
        agent_id,
    )


# ── Analytics ─────────────────────────────────────────────────────────────

async def get_analytics_date_stats(agent_id: UUID, since_dt) -> asyncpg.Record | None:
    """에이전트가 참여한 dates의 통계."""
    return await get_pool().fetchrow(
        "SELECT"
        " COUNT(*) FILTER (WHERE d.ended_at IS NOT NULL) AS total_dates,"
        " COUNT(*) FILTER (WHERE d.outcome = 'completed') AS successful_dates,"
        " ROUND(AVG(r.stars)::numeric, 2) AS avg_stars,"
        " COUNT(*) FILTER (WHERE d.type = 'coffee_chat') AS coffee_chat_count,"
        " COUNT(*) FILTER (WHERE d.type = 'deep_dive') AS deep_dive_count,"
        " COUNT(*) FILTER (WHERE d.type = 'activity_date') AS activity_date_count"
        " FROM dates d"
        " JOIN matches m ON m.match_id = d.match_id"
        " LEFT JOIN ratings r ON r.date_id = d.date_id AND r.rated_agent_id = $1"
        " WHERE (m.agent_a_id = $1 OR m.agent_b_id = $1)"
        "   AND ($2::timestamptz IS NULL OR d.created_at >= $2)",
        agent_id, since_dt,
    )


async def get_analytics_relationship_tiers(agent_id: UUID) -> list[asyncpg.Record]:
    """에이전트의 관계 티어 현황."""
    return await get_pool().fetch(
        "SELECT tier, COUNT(*) AS count"
        " FROM relationships"
        " WHERE agent_a_id = $1 OR agent_b_id = $1"
        " GROUP BY tier",
        agent_id,
    )


async def get_analytics_recent_dates(agent_id: UUID, since_dt, limit: int = 10) -> list[asyncpg.Record]:
    """최근 데이트 이력 (신뢰 점수 추이용)."""
    return await get_pool().fetch(
        "SELECT d.ended_at, r.stars, r.compatibility"
        " FROM dates d"
        " JOIN matches m ON m.match_id = d.match_id"
        " LEFT JOIN ratings r ON r.date_id = d.date_id AND r.rated_agent_id = $1"
        " WHERE (m.agent_a_id = $1 OR m.agent_b_id = $1)"
        "   AND d.ended_at IS NOT NULL"
        "   AND ($2::timestamptz IS NULL OR d.created_at >= $2)"
        " ORDER BY d.ended_at DESC LIMIT $3",
        agent_id, since_dt, limit,
    )
