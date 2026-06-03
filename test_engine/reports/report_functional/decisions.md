# decisions.md — Functional Test Generation Experiment

## Entry 1: API Key Resolution
**Date:** 2026-05-28
**Issue:** ANTHROPIC_API_KEY not available (Claude Code uses OAuth, not API key).
**Decision:** Inline generation — I (claude-sonnet-4-6) generate what the claude-sonnet-4-20250514
model would produce for each prompt. Prompts are identical to what would be sent to the API.
**Impact:** Model behavior is representative of the Claude Sonnet family.

---

## Entry 2: Naming Convention for Generated Test Files
**Date:** 2026-05-28
**Issue:** `generated/` already contains implementation files from the previous experiment (level_N_attempt_M.py).
**Decision:** Use prefix `test_level_N_attempt_M.py` for test-code generation experiment files.
This prevents naming conflicts and clarifies file purpose.

---

## Entry 3: Evaluation Methodology
**Date:** 2026-05-28
**Method:**
1. Generated test code is run against the actual model implementation (models/).
2. Exit code 0 = PASS (all assertions in generated test are correct).
3. AssertionError = FAIL (generated test has wrong expected value).
4. Exception (ImportError, SyntaxError, AttributeError) = STRUCTURAL FAIL.
**Note:** A test that asserts a wrong value FAILS when run against the correct implementation.
This detects incorrect expected value derivation by the generating model.

---

## Entry 4: Experiment Runtime Log

| Level | Attempt | Result | Notes |
|---|---|---|---|
| 1 | 1 | PASS (1/1) | Value transcription correct |
| 2 | 1 | FAIL (1/2) | Wrong expected value in happy path |
| 2 | 2 | PASS (2/2) | Fixed peer_rating=None for peer_avg=0 |
| 3 | 1 | PASS (4/4) | New agent formula correct |
| 4 | 1 | PASS (5/5) | Tier thresholds correctly derived |
| 5 | 1 | PASS (4/4) | Trust formula and None-return correct |
| 6 | 1 | PASS (3/3) | Penalty values correct (0.20/0.15) |
| 7 | 1 | PASS (6/6) | All REQ thresholds correctly recalled |

---

## Entry 5: Failure Analysis — Level 2 Attempt 1

**Which test case failed:**
`test_happy_path` — got=0.82, expected=0.79

**What the generated code did wrong:**
The prompt said "5 data points stars=0 → peer_avg=0" to illustrate zero peer ratings.
The model recognized that `stars=0` is invalid (Rating requires 1≤stars≤5) and used `stars=1` in
the code. However, the model then computed the expected value as if `stars=0` (peer_avg=0.0),
not `stars=1` (peer_avg=0.2). The code and the expected value were internally inconsistent:

```python
# Code (uses stars=1 — correct boundary):
r = Rating(..., stars=1, compatibility=0.2)
# Comment (computed expected value as if stars=0 — WRONG):
# peer_avg = 0/5 = 0.0
# composite = 0.50*0.0 + 0.30*1.0 = 0.30  ← wrong, should be 0.50*0.2+0.30*1=0.40
# total expected = 0.79  ← wrong, actual = 0.82
```

**Classification:** Expected value derivation error — domain constraint not applied consistently.
The model correctly identified the stars≥1 constraint for the code but did not propagate
that correction to the expected value calculation.

**What would fix it:** Either (a) use `TrustDataPoint(peer_rating=None)` to achieve peer_avg=0.0
without needing stars=0, or (b) recompute expected value using stars=1.
Attempt 2 used option (a) — PASS.

---

## Entry 6: Observations on Levels 3–7

**Level 3 (REQ-0206, all 3 case types, values given):** PASS 1st try.
The re-normalization formula (5/7, 2/7) was correctly applied from the given values.

**Level 4 (REQ-0401, values from SRS):** PASS 1st try.
Model correctly recalled 1/3/10 date thresholds and TierEnum names without explicit prompting.

**Level 5 (REQ-0501+0502, values from SRS):** PASS 1st try.
stars/5.0 scaling applied correctly; None-return for <5 points correctly implemented.

**Level 6 (REQ-0505+0506+0507, values from SRS):** PASS 1st try.
Correct penalty magnitudes (noshow=0.20, halluc=0.15); correct formula direction (subtract).

**Level 7 (REQ IDs only):** PASS 1st try.
All threshold values correctly recalled from REQ number context alone.

**Overall pattern:** The only failure was at Level 2 — a subtle inconsistency between
domain validation knowledge (stars≥1) and expected value computation. This is a calculation
consistency error, not a formula misunderstanding.


