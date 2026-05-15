from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..auth.error_handler_middleware import envelope
from ..auth.oauth_oidc_auth import OAuthOIDCAuth

router = APIRouter(prefix="/v1/auth", tags=["auth"])
_oauth = OAuthOIDCAuth()


class LoginRequest(BaseModel):
    code: str
    code_verifier: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login")
async def login(body: LoginRequest) -> dict:
    tokens = await _oauth.authorize(body.code, body.code_verifier)
    return envelope(data={
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
    })


@router.post("/refresh")
async def refresh(body: RefreshRequest) -> dict:
    tokens = await _oauth.refresh(body.refresh_token)
    return envelope(data={
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "expires_in": tokens.expires_in,
    })


@router.post("/logout")
async def logout(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        await _oauth.revoke(auth_header[7:])
    return envelope(data={"message": "로그아웃 완료"})
