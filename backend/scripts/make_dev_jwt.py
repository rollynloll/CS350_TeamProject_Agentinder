#!/usr/bin/env python3
"""개발용 Supabase 호환 JWT 생성기 (HS256).

백엔드 AuthMiddleware(`app/auth/auth_middleware.py`)가 SUPABASE_JWT_SECRET 으로
검증하는 JWT를 만든다. 프론트 OAuth 로그인 UI가 비활성인 상태에서 real 백엔드를
테스트할 때, VITE_DEV_JWT 로 주입할 토큰을 발급하는 용도다.

사용법 (backend 디렉토리에서 venv 활성화 후 실행):
    python scripts/make_dev_jwt.py                       # 새 UUID로 발급
    python scripts/make_dev_jwt.py --email me@test.com   # email 지정
    python scripts/make_dev_jwt.py --sub <uuid>          # 기존 principal 재사용
    python scripts/make_dev_jwt.py --ttl 604800          # 만료 7일

시크릿 우선순위: --secret > 환경변수 SUPABASE_JWT_SECRET > backend/.env
출력된 VITE_DEV_JWT / VITE_DEV_PRINCIPAL_ID 두 줄을 frontend/.env.local 에 붙여넣는다.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

from jose import jwt

try:
    from dotenv import dotenv_values
except ImportError:  # python-dotenv 미설치 환경 방어
    dotenv_values = None


def resolve_secret(cli_secret: str | None) -> str:
    """--secret → 환경변수 → backend/.env 순으로 JWT 시크릿을 찾는다."""
    if cli_secret:
        return cli_secret
    env_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if env_secret:
        return env_secret
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if dotenv_values and env_path.is_file():
        values = dotenv_values(env_path)
        secret = values.get("SUPABASE_JWT_SECRET")
        if secret:
            return secret
    sys.exit(
        "ERROR: SUPABASE_JWT_SECRET 을 찾을 수 없습니다.\n"
        "  --secret 옵션, 환경변수 SUPABASE_JWT_SECRET, 또는 backend/.env 중 하나로 제공하세요."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="개발용 Supabase 호환 JWT 생성기")
    parser.add_argument("--email", default="dev@agentinder.io", help="JWT email 클레임")
    parser.add_argument("--sub", default=None, help="principal_id(UUID). 미지정 시 새로 생성")
    parser.add_argument("--ttl", type=int, default=86400, help="만료(초), 기본 1일")
    parser.add_argument("--secret", default=None, help="서명 시크릿(미지정 시 env/.env)")
    args = parser.parse_args()

    secret = resolve_secret(args.secret)
    sub = args.sub or str(uuid.uuid4())
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": args.email,
        "role": "authenticated",
        "aud": "authenticated",  # 백엔드는 verify_aud=False 이지만 Supabase 규약과 맞춤
        "iat": now,
        "exp": now + args.ttl,
        "session_id": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    # stdout: .env에 그대로 붙여넣을 두 줄
    print("# ── frontend/.env.local 에 붙여넣기 ──────────────────────────")
    print(f"VITE_DEV_JWT={token}")
    print(f"VITE_DEV_PRINCIPAL_ID={sub}")
    # stderr: 사람이 읽는 요약 (파이프/복사에 안 섞이도록 분리)
    print(f"\n# sub(principal_id) = {sub}", file=sys.stderr)
    print(f"# email             = {args.email}", file=sys.stderr)
    print(f"# expires in        = {args.ttl}s", file=sys.stderr)


if __name__ == "__main__":
    main()
