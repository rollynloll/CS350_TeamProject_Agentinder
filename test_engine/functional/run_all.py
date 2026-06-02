"""
Functional test runner — executes all test_req_*.py files and reports summary.
Usage: python functional/run_all.py
"""
import sys, os, subprocess, importlib, glob

FUNCTIONAL_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(FUNCTIONAL_DIR, '..', '..'))
sys.path.insert(0, os.path.join(FUNCTIONAL_DIR, '..'))

def main():
    test_files = sorted(glob.glob(os.path.join(FUNCTIONAL_DIR, "test_req_*.py")))
    if not test_files:
        print("No test files found.")
        sys.exit(1)

    total_pass = total_fail = 0
    results = []

    print("=" * 60)
    print("FUNCTIONAL TEST ENGINE — ALL REQ TESTS")
    print("=" * 60)

    for tf in test_files:
        req_name = os.path.basename(tf).replace(".py", "").upper().replace("TEST_", "")
        result = subprocess.run(
            [sys.executable, tf],
            capture_output=True, text=True
        )
        output = result.stdout + result.stderr
        print(output, end="")

        # Count PASS/FAIL lines
        p = output.count("  PASS  ")
        f = output.count("  FAIL  ") + output.count("  ERROR ")
        total_pass += p
        total_fail += f

        status = "PASS" if result.returncode == 0 else "FAIL"
        results.append((req_name, status, p, f))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for req_name, status, p, f in results:
        badge = "✅" if status == "PASS" else "❌"
        print(f"  {badge} {req_name:<20} {p} passed, {f} failed")
    print("-" * 60)
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
    print("=" * 60)

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
