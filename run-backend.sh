#!/usr/bin/env bash
#
# Agentinder 백엔드 실행 스크립트
#
#   ./run-backend.sh            # Docker Compose 로 DB + 백엔드 전체 기동 (권장)
#   ./run-backend.sh local      # DB 만 컨테이너로, 백엔드는 uvicorn --reload (개발용)
#   ./run-backend.sh down       # Compose 스택 종료
#
# 백엔드: http://localhost:8000  |  DB: localhost:5432 (postgres + pgvector)

set -euo pipefail

# 스크립트 위치 기준으로 backend 디렉토리 이동 (어디서 실행하든 동작)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/backend"

MODE="${1:-compose}"

case "$MODE" in
  compose)
    echo "▶ Docker Compose: DB + 백엔드 기동 (http://localhost:8000)"
    exec docker compose up --build
    ;;

  local)
    echo "▶ DB 컨테이너 기동..."
    docker compose up -d db

    echo "▶ Python 의존성 설치..."
    pip install -r requirements.txt

    echo "▶ uvicorn 개발 서버 (--reload, http://localhost:8000)"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ;;

  down)
    echo "▶ Compose 스택 종료"
    exec docker compose down
    ;;

  *)
    echo "사용법: $0 [compose|local|down]" >&2
    exit 1
    ;;
esac
