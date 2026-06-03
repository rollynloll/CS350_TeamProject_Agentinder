from __future__ import annotations

from uuid import UUID

from .. import db
from .auth_context import AuthContext


async def check_agent_ownership(ctx: AuthContext, agent_id: UUID) -> None:
    row = await db.get_agent_row(agent_id)
    if row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    if row["principal_id"] != ctx.principal_id:
        raise PermissionError("이 에이전트의 소유자가 아닙니다.")


def check_agent_actor(ctx: AuthContext, agent_id: UUID, agent_row: object) -> None:
    """주어진 agent_id 로 행위(피드 조회·스와이프 등)할 권한이 있는지 검사한다.

    호출 주체에 따라 분기한다. agent_row 는 이미 조회된 레코드(존재 검증 완료)를
    받아 중복 조회를 피한다.

    - role == 'agent' (X-Agent-Key 인증): 본인 에이전트(ctx.agent_id == agent_id)만 허용
    - 그 외 (principal JWT 인증): 소유자(agent_row['principal_id'] == ctx.principal_id)만 허용
    """
    if ctx.is_agent():
        if ctx.agent_id is None or ctx.agent_id != agent_id:
            raise PermissionError("다른 에이전트로는 이 작업을 수행할 수 없습니다.")
        return
    if agent_row["principal_id"] != ctx.principal_id:
        raise PermissionError("이 에이전트의 소유자가 아닙니다.")


async def check_match_participant(ctx: AuthContext, match_id: UUID) -> None:
    row = await db.get_match(match_id)
    if row is None:
        raise KeyError(f"매치를 찾을 수 없습니다: {match_id}")

    agent_a = await db.get_agent_row(row["agent_a_id"])
    agent_b = await db.get_agent_row(row["agent_b_id"])

    participant_principals = {
        r["principal_id"] for r in [agent_a, agent_b] if r is not None
    }
    if ctx.principal_id not in participant_principals:
        raise PermissionError("이 매치의 참여자가 아닙니다.")


async def check_date_participant(ctx: AuthContext, date_id: UUID) -> None:
    row = await db.get_date(date_id)
    if row is None:
        raise KeyError(f"데이트를 찾을 수 없습니다: {date_id}")
    await check_match_participant(ctx, row["match_id"])
