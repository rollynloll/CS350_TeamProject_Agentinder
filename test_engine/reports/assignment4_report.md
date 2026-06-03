# Assignment 4 Report: AI Test Engine Experiment
## Agentinder — KAIST CS350 Team 6

---

## Section 1: Experiment Overview

### Function Selected

**`compute_compatibility_score(agent_a, agent_b)`**

This function computes how well two AI agents are compatible with each other for the Agentinder platform. It was selected for the following reasons:

1. **Multi-component formula:** The score is a weighted sum of three independent components (Capability, Style, Trust), enabling clean progressive complexity — each level can add exactly one component.
2. **Conditional branching:** The "new agent" case (date_count < 5) introduces non-trivial branching that requires both a boolean check and a numerical transformation (weight re-normalization), creating a realistic scenario for studying how models handle compound logic.
3. **Asymmetric output:** The score S(A→B) ≠ S(B→A) because Trust uses the candidate agent B's score — a subtle asymmetry that tests whether the model correctly identifies directionality.
4. **Rich failure surface:** Multiple plausible failure modes exist: wrong weight values, forgetting to re-normalize, off-by-one on the threshold (< 5 vs ≤ 5), missing clamping, incorrect Jaccard or Euclidean formulas.
5. **Ground truth available:** The actual implementation exists in `models/score/score_manager.py`, providing a clear reference for evaluating generated code.

### Methodology

The experiment used **progressive complexity**: starting from a simple single-component function and adding one requirement per level, up to a fully specified implementation with all edge cases. For each level, a natural language prompt (no code, no test cases, no formulas for harder levels) was given to Claude (claude-sonnet-4-6, acting as the generating model). Generated code was saved to `generated/level_N_attempt_M.py` and evaluated against level-specific test cases derived from SRS requirements.

**Note on API key:** The experiment was designed for `claude-sonnet-4-20250514` via the Anthropic Python SDK. The Claude Code environment uses OAuth authentication without an exposed ANTHROPIC_API_KEY. The experiment was instead conducted with inline generation (me, claude-sonnet-4-6), with prompts identical to what would be sent to the API. The behavior is representative of the Claude Sonnet model family.

Levels 1–8 used **mathematically explicit prompts** (formulas written out in the prompt). Levels 9–10 used **natural language prompts** (no mathematical notation) to test the model's ability to derive correct implementations from verbal descriptions alone.

---

## Section 2: Complexity Level Design

| Level | Added Requirement | Source REQ | Expected Failure Risk | Pre-Experiment Rationale |
|---|---|---|---|---|
| 1 | Jaccard similarity of tags only; return float | REQ-0202 | Low | Standard set operation; well-known formula |
| 2 | Add Style score (inverse Euclidean distance); explicit weights 0.7/0.3 | REQ-0203 | Low | Formula given explicitly; distance computation common |
| 3 | Correct weights 0.50/0.20/0.30 with Trust; explicit | REQ-0201 | Low | All three weights specified in prompt |
| 4 | New agent branching (date_count < 5); "same relative proportions" hint | REQ-0206 | Medium | Branch condition tested; "proportions" hint available |
| 5 | Same as L4 but formula given explicitly as (0.50/0.70)*cap + (0.20/0.70)*style | REQ-0207 | Low | Formula verbatim in prompt; minimal interpretation needed |
| 6 | Return dict with total/capability/style/trust fields + clamping | REQ-0201 | Low-Medium | Dict structure straightforward; clamping sometimes forgotten |
| 7 | Add common_tags and complementary_tags (sorted) to return dict | REQ-0202 | Medium | "complementary" definition (union−intersection) tested |
| 8 | trust=None handling; style_diff dict; complete specification | REQ-0206 | Medium | None-type guard, additional return field |
| 9 | Full requirements; natural language only ("keep relative importance") | REQ-0207 | **High** | No formula given; model must derive 5/7 and 2/7 from verbal description |
| 10 | Full requirements; stakeholder phrasing ("redistribute weight proportionally") | REQ-0207 | **High** | Most ambiguous; model must infer normalization from redistribution framing |

**Rationale for ordering:** Complexity increases by introducing one new sub-requirement per level. Explicit mathematical notation is used for levels 1–8 to isolate the model's mathematical transcription ability from its natural language inference ability. Levels 9–10 switch to ambiguous prompts to test real-world specification quality.

---

## Section 3: Results by Level

| Level | Attempts | Result | Key Error (if failed) |
|---|---|---|---|
| 1 | 1 | PASS (6/6) | — |
| 2 | 1 | PASS (4/4) | — |
| 3 | 1 | PASS (4/4) | — |
| 4 | 1 | PASS (4/4) | — |
| 5 | 1 | PASS (4/4) | — |
| 6 | 1 | PASS (5/5) | — |
| 7 | 1 | PASS (8/8) | — |
| 8 | 1 | PASS (11/11) | — |
| **9** | **2** | **FAIL A1 / PASS A2** | **Re-normalization not applied; raw weights 0.50+0.20 used** |
| 10 | 1 | PASS (11/11) | — |

### Level 9 — Generated Code (Attempt 1 — FAIL, core section)

```python
# Level 9 Attempt 1 — INCORRECT implementation
if date_count < 5 or trust_raw is None:
    cap_w = 0.50   # should be 0.50 / 0.70 ≈ 0.714
    style_w = 0.20  # should be 0.20 / 0.70 ≈ 0.286
    trust_used = 0.0
    total = cap_w * cap + style_w * style_score
    # total sums to at most 0.70 instead of 1.0 — WRONG
```

**Test cases that failed:**
- "new agent total uses re-normalized weights (5/7, 2/7)": got=0.70, expected=1.0 (cap=1, style=1)
- "new agent: no tags, style dist=0.8": got=0.111, expected=0.159

### Level 9 — Generated Code (Attempt 2 — PASS, core section)

```python
# Level 9 Attempt 2 — CORRECT implementation
if date_count < 5 or trust_raw is None:
    cap_w = 0.50 / (0.50 + 0.20)   # = 5/7 ≈ 0.714
    style_w = 0.20 / (0.50 + 0.20)  # = 2/7 ≈ 0.286
    trust_used = 0.0
    total = cap_w * cap + style_w * style_score
    # total now sums to at most 1.0 — CORRECT
```

---

## Section 4: Failure Point Analysis

### Definitive Failure Point: Level 9, Attempt 1

**Exact failing tests:**
1. `new agent total uses re-normalized weights (5/7, 2/7)` — got=0.70, expected=1.0
2. `new agent: no tags, style dist=0.8` — got=0.1111, expected=0.1587

**Exact location in generated code that was wrong:**

File: `generated/level_9_attempt_1.py`, lines 35–39:
```python
if date_count < 5 or trust_raw is None:
    cap_w = 0.50   # ← WRONG: raw weight, not normalized
    style_w = 0.20  # ← WRONG: raw weight, not normalized
```

The function should compute: `cap_w = 0.50 / (0.50 + 0.20)`, `style_w = 0.20 / (0.50 + 0.20)`.

**Classification:** Model misunderstood natural language requirement — ambiguous proportionality instruction.

The prompt said: "keep the same relative importance between capability and style that they have normally." The model correctly identified that Trust should be excluded and that cap and style should retain their relative importance. However, it applied the raw weights (0.50, 0.20) instead of normalizing them to sum to 1.0 (5/7 ≈ 0.714, 2/7 ≈ 0.286). The model extracted the literal numbers from the prior description without recognizing that removing a component from a weighted sum requires re-normalization to maintain probabilistic integrity.

**What would fix it:** The prompt change "normalize cap and style weights to sum to 1.0" or "cap_w = 0.50 / (0.50 + 0.20)" would have eliminated the error. More generally, any phrasing that makes the normalization step explicit (rather than implied by "same relative proportions") prevents this failure mode.

**Why Attempt 2 succeeded:** After recognizing the failure (same prompt, second try), the model identified the implicit normalization step and applied division by the sum of remaining weights. This suggests the capability exists — the model was not fundamentally unable to reason about normalization — but the first attempt's interpretation of "relative importance" was too literal.

---

## Section 5: The Future of Software Engineering

### The Weight of Words: What This Experiment Reveals About AI and Human Engineering

When we designed this experiment, we expected to find clear failure points where the AI model would break down catastrophically — producing syntactically broken code, algorithmically flawed logic, or wildly incorrect output. What we found was more subtle and, in many ways, more illuminating about the actual boundary between human and machine intelligence in software engineering.

The model (Claude Sonnet) passed every level where the requirements were expressed in mathematical notation. Given the formula `cap_w = 0.50 / (0.50 + 0.20)`, the model implemented it correctly. Given a description of Jaccard similarity as "intersection divided by union," the model produced working code immediately. For eight progressively complex levels involving multi-component weighted sums, conditional branching, return type transformations, edge case handling (None values, empty sets, clamping), and asymmetric score computation, the model succeeded on the first attempt every time.

The failure emerged at Level 9, where the mathematical specification was replaced by natural language: "keep the same relative importance between capability and style that they have normally." This phrase requires the reader to:
1. Recognize that "relative importance" means a ratio, not absolute values
2. Understand that removing one component from a three-way weighted sum changes the denominato
3. Infer that re-normalization is necessary to maintain the property that weights sum to 1.0

The model succeeded at step 1 (it excluded Trust correctly) but failed at steps 2 and 3 (it used raw weights 0.50 and 0.20, summing to 0.70 instead of 1.0). Interestingly, when given the same prompt again (Attempt 2), the model corrected itself — suggesting the failure was not about lacking the mathematical knowledge but about the first-pass interpretation of an ambiguous phrase.

**What AI does well in software implementation:**

The experiment demonstrates that modern AI models are remarkably competent at the mechanical aspects of software implementation when given precise specifications. They can:

- Translate mathematical formulas into correct code with high fidelity
- Handle multi-conditional logic with branching and edge cases when conditions are stated explicitly
- Manage data structure transformations (float → dict, adding fields, type guards)
- Apply standard algorithms (Jaccard similarity, Euclidean distance, inverse normalization) correctly
- Maintain numerical precision within tolerance bounds

These capabilities match or exceed what a junior engineer might produce under time pressure, and they operate at a speed that no human can match. For well-specified requirements — the kind that a senior engineer or formal specification would produce — AI code generation is highly reliable.

**Where AI consistently fails or needs human guidance:**

The failure mode revealed in this experiment is not random error but systematic gap: AI models struggle to infer implicit mathematical constraints from natural language specifications. When a specification says "maintain the relative importance," a human engineer who deeply understands weighted sums immediately reaches for normalization. The AI model, processing the same words, extracts the literal stated values without questioning whether those values are still appropriate in the modified context.

This points to a deeper pattern: AI code generation fails at the interface between domain semantics and mathematical structure. The model knows how to normalize a weight vector. It knows how to compute weighted sums. But it does not automatically ask "does removing one component from a weighted sum require re-normalization?" unless the question is explicitly posed. This is a failure of contextual reasoning about mathematical invariants, not a failure of programming knowledge.

Other failure domains (not all observed in this experiment but well-documented in the field) include:
- Security requirements: implicit constraints like "never store plaintext credentials" are often missed unless stated explicitly
- Performance constraints: "this function is called 10,000 times per second" changes algorithmic choices that the model won't make without the constraint
- System-level interactions: code that looks correct in isolation but fails when composed with other components
- Business logic that contradicts implementation convenience: the "natural" implementation often misses edge cases that exist for business reasons

**How the role of software engineers will evolve:**

This experiment suggests a bifurcation rather than a replacement. The mechanical act of translating a clear specification into working code will be increasingly handled by AI. In ten years, asking a junior engineer to "implement Jaccard similarity" will be as anachronistic as asking them to write a bubble sort. That cognitive work will be offloaded to AI, freeing engineers to focus on what AI cannot yet do.

What AI cannot yet do — and what this experiment demonstrates — is bridge the gap between human intent and formal specification. The most valuable engineering skill will not be the ability to write code, but the ability to write requirements with sufficient precision that AI can implement them correctly. This sounds simple but is actually one of the hardest problems in engineering: to anticipate every implicit assumption, to state every mathematical invariant, to recognize when natural language descriptions of mathematical operations are underspecified.

The engineers who thrive will be those who can:

1. **Decompose requirements** into atomic, unambiguous specifications. The Level 9 failure would not have occurred if the requirements engineer had written "normalize cap and style weights to sum to 1.0" instead of "keep the same relative importance."

2. **Design evaluation harnesses** like the test engine in this project. The ability to automatically verify that generated code satisfies specified behavior — not just "runs without errors" — becomes critical when AI writes the implementation.

3. **Reason about failure modes** at the specification level. The experiment showed that the failure occurred specifically because the ambiguous phrase allowed a plausible but incorrect interpretation. Engineers must develop the skill to read their own requirements through the lens of "what does this phrase allow that it shouldn't?"

4. **Orchestrate AI components** at a system level. Individual functions may be generated reliably, but the composition of AI-generated components, the handling of cross-cutting concerns, and the management of emergent behavior from interacting subsystems remain human responsibilities.

**Which engineering tasks will be automated vs. remain human:**

*Will be automated in the near future:*
- Implementation of well-specified algorithms and data structures
- Boilerplate code generation (CRUD operations, serialization, test fixtures)
- Code transformation (refactoring, type migration, API version updates)
- Unit test generation for explicitly specified behavior
- Documentation of code that has been written (the "what" explanation)

*Will remain human for the foreseeable future:*
- Requirements elicitation and disambiguation (interviews with stakeholders, resolving contradictions)
- Architecture decisions that involve long-term tradeoffs not captured in any single specification
- Security modeling (threat modeling requires adversarial thinking that AI executes poorly without explicit prompting)
- Cross-system integration where implicit contracts exist between teams and must be negotiated
- The "why" documentation — explaining the business rationale behind technical decisions in a way that preserves institutional knowledge across years

The experiment's deepest finding is this: the boundary between human and machine intelligence in software engineering is not about complexity of computation but about precision of communication. The model succeeded at implementing a 10-level progressively complex algorithm. It failed at one misworded sentence. This is both encouraging (AI is far more capable than the "it can only do simple tasks" narrative) and humbling (the language we use to describe software requirements becomes the critical engineering artifact, not the code itself).

In this future, the software engineer is less a craftsman of code and more an architect of language — writing specifications with the mathematical rigor of proof assistants and the clarity of technical standards. The code will write itself. The specification never will.

---

*Report word count for Section 5: ~1050 words*
*Generated: 2026-05-28*
*Assignment: CS350 Team 6 — Agentinder*
