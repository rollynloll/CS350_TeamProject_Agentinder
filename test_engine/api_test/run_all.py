"""
API Test Engine — 전체 스위트 러너
Usage: python test_engine/api_test/run_all.py

사전 조건:
  - backend Docker 실행 중: cd backend && docker-compose up --build
  - backend/.env 에 SUPABASE_JWT_SECRET 설정됨
  - (선택) websockets 설치: pip install websockets  ← 3-6·3-7 WS 테스트에 필요

실행 순서: S1 → S2 → S3 (각 파일은 독립 프로세스, setup 자체 포함)

미구현 API (스킵):
  2-4  Free tier 5개 초과     — 에이전트 5개 사전 생성 필요, 수동 검증
  3-10 No-show 자동 타임아웃  — SQL 직접 조작만 가능
  4-2~4-4 Trust Score 이력   — trust_data_points DB 직접 확인
  5-1~5-4 Relationship 단계  — relationships DB 직접 확인
  7    AI 주도 자동 매칭      — 엔드포인트 미구현
"""
import sys
import os
import subprocess
import glob

API_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    test_files = sorted(glob.glob(os.path.join(API_TEST_DIR, "test_s*.py")))
    if not test_files:
        print("test_s*.py 파일을 찾을 수 없습니다.")
        sys.exit(1)

    total_pass = total_fail = 0
    results: list[tuple[str, str, int, int]] = []

    print("=" * 60)
    print("API TEST ENGINE")
    print(f"Backend: http://localhost:8000")
    print("=" * 60)

    for tf in test_files:
        suite_name = os.path.basename(tf).replace(".py", "").upper().replace("TEST_", "")
        result = subprocess.run(
            [sys.executable, tf],
            capture_output=True, text=True,
        )
        output = result.stdout + result.stderr
        print(output, end="")

        p = output.count("  PASS  ")
        f = output.count("  FAIL  ") + output.count("  ERROR ")
        total_pass += p
        total_fail += f

        status = "PASS" if result.returncode == 0 else "FAIL"
        results.append((suite_name, status, p, f))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, status, p, f in results:
        badge = "✅" if status == "PASS" else "❌"
        print(f"  {badge} {name:<35} {p} passed, {f} failed")
    print("-" * 60)
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
    print("=" * 60)

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
