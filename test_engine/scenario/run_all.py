"""
Scenario test runner — executes all test_uc_*.py files and reports summary.
Usage: python scenario/run_all.py
"""
import sys, os, subprocess, glob

SCENARIO_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(SCENARIO_DIR, '..', '..'))
sys.path.insert(0, os.path.join(SCENARIO_DIR, '..'))


def main():
    test_files = sorted(glob.glob(os.path.join(SCENARIO_DIR, "test_uc_*.py")))
    if not test_files:
        print("No scenario test files found.")
        sys.exit(1)

    total_pass = total_fail = 0
    results = []

    print("=" * 60)
    print("SCENARIO TEST ENGINE — ALL UC TESTS")
    print("=" * 60)

    for tf in test_files:
        uc_name = os.path.basename(tf).replace(".py", "").upper().replace("TEST_", "")
        result = subprocess.run(
            [sys.executable, tf],
            capture_output=True, text=True
        )
        output = result.stdout + result.stderr
        print(output, end="")

        p = output.count("  PASS  ")
        f = output.count("  FAIL  ") + output.count("  ERROR ")
        total_pass += p
        total_fail += f

        status = "PASS" if result.returncode == 0 else "FAIL"
        results.append((uc_name, status, p, f))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for uc_name, status, p, f in results:
        badge = "✅" if status == "PASS" else "❌"
        print(f"  {badge} {uc_name:<20} {p} passed, {f} failed")
    print("-" * 60)
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
    print("=" * 60)

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
