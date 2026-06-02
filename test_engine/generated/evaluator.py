"""
Assignment 4 Experiment Evaluator
Evaluates each generated level_N_attempt_M.py against level-specific test cases.
Test cases derived from SRS requirements (no ground truth in generation prompts).
"""
import sys, os, importlib.util, math, traceback

GENERATED_DIR = os.path.dirname(__file__)
TOL = 0.001


def load_function(filepath):
    spec = importlib.util.spec_from_file_location("generated_module", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.compute_compatibility_score


def check(label, got, expected, tol=TOL):
    if isinstance(expected, float):
        ok = abs(got - expected) <= tol
    else:
        ok = (got == expected)
    if ok:
        return True, f"    PASS  {label}"
    else:
        return False, f"    FAIL  {label} — got={got!r}, expected={expected!r}"


# ---------------------------------------------------------------------------
# Level-specific test suites
# ---------------------------------------------------------------------------

def level_1_tests(fn):
    """REQ-0202: Jaccard similarity only. Returns float."""
    cases = [
        ("identical tags", {"tags": ["a","b","c"]}, {"tags": ["a","b","c"]}, 1.0),
        ("partial overlap 2/6", {"tags": ["a","b","c","d"]}, {"tags": ["a","b","e","f"]}, 2/6),
        ("no overlap", {"tags": ["a","b"]}, {"tags": ["c","d"]}, 0.0),
        ("both empty", {"tags": []}, {"tags": []}, 0.0),
        ("one empty", {"tags": ["a"]}, {"tags": []}, 0.0),
        ("single shared tag", {"tags": ["x","y"]}, {"tags": ["x"]}, 1/2),
    ]
    results = []
    for label, a, b, exp in cases:
        try:
            got = fn(a, b)
            ok, msg = check(label, got, float(exp))
            results.append((ok, msg))
        except Exception as e:
            results.append((False, f"    ERROR {label}: {e}"))
    return results


def level_2_tests(fn):
    """REQ-0202+0203: Jaccard + Style. Weights 0.7/0.3. Returns float."""
    cases = [
        ("same tags same style", {"tags":["a"], "style":{"f":0.8}},
                                  {"tags":["a"], "style":{"f":0.8}}, 0.7*1.0 + 0.3*1.0),
        ("same tags style dist=1", {"tags":["a"], "style":{"f":1.0}},
                                    {"tags":["a"], "style":{"f":0.0}}, 0.7*1.0 + 0.3*(1/(1+1))),
        ("no tags same style", {"tags":[], "style":{"f":0.5}},
                                {"tags":[], "style":{"f":0.5}}, 0.7*0.0 + 0.3*1.0),
        ("no tags style dist=1", {"tags":[], "style":{"f":1.0}},
                                  {"tags":[], "style":{"f":0.0}}, 0.7*0.0 + 0.3*0.5),
    ]
    results = []
    for label, a, b, exp in cases:
        try:
            got = fn(a, b)
            ok, msg = check(label, got, exp)
            results.append((ok, msg))
        except Exception as e:
            results.append((False, f"    ERROR {label}: {e}"))
    return results


def level_3_tests(fn):
    """REQ-0201: Full formula 0.50*cap + 0.20*style + 0.30*trust. Returns float."""
    cases = [
        ("all max", {"tags":["a"], "style":{}, "trust":0.0},
                    {"tags":["a"], "style":{}, "trust":1.0},
                    0.50*1.0 + 0.20*1.0 + 0.30*1.0),
        ("zero trust", {"tags":["a"], "style":{"f":0.5}, "trust":0.0},
                        {"tags":["a"], "style":{"f":0.5}, "trust":0.0},
                        0.50*1.0 + 0.20*1.0 + 0.30*0.0),
        ("no tags trust 0.5", {"tags":[], "style":{}, "trust":0.0},
                               {"tags":[], "style":{}, "trust":0.5},
                               0.50*0.0 + 0.20*1.0 + 0.30*0.5),
        ("partial cap trust 0.8", {"tags":["a","b"], "style":{}, "trust":0.0},
                                   {"tags":["a","c"], "style":{}, "trust":0.8},
                                   0.50*(1/3) + 0.20*1.0 + 0.30*0.8),
    ]
    results = []
    for label, a, b, exp in cases:
        try:
            got = fn(a, b)
            ok, msg = check(label, got, exp)
            results.append((ok, msg))
        except Exception as e:
            results.append((False, f"    ERROR {label}: {e}"))
    return results


def level_4_tests(fn):
    """REQ-0206: New agent branching. Returns float."""
    _cap_w = 0.50/0.70
    _sty_w = 0.20/0.70
    cases = [
        ("new agent (dc=0): trust excluded, re-normalized",
         {"tags":["a"], "style":{}, "trust":0.0, "date_count":10},
         {"tags":["a"], "style":{}, "trust":0.9, "date_count":0},
         _cap_w*1.0 + _sty_w*1.0),
        ("new agent dc=4: same as dc=0",
         {"tags":["a","b"], "style":{}, "trust":0.0, "date_count":10},
         {"tags":["a","b"], "style":{}, "trust":0.9, "date_count":4},
         _cap_w*1.0 + _sty_w*1.0),
        ("experienced (dc=5): uses trust",
         {"tags":["a"], "style":{}, "trust":0.0, "date_count":10},
         {"tags":["a"], "style":{}, "trust":0.8, "date_count":5},
         0.50*1.0 + 0.20*1.0 + 0.30*0.8),
        ("experienced no overlap",
         {"tags":["a"], "style":{}, "trust":0.0, "date_count":10},
         {"tags":["b"], "style":{}, "trust":0.5, "date_count":10},
         0.50*0.0 + 0.20*1.0 + 0.30*0.5),
    ]
    results = []
    for label, a, b, exp in cases:
        try:
            got = fn(a, b)
            ok, msg = check(label, got, exp)
            results.append((ok, msg))
        except Exception as e:
            results.append((False, f"    ERROR {label}: {e}"))
    return results


def level_5_tests(fn):
    """Same as level 4 but formula in prompt is explicit."""
    return level_4_tests(fn)


def level_6_tests(fn):
    """REQ-0201: Returns dict with total, capability, style, trust."""
    _cap_w = 0.50/0.70
    _sty_w = 0.20/0.70

    def run(a, b):
        result = fn(a, b)
        if not isinstance(result, dict):
            raise TypeError(f"Expected dict, got {type(result)}")
        return result

    cases = [
        ("required keys present", {"tags":["a"], "style":{}, "trust":0.8, "date_count":10},
                                   {"tags":["a"], "style":{}, "trust":0.8, "date_count":10},
                                   None),
        ("new agent trust=0.0", {"tags":["a"], "style":{}, "trust":0.0, "date_count":0},
                                  {"tags":["a"], "style":{}, "trust":0.9, "date_count":0},
                                  None),
        ("total clamped", {"tags":["a"], "style":{}, "trust":0.0, "date_count":10},
                           {"tags":["a"], "style":{}, "trust":1.0, "date_count":10},
                           None),
    ]

    results = []
    # Test 1: required keys
    try:
        a = {"tags":["a"], "style":{}, "trust":0.8, "date_count":10}
        b = {"tags":["a"], "style":{}, "trust":0.8, "date_count":10}
        r = run(a, b)
        req_keys = {"total", "capability", "style", "trust"}
        missing = req_keys - set(r.keys())
        ok = len(missing) == 0
        results.append((ok, f"    {'PASS' if ok else 'FAIL'}  required keys present (missing: {missing})"))
    except Exception as e:
        results.append((False, f"    ERROR required_keys: {e}"))

    # Test 2: new agent trust=0.0
    try:
        a = {"tags":["a"], "style":{}, "trust":0.0, "date_count":0}
        b = {"tags":["a"], "style":{}, "trust":0.9, "date_count":0}
        r = run(a, b)
        ok, msg = check("new agent: trust=0.0 in dict", r.get('trust'), 0.0)
        results.append((ok, msg))
    except Exception as e:
        results.append((False, f"    ERROR new_agent_trust: {e}"))

    # Test 3: total is float in [0,1]
    try:
        a = {"tags":["a"], "style":{}, "trust":0.0, "date_count":10}
        b = {"tags":["a"], "style":{}, "trust":1.0, "date_count":10}
        r = run(a, b)
        total = r.get('total')
        ok = isinstance(total, float) and 0.0 <= total <= 1.0
        results.append((ok, f"    {'PASS' if ok else 'FAIL'}  total in [0,1]: {total}"))
    except Exception as e:
        results.append((False, f"    ERROR total_bounds: {e}"))

    # Test 4: capability matches Jaccard
    try:
        a = {"tags":["a","b","c","d"], "style":{}, "trust":0.0, "date_count":10}
        b = {"tags":["a","b","e","f"], "style":{}, "trust":0.5, "date_count":10}
        r = run(a, b)
        ok, msg = check("capability = Jaccard 2/6", r.get('capability'), 2/6)
        results.append((ok, msg))
    except Exception as e:
        results.append((False, f"    ERROR capability: {e}"))

    # Test 5: total correct for experienced agent
    try:
        a = {"tags":["a"], "style":{}, "trust":0.0, "date_count":10}
        b = {"tags":["a"], "style":{}, "trust":0.6, "date_count":10}
        r = run(a, b)
        expected = 0.50*1.0 + 0.20*1.0 + 0.30*0.6
        ok, msg = check("total correct experienced", r.get('total'), expected)
        results.append((ok, msg))
    except Exception as e:
        results.append((False, f"    ERROR total_experienced: {e}"))

    return results


def level_7_tests(fn):
    """Level 6 + common_tags + complementary_tags in return dict."""
    results = level_6_tests(fn)

    # Additional: common_tags and complementary_tags
    try:
        a = {"tags":["a","b","c"], "style":{}, "trust":0.0, "date_count":10}
        b = {"tags":["a","b","d"], "style":{}, "trust":0.5, "date_count":10}
        r = fn(a, b)
        if not isinstance(r, dict):
            results.append((False, "    ERROR common_tags: result not dict"))
            return results
        ok_common = (r.get('common_tags') == ["a","b"])
        ok_comp = (r.get('complementary_tags') == ["c","d"])
        results.append((ok_common, f"    {'PASS' if ok_common else 'FAIL'}  common_tags=['a','b'] got={r.get('common_tags')}"))
        results.append((ok_comp, f"    {'PASS' if ok_comp else 'FAIL'}  complementary_tags=['c','d'] got={r.get('complementary_tags')}"))
    except Exception as e:
        results.append((False, f"    ERROR tag_lists: {e}"))

    # Empty tags common_tags/complementary_tags
    try:
        a = {"tags":[], "style":{}, "trust":0.0, "date_count":10}
        b = {"tags":[], "style":{}, "trust":0.5, "date_count":10}
        r = fn(a, b)
        ok = (r.get('common_tags') == [] and r.get('complementary_tags') == [])
        results.append((ok, f"    {'PASS' if ok else 'FAIL'}  empty tags → empty tag lists"))
    except Exception as e:
        results.append((False, f"    ERROR empty_tags: {e}"))

    return results


def level_8_tests(fn):
    """Level 7 + trust=None handling + style_diff dict."""
    results = level_7_tests(fn)

    # trust=None treated as new agent
    try:
        a = {"tags":["a"], "style":{}, "trust":None, "date_count":10}
        b = {"tags":["a"], "style":{}, "trust":None, "date_count":10}
        r = fn(a, b)
        if not isinstance(r, dict):
            results.append((False, "    ERROR trust_none: result not dict"))
            return results
        ok = (r.get('trust') == 0.0)
        results.append((ok, f"    {'PASS' if ok else 'FAIL'}  trust=None → trust=0.0 in result"))
    except Exception as e:
        results.append((False, f"    ERROR trust_none: {e}"))

    # style_diff returned
    try:
        a = {"tags":["a"], "style":{"formality": 0.8}, "trust":0.5, "date_count":10}
        b = {"tags":["a"], "style":{"formality": 0.3}, "trust":0.5, "date_count":10}
        r = fn(a, b)
        sd = r.get('style_diff')
        ok = isinstance(sd, dict) and abs(sd.get('formality', -1) - 0.5) < TOL
        results.append((ok, f"    {'PASS' if ok else 'FAIL'}  style_diff['formality']=0.5 got={sd}"))
    except Exception as e:
        results.append((False, f"    ERROR style_diff: {e}"))

    # total clamped when all max
    try:
        a = {"tags":["a"], "style":{}, "trust":None, "date_count":10}
        b = {"tags":["a"], "style":{}, "trust":1.0, "date_count":10}
        r = fn(a, b)
        total = r.get('total', -1)
        ok = (0.0 <= total <= 1.0)
        results.append((ok, f"    {'PASS' if ok else 'FAIL'}  total clamped to [0,1]: {total}"))
    except Exception as e:
        results.append((False, f"    ERROR clamping: {e}"))

    return results


def level_9_tests(fn):
    """Level 7 requirements + ambiguous re-normalization via natural language prompt."""
    results = level_7_tests(fn)
    _cap_w = 0.50 / 0.70
    _sty_w = 0.20 / 0.70

    # Critical: new agent total must use re-normalized weights, not raw 0.50/0.20
    try:
        a = {"tags":["a","b"], "style":{}, "trust":0.0, "date_count":10}
        b = {"tags":["a","b"], "style":{}, "trust":0.9, "date_count":0}
        r = fn(a, b)
        got_total = r.get('total') if isinstance(r, dict) else r
        expected = min(1.0, _cap_w * 1.0 + _sty_w * 1.0)  # 1.0
        ok, msg = check("new agent total uses re-normalized weights (5/7, 2/7)", got_total, expected)
        results.append((ok, msg))
    except Exception as e:
        results.append((False, f"    ERROR new_agent_renorm_total: {e}"))

    try:
        a = {"tags":["a"], "style":{"f":0.8}, "trust":0.0, "date_count":10}
        b = {"tags":["b"], "style":{"f":0.0}, "trust":0.9, "date_count":0}
        r = fn(a, b)
        got_total = r.get('total') if isinstance(r, dict) else r
        dist = abs(0.8 - 0.0)
        style_s = 1.0/(1.0+dist)
        expected = _cap_w * 0.0 + _sty_w * style_s
        ok, msg = check("new agent: no tags, style dist=0.8", got_total, expected)
        results.append((ok, msg))
    except Exception as e:
        results.append((False, f"    ERROR new_agent_style_only: {e}"))

    return results


def level_10_tests(fn):
    """Level 9 + 'redistribute weight proportionally' phrasing from stakeholder."""
    results = level_9_tests(fn)

    # Test that redistribution gives same result as re-normalization
    _cap_w = 0.50 / 0.70
    _sty_w = 0.20 / 0.70
    try:
        a = {"tags":["a","b"], "style":{"f":0.6}, "trust":0.0, "date_count":10}
        b = {"tags":["a","c"], "style":{"f":0.6}, "trust":None, "date_count":10}
        r = fn(a, b)
        got = r.get('total') if isinstance(r, dict) else r
        cap = 1/3
        style_s = 1.0
        expected = min(1.0, _cap_w * cap + _sty_w * style_s)
        ok, msg = check("redistribute=renormalize: trust=None treated as new agent", got, expected)
        results.append((ok, msg))
    except Exception as e:
        results.append((False, f"    ERROR redistribute: {e}"))

    return results


LEVEL_TEST_MAP = {
    1: level_1_tests,
    2: level_2_tests,
    3: level_3_tests,
    4: level_4_tests,
    5: level_5_tests,
    6: level_6_tests,
    7: level_7_tests,
    8: level_8_tests,
    9: level_9_tests,
    10: level_10_tests,
}


def evaluate_level(level_num, attempt_num):
    filepath = os.path.join(GENERATED_DIR, f"level_{level_num}_attempt_{attempt_num}.py")
    if not os.path.exists(filepath):
        return None, None, "FILE_NOT_FOUND"

    try:
        fn = load_function(filepath)
    except Exception as e:
        return 0, 0, f"LOAD_ERROR: {e}"

    test_fn = LEVEL_TEST_MAP.get(level_num)
    if not test_fn:
        return None, None, "NO_TESTS"

    results = test_fn(fn)
    passed = sum(1 for ok, _ in results if ok)
    failed = sum(1 for ok, _ in results if not ok)
    msgs = [msg for _, msg in results]
    return passed, failed, msgs


def main():
    print("=" * 60)
    print("ASSIGNMENT 4 EXPERIMENT — EVALUATOR")
    print("=" * 60)

    summary = []
    decisions_entries = []
    prev_failed = False

    for level in range(1, 11):
        print(f"\n--- Level {level} ---")
        all_passed = True
        final_attempt = None

        for attempt in range(1, 3):
            filepath = os.path.join(GENERATED_DIR, f"level_{level}_attempt_{attempt}.py")
            if not os.path.exists(filepath):
                break
            print(f"  [Attempt {attempt}]")
            p, f, msgs = evaluate_level(level, attempt)

            if msgs == "FILE_NOT_FOUND":
                break
            if isinstance(msgs, str):
                print(f"  ERROR: {msgs}")
                all_passed = False
                final_attempt = attempt
                break

            for msg in msgs:
                print(msg)

            if f == 0:
                print(f"  → Level {level} Attempt {attempt}: PASS ({p}/{p+f})")
                # Update file header with result
                _update_result(filepath, "PASS")
                all_passed = True
                final_attempt = attempt
                break
            else:
                print(f"  → Level {level} Attempt {attempt}: FAIL ({p}/{p+f} passed)")
                _update_result(filepath, f"FAIL ({p}/{p+f} passed)")
                all_passed = False
                final_attempt = attempt
                decisions_entries.append(
                    f"Level {level} Attempt {attempt}: FAIL — {f} test(s) failed"
                )

        result_str = "PASS" if all_passed else f"FAIL (all {final_attempt} attempt(s))"
        summary.append((level, result_str, final_attempt))

        if not all_passed:
            if prev_failed:
                print(f"\n⚠ Two consecutive level failures — experiment complete at Level {level}")
                break
            prev_failed = True
        else:
            prev_failed = False

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Level':<8} {'Result':<30} {'Attempts'}")
    print("-" * 50)
    for level, result, attempts in summary:
        badge = "✅" if "PASS" in result else "❌"
        print(f"  {badge} L{level:<6} {result:<30} {attempts}")

    return summary, decisions_entries


def _update_result(filepath, result):
    with open(filepath, 'r') as f:
        content = f.read()
    content = content.replace("Result: (evaluated after run)", f"Result: {result}")
    with open(filepath, 'w') as f:
        f.write(content)


if __name__ == "__main__":
    summary, entries = main()
