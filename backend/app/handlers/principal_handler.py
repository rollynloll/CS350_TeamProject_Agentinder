from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import db
from ..auth.auth_context import AuthContext
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth

router = APIRouter(prefix="/v1/principals", tags=["principals"])


class CreatePrincipalRequest(BaseModel):
    name: str | None = None
    email: str | None = None


@router.post("")
async def create_principal(
    body: CreatePrincipalRequest,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """회원 레코드 생성 (로그인 직후 1회 호출, 멱등).

    principals + principal_profiles 테이블에 레코드를 생성한다.
    이미 존재하면 ON CONFLICT DO NOTHING 으로 무시하고 기존 레코드를 반환한다.
    """
    if auth.principal_id is None:
        raise PermissionError("인증 정보가 없습니다.")

    # email 우선순위: JWT 클레임 → 요청 바디
    email: str | None = auth.email or body.email
    if not email:
        raise ValueError("email을 확인할 수 없습니다. (JWT 또는 요청 본문 필요)")

    # name 우선순위: 요청 바디 → email 앞부분 → 기본값
    name: str
    if body.name:
        name = body.name
    elif "@" in email:
        name = email.split("@")[0]
    else:
        name = "New User"

    row = await db.upsert_principal(auth.principal_id, email, name)

    created_at = row["created_at"]
    return envelope(data={
        "principal_id": str(row["principal_id"]),
        "email": row["email"],
        "name": row["name"],
        "plan": str(row["plan"]).upper(),
        "created_at": created_at.isoformat() if created_at is not None else None,
    })
