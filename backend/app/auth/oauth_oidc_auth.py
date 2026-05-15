from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..config import settings


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class OAuthOIDCAuth:
    """Supabase Auth 위임: OAuth 2.0 Authorization Code + PKCE."""

    def __init__(self) -> None:
        self._base = settings.supabase_url.rstrip("/") + "/auth/v1"
        self._headers = {
            "apikey": settings.supabase_anon_key,
            "Content-Type": "application/json",
        }

    async def authorize(self, code: str, code_verifier: str) -> TokenPair:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base}/token",
                params={"grant_type": "pkce"},
                json={"auth_code": code, "code_verifier": code_verifier},
                headers=self._headers,
            )
        if res.status_code != 200:
            raise ValueError(f"OAuth 코드 교환 실패: {res.text}")
        data = res.json()
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base}/token",
                params={"grant_type": "refresh_token"},
                json={"refresh_token": refresh_token},
                headers=self._headers,
            )
        if res.status_code != 200:
            raise ValueError(f"토큰 갱신 실패: {res.text}")
        data = res.json()
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )

    async def revoke(self, access_token: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self._base}/logout",
                headers={**self._headers, "Authorization": f"Bearer {access_token}"},
            )
