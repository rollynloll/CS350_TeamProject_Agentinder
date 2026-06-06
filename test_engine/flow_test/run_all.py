"""
Flow Test 전체 실행기
Usage:
  python test_engine/flow_test/run_all.py           # S1→S2→S3→S4 전체
  python test_engine/flow_test/run_all.py --from s3 # S3부터 재개 (기존 state 로드)
  python test_engine/flow_test/run_all.py --only s2 # S2만 실행

사전 조건:
  - backend Docker 실행 중 (docker-compose up --build -d)
  - pip install websockets   (WS 데이트 세션 필요 시)
  - backend/.env에 SUPABASE_JWT_SECRET, OPENAI_API_KEY 설정

상태 파일: test_engine/flow_test/flow_state.json
  각 시나리오 완료 후 자동 저장 → --from 옵션으로 중간부터 재개 가능
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from helpers import (
    empty_state, load_state, save_state, make_logger,
    api_get, HAS_WS,
)
import s1_onboarding
import s2_async_dating
import s3_discover
import s4_sync_dating

log = make_logger("run_all")

SCENARIOS = {
    "s1": ("S1: 온보딩",       s1_onboarding.run),
    "s2": ("S2: 비동기 데이트", s2_async_dating.run),
    "s3": ("S3: 탐색",         s3_discover.run),
    "s4": ("S4: 동기 데이트",   s4_sync_dating.run),
}
SCENARIO_ORDER = ["s1", "s2", "s3", "s4"]


def _check_backend() -> bool:
    try:
        r = api_get("/healthz")
        return r.status_code == 200
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flow Test 실행기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
S2 매칭 모드 (--s2-mode):
  single   임의의 쌍 1개, 데이트 1회          (빠른 스모크 테스트)
  all_n    전체 24쌍 × --s2-n 회              (커스텀 반복)
  all_10   전체 24쌍 × 10회  [기본값]          (전체 플로우)

예시:
  python run_all.py                          # 전체, all_10
  python run_all.py --s2-mode single         # S2 단일 쌍 테스트
  python run_all.py --s2-mode all_n --s2-n 3 # S2 전체 24쌍 × 3회
  python run_all.py --from s3                # S3부터 재개
        """,
    )
    parser.add_argument("--from",    dest="from_", metavar="SN",
                        help="이 시나리오부터 재개 (기존 state 로드). 예: --from s3")
    parser.add_argument("--only",    dest="only",  metavar="SN",
                        help="이 시나리오만 실행. 예: --only s2")
    parser.add_argument("--s2-mode", dest="s2_mode", default="all_10",
                        choices=["single", "all_n", "all_10"],
                        help="S2 매칭 모드 (기본: all_10)")
    parser.add_argument("--s2-n",    dest="s2_n", type=int, default=1,
                        metavar="N",
                        help="all_n 모드에서 쌍당 데이트 횟수 (기본: 1)")
    args = parser.parse_args()

    # ── 백엔드 연결 확인 ──────────────────────────────────────────────────
    log.info("백엔드 연결 확인 중…")
    if not _check_backend():
        log.error("백엔드에 연결할 수 없습니다 (http://localhost:8000/healthz)")
        log.error("docker-compose up --build -d 를 먼저 실행하세요.")
        sys.exit(1)
    log.info("백엔드 연결 확인 ✓")

    if not HAS_WS:
        log.warning("websockets 미설치 — WS 데이트 세션은 REST-only 모드로 진행됩니다.")
        log.warning("  전체 기능 테스트: pip install websockets")

    # ── 실행할 시나리오 결정 ──────────────────────────────────────────────
    if args.only:
        keys = [args.only.lower()]
        if keys[0] not in SCENARIOS:
            log.error("알 수 없는 시나리오: %s  (s1~s4)", args.only)
            sys.exit(1)
        state = load_state()
        log.info("기존 state 로드 (--only %s)", args.only)
    elif args.from_:
        start_key = args.from_.lower()
        if start_key not in SCENARIO_ORDER:
            log.error("알 수 없는 시나리오: %s  (s1~s4)", args.from_)
            sys.exit(1)
        keys  = SCENARIO_ORDER[SCENARIO_ORDER.index(start_key):]
        state = load_state()
        log.info("기존 state 로드 (--from %s)", args.from_)
    else:
        keys  = SCENARIO_ORDER
        state = empty_state()
        log.info("새 flow test 시작 (전체 실행)")

    # ── 시나리오 순차 실행 ────────────────────────────────────────────────
    results: dict[str, bool] = {}
    t_total = time.time()

    for key in keys:
        name, fn = SCENARIOS[key]
        log.info("\n%s", "=" * 70)
        log.info("실행: %s", name)
        log.info("%s\n", "=" * 70)

        t0 = time.time()
        try:
            # S2는 mode·n 인자 전달
            if key == "s2":
                ok = fn(state, mode=args.s2_mode, n=args.s2_n)
            else:
                ok = fn(state)
        except Exception as e:
            log.exception("%s 실행 중 예외 발생: %s", name, e)
            ok = False

        elapsed = time.time() - t0
        results[key] = ok
        log.info("%s %s (%.1fs)\n", name, "✓" if ok else "✗", elapsed)

        # 상태 저장 (다음 시나리오 재개 가능)
        save_state(state)
        log.info("state 저장 → flow_state.json")

        if not ok and key in ("s1", "s2"):
            log.error("선행 시나리오 실패 — 이후 시나리오 스킵")
            break

    # ── 최종 요약 ─────────────────────────────────────────────────────────
    total_elapsed = time.time() - t_total
    log.info("\n%s", "=" * 70)
    log.info("FLOW TEST 최종 요약  (총 %.1fs)", total_elapsed)
    log.info("%s", "=" * 70)

    for key in keys:
        if key in results:
            badge = "✅" if results[key] else "❌"
            name  = SCENARIOS[key][0]
            log.info("  %s %s", badge, name)

    # 최종 에이전트 상태 출력
    if state.get("users"):
        log.info("\n── 에이전트 최종 상태 ──────────────────────────────────────────")
        for n in range(1, 5):
            user = state["users"].get(str(n), {})
            if not user:
                continue
            jwt     = user["jwt"]
            agent_a = user["agents"].get("a", {}).get("id", "")
            if not agent_a:
                continue
            r = api_get(f"/v1/agents/{agent_a}", jwt)
            if r.status_code == 200:
                d = r.json().get("data", {})
                log.info("  User%d AgentA: date_count=%-3s  tier_badge=%-12s  trust_score=%s",
                         n, d.get("date_count"), d.get("tier_badge"), d.get("trust_score"))

    # 통계
    if state.get("async_matches"):
        log.info("\n  비동기 매치: %d  데이트: %d",
                 len(state["async_matches"]),
                 sum(len(m["dates"]) for m in state["async_matches"]))
    if state.get("sync_matches"):
        log.info("  동기 매치: %d  데이트: %d",
                 len(state["sync_matches"]),
                 sum(len(m["dates"]) for m in state["sync_matches"]))
    log.info("  로그 위치: test_engine/flow_test/logs/")

    all_ok = all(results.values())
    log.info("%s", "=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
