# Functional Test Generation — Complexity Level Design

## Experiment Context

Claude API is asked to generate **test code** for REQ requirements.
Each level increases the amount of inference the model must do:
- Levels 1–3: expected values given in prompt → model transcribes
- Levels 4–5: expected values must be derived from SRS description in prompt
- Levels 6–7: case design AND expected values both determined by model

---

## Level Table

| Level | Info Allowed in Prompt | Target REQ(s) | Case Types | Expected Value Source | Predicted Failure Risk | Failure Rationale |
|---|---|---|---|---|---|---|
| 1 | REQ text + setup code + expected value | REQ-0201 | Happy only | Given in prompt | Very Low | Direct transcription of given value |
| 2 | REQ text + setup code + expected values | REQ-0201 | Happy + boundary | Given in prompt | Low | Two cases; same transcription task |
| 3 | REQ text + setup code + expected values | REQ-0206 | Happy + boundary + exception | Given in prompt | Low | Three cases with new-agent branch; values given |
| 4 | REQ text only (no setup, no expected value) | REQ-0401 | Happy + boundary, types named | Must derive from SRS | Medium | Model must translate tier conditions into test assertions |
| 5 | REQ text only | REQ-0501 + REQ-0502 | All types, types named | Must derive from SRS | Medium-High | Formula derivation for two REQs; composite calculation |
| 6 | REQ ID + one-line description only | REQ-0505 + REQ-0506 | Model decides | Must derive from SRS | High | Penalty formula is non-obvious; model must identify edge cases |
| 7 | REQ IDs only (no description) | REQ-0401 + REQ-0403 + REQ-0504 | Model decides everything | Must derive from SRS | Very High | Three linked REQs; threshold values must be inferred from REQ number alone |

---

## Prompts (System + User per Level)

### System Prompt (all levels)
```
You are a software test engineer. Write Python test code for the given requirement.
The code must:
- Import from sys.path which includes the project root
- Use: from models.score.score_manager import ScoreManager, TrustDataPoint
- Use: from models.agent.agent_profile import AgentProfile
- Use: from models.enums import TierEnum, IssueEnum
- Use: from uuid import uuid4
- Print "PASS <test_name>" or "FAIL <test_name>: <reason>" for each test
- Call all test functions at the end of the file
Output only raw Python code, no markdown fences, no explanation.
```

### Level 1 Prompt
```
REQ-0201: Compatibility score = 0.50*Cap + 0.20*Style + 0.30*Trust.
Cap = Jaccard similarity of capability_tags. Style = 1/(1+euclidean_distance(style_vectors)).
Trust = candidate agent's trust score (0.0-1.0).

Write one happy-path test:
- agent_a: tags=["coding","research"], style={"formality":0.8}, date_count=10
- agent_b: tags=["coding","research"], style={"formality":0.8}, date_count=10, trust=0.6
Setup: sm = ScoreManager(); add 5 data points to agent_b (all stars=3, task_completed=True)
  peer_avg = 3/5 = 0.6, task_rate = 1.0, composite = 0.50*0.6 + 0.30*1.0 = 0.60
Expected total = 0.50*1.0 + 0.20*1.0 + 0.30*0.60 = 0.88
```

### Level 2 Prompt
```
REQ-0201: S = 0.50*Cap + 0.20*Style + 0.30*Trust
Cap = |tags_a ∩ tags_b| / |tags_a ∪ tags_b| (Jaccard). Style = 1/(1+euclidean(sv_a,sv_b)).

Test case A (happy path — identical tags, identical style, trust=0):
  agent_a: tags=["a","b"], style={}, date_count=10
  agent_b: tags=["a","b"], style={}, date_count=10, 5 data points stars=0 (peer_avg=0), task_rate=1.0
  composite_b = 0.50*0.0 + 0.30*1.0 = 0.30
  total = 0.50*1.0 + 0.20*1.0 + 0.30*0.30 = 0.79

Test case B (boundary — no common tags, style dist=1):
  agent_a: tags=["x"], style={"f":1.0}, date_count=10
  agent_b: tags=["y"], style={"f":0.0}, date_count=10, 5 data points stars=5, task_rate=1.0
  Cap=0.0, style=1/(1+1)=0.5, composite_b=0.50*1.0+0.30*1.0=0.80
  total = 0.50*0.0 + 0.20*0.5 + 0.30*0.80 = 0.34
```

### Level 3 Prompt
```
REQ-0206: New agent (date_count<5): Trust excluded from compatibility score.
Re-normalized weights: cap_w = 0.50/0.70 = 5/7, style_w = 0.20/0.70 = 2/7.
REQ-0201: experienced agent (date_count>=5): S = 0.50*Cap + 0.20*Style + 0.30*Trust.

Test A (happy — new agent, Cap=1, Style=1):
  agent_b.date_count=0; trust excluded
  total = (5/7)*1.0 + (2/7)*1.0 = 1.0

Test B (boundary — date_count=4 still new, date_count=5 experienced):
  B1: date_count=4, cap=1, style=1 → total=(5/7)+(2/7)=1.0 (new agent)
  B2: date_count=5, cap=1, style=1, trust=0 → total=0.50+0.20+0.0=0.70 (experienced, no trust data)

Test C (exception — new agent with trust data present but ignored):
  agent_b.date_count=2, 5 data points stars=5 (composite=0.80), but ignored
  cap=1, style=1 → total = (5/7)*1.0 + (2/7)*1.0 = 1.0
```

### Level 4 Prompt
```
REQ-0401: When two agents complete a successful date together, their relationship tier
may upgrade. Thresholds: STRANGER→ACQUAINTANCE when successful_dates>=1;
ACQUAINTANCE→COLLEAGUE when successful_dates>=3;
COLLEAGUE→TRUSTED_PARTNER when successful_dates>=10 AND avg_rating>=4.0.
Upgrade is one step at a time. Freeze blocks upgrade.

Use: ScoreManager, sm.recordSuccessfulDate(a,b,rating), sm.checkUpgrade(a,b),
     sm.getRelationship(a,b), sm.freeze(a,b), sm.unfreeze(a,b), TierEnum.

Write tests covering: happy path, boundary (exact thresholds), exception (freeze).
Derive expected values from the threshold conditions above.
```

### Level 5 Prompt
```
REQ-0501: Trust Score composite = 0.50*peer_ratings_avg + 0.30*task_completion_rate.
peer_ratings_avg = mean(stars/5.0 for data points with peer_rating).
task_completion_rate = completed_count / total_count.
REQ-0502: Fewer than 5 data points → getTrust() returns None.

Use: ScoreManager, TrustDataPoint, sm.addTrustDataPoint(agent_id, dp),
     sm.getTrust(agent_id), sm.getTrustBreakdown(agent_id).
TrustDataPoint fields: agent_id, date_id (uuid4()), peer_rating (Rating|None),
                       task_completed (bool), is_noshow (bool, default False).
For peer_rating, use Rating(date_id=..., rater_principal_id=uuid4(),
                             rated_agent_id=agent_id, stars=N, compatibility=N/5.0).

Write tests covering: happy path (correct composite value), boundary (4 vs 5 data points),
exception (None return when insufficient data). Derive expected values from the formula.
```

### Level 6 Prompt
```
REQ-0505: Trust composite is penalized for noshow events:
subtract (noshow_count * 0.20) / data_point_count from composite.
REQ-0506: Penalized for confirmed hallucinations:
subtract (halluc_count * 0.15) / data_point_count.
REQ-0507: Composite is clamped to [0.0, 1.0].

Use TrustDataPoint(is_noshow=True) for noshow, TrustDataPoint(hallucination_confirmed=True) for hallucination.
Write tests you consider appropriate for these requirements.
```

### Level 7 Prompt
```
REQ-0401, REQ-0403, REQ-0504 are requirements in the Agentinder system.
REQ-0401 concerns relationship tiers between agents.
REQ-0403 concerns the highest relationship tier.
REQ-0504 concerns agent badge display.

Write tests for all three requirements. Determine the test cases and expected values yourself.
```

---

## Pre-Experiment Failure Predictions

| Level | Predicted Failure | Probability |
|---|---|---|
| 1 | Incorrect import or setup → SyntaxError/ImportError | Low |
| 2 | Wrong expected value for boundary case (style formula) | Low |
| 3 | Off-by-one on date_count threshold (uses <= instead of <) | Low-Medium |
| 4 | Wrong tier name (e.g. PARTNER instead of TRUSTED_PARTNER), missing freeze test | Medium |
| 5 | Wrong formula: may use 0.50*peer + 0.30*task but forget that peer_avg = stars/5, not stars | Medium-High |
| 6 | Wrong penalty magnitude (uses 0.15 for noshow, 0.20 for halluc — swapped) | High |
| 7 | Hallucinated thresholds (e.g. TRUSTED_PARTNER at 5 dates instead of 10) | Very High |
