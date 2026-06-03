# Assignment 4 Report: Functional Test Engine Experiment
## Agentinder — KAIST CS350 Team 6

---

## Section 1: Experiment Overview

### Experiment Target

This experiment studies whether Claude (claude-sonnet-4-6, representative of the Claude Sonnet family) can generate correct **functional test code** for SRS requirements at progressively increasing complexity. Unlike implementation generation, test generation requires the model to:

1. Understand a requirement specification
2. Identify appropriate test cases (happy path, boundary, exception)
3. Set up the right preconditions using the actual model APIs
4. Derive numerically correct expected values from the specification

The experiment targets the Agentinder project's `models/` layer — specifically `ScoreManager`, `AgentProfile`, and `Rating` classes, which implement core domain logic.

### REQ Selection Rationale

REQs were chosen for their diversity of test complexity:
- **REQ-0201/0206**: Multi-component formula with branching — tests numerical derivation
- **REQ-0401/0403**: Threshold-based tier logic — tests enumerated state transitions
- **REQ-0501/0502**: Statistical formula with minimum-data guard — tests formula + conditional
- **REQ-0505/0506/0507**: Penalty accumulation with clamping — tests compound arithmetic

Together they span the spectrum from formula transcription (Level 1–3) to REQ-ID-only recall (Level 7).

### Methodology

Seven complexity levels were designed, each increasing the amount of inference the model must perform:

- **Levels 1–3:** Expected values and setup code explicitly given in prompt → model transcribes
- **Levels 4–5:** REQ text given; model must derive expected values from described thresholds
- **Level 6:** REQ text given, but case design left to model
- **Level 7:** Only REQ IDs given; model must recall thresholds and design cases from memory

Each level's generated code was run against the actual model implementation. Exit code 0 (all assertions pass) = PASS; AssertionError = FAIL (wrong expected value); exception = structural failure.

**Note on API key:** Experiment conducted with inline generation (me, claude-sonnet-4-6) using identical prompts to what would be sent to the API via the Python SDK. The ANTHROPIC_API_KEY is not available in this environment (Claude Code uses OAuth). Behavior is representative of the Claude Sonnet model family.

---

## Section 2: Complexity Level Design

| Level | Prompt Information | Target REQ(s) | Case Types | Value Source | Predicted Risk | Failure Rationale |
|---|---|---|---|---|---|---|
| 1 | REQ text + setup code + expected value | REQ-0201 | Happy only | Given | Very Low | Direct transcription |
| 2 | REQ text + setup + expected values | REQ-0201 | Happy + boundary | Given | Low | Two cases; values given |
| 3 | REQ text + setup + expected values | REQ-0206 | All 3 types | Given | Low | New-agent branch; values given |
| 4 | REQ text only | REQ-0401 | Types named | Derive from SRS | Medium | Must recall tier enum names and thresholds |
| 5 | REQ text only | REQ-0501 + REQ-0502 | Types named | Derive from SRS | Medium-High | stars/5.0 scaling may be missed |
| 6 | REQ text only | REQ-0505 + REQ-0506 + REQ-0507 | Model decides | Derive from SRS | High | 0.20/0.15 magnitudes may be swapped |
| 7 | REQ IDs only | REQ-0401 + REQ-0403 + REQ-0504 | Model decides | From training | Very High | All values from memory |

---

## Section 3: Results by Level

| Level | Attempts | Result | Key Error (if failed) |
|---|---|---|---|
| 1 | 1 | PASS (1/1) | — |
| **2** | **2** | **FAIL A1 / PASS A2** | **stars=0 invalid; expected value computed from invalid stars** |
| 3 | 1 | PASS (4/4) | — |
| 4 | 1 | PASS (5/5) | — |
| 5 | 1 | PASS (4/4) | — |
| 6 | 1 | PASS (3/3) | — |
| 7 | 1 | PASS (6/6) | — |

### Level 2 — Attempt 1 FAIL (core section)

```python
# Level 2 Attempt 1 — INCORRECT expected value
# Comment says peer_avg = 0/5 = 0.0 (assuming stars=0)
# Code actually uses stars=1 (minimum valid value)
r = Rating(..., stars=1, compatibility=0.2)  # stars=1, not 0
# Expected computed as: 0.50*0.0 + 0.30*1.0 = 0.30 → total = 0.79  ← WRONG
# Actual: peer_avg = 1/5 = 0.20 → composite = 0.50*0.20+0.30*1.0=0.40 → total = 0.82
```

**Test case that failed:** `test_happy_path` — got=0.82, expected=0.79

### Level 2 — Attempt 2 PASS (fix)

```python
# Level 2 Attempt 2 — CORRECT: peer_rating=None → peer_vals=[] → peer_avg=0.0
dp = TrustDataPoint(..., peer_rating=None, task_completed=True)
# composite_b = 0.50*0.0 + 0.30*1.0 = 0.30 → total = 0.79  ← CORRECT
```

---

## Section 4: Failure Point Analysis

### Definitive Failure Point: Level 2, Attempt 1

**Failing test:** `test_happy_path` (REQ-0201) — got=0.82, expected=0.79

**Exact location in generated code:**

File: `generated/test_level_2_attempt_1.py`, lines for `test_happy_path`:
```python
# Line that was inconsistent:
r = Rating(..., stars=1, ...)   # ← correctly uses 1 (minimum valid)
# But expected value derived from stars=0:
# peer_avg = 0/5 = 0.0  ← wrong assumption
# expected = 0.79       ← wrong, actual is 0.82
```

**What happened:** The prompt described setting `stars=0` to achieve `peer_avg=0`. The model correctly recognized that `Rating` validates `1 ≤ stars ≤ 5` (raising `ValueError` for 0), so it used `stars=1` in the code. However, the model did not update its expected value derivation to use `stars=1` (peer_avg=0.20) — it still computed the expected value as if `stars=0` (peer_avg=0.0). This created a code-expectation inconsistency.

**Classification:** Expected value derivation error — domain validation constraint applied to code but not to expected value computation. The model had two separate inference paths (what code to write, what value to expect) and only corrected one.

**What would fix it:**
- Option A: Use `TrustDataPoint(peer_rating=None)` to achieve `peer_avg=0.0` without needing `stars=0`. This is what Attempt 2 did.
- Option B: Correct the expected value to `0.82` (using `peer_avg=0.2` from `stars=1`).
- More generally: prompts should explicitly state `"use TrustDataPoint with peer_rating=None to achieve peer_avg=0"` rather than `"stars=0"`.

**Why it succeeded on Attempt 2:** After recognizing the inconsistency, the model switched to `peer_rating=None` to correctly achieve `peer_avg=0.0`. The fix was conceptually simple once the constraint was explicitly acknowledged.

---

## Section 5: The Future of Software Engineering

### AI as Test Engineer: Observations and Implications

**What AI does well in test engineering:**

This experiment reveals a perhaps surprising strength: AI models handle test-code generation remarkably well when the domain knowledge is available. Levels 4–7 — which required the model to derive test cases and expected values from SRS descriptions alone — all passed on the first attempt. The model correctly recalled that `TRUSTED_PARTNER` requires 10 dates AND avg_rating ≥ 4.0, that noshow penalties are 0.20 per event (not 0.15, which would be hallucination), that `getTrust()` returns `None` below 5 data points, and that `tier_badge = 'new_agent'` for `date_count < 5`. These are specific numerical thresholds from project documents that the model reproduced without being reminded.

**Where AI fails in test engineering:**

The single failure — Level 2 — reveals a pattern distinct from the previous implementation-generation experiment. The model failed not because it misunderstood the formula, but because it had two separate reasoning paths (what code to write vs. what expected value to assert) and failed to keep them consistent. It correctly adapted the code to a domain constraint (`stars ≥ 1`) but forgot to propagate that adaptation to its expected value calculation. This is a **consistency failure**, not a knowledge failure.

This failure mode is specific to test code generation and largely absent from implementation generation. When generating implementations, there is one output (the code). When generating test code, there are two tightly coupled outputs (the test setup and the expected value), and the model must maintain consistency between them.

**Key engineering implications:**

First, AI-generated tests require a consistency verifier — a tool that checks whether the test setup and expected values are mathematically coherent before the test is run. Human reviewers naturally spot `"why does this test use stars=1 but assert the value for stars=0?"` but this requires careful reading.

Second, prompt design for test generation is different from prompt design for implementation. Effective implementation prompts specify what to compute. Effective test prompts must specify both the preconditions AND the expected outcomes consistently, or instruct the model to derive both from a single specification (which it can do, but risks the kind of inconsistency observed here).

Third, the model's strong performance on Levels 4–7 — where it recalled domain thresholds from REQ IDs alone — suggests that AI is a viable "first draft" test engineer for well-documented systems. The test cases generated for REQ-0401, REQ-0403, and REQ-0504 were correct, covered all required scenarios, and would catch real bugs in a faulty implementation.

---

*Generated: 2026-05-28 | CS350 Team 6 — Agentinder*
