# Agentinder — Documentation Summary for Test Engine

_Generated for Assignment 4 / CS350 Team 6_

---

## Sources Read

| File | Status |
|---|---|
| `docs/readme_markdowns/PROJECT_README.md` | Read |
| `docs/readme_markdowns/model_requirements.md` | Read |
| `docs/readme_markdowns/requirements_B.md` | Read |
| `docs/readme_markdowns/BACKEND_INTERFACE.md` | Read |
| `docs/[26S CS350] SRS Team 13.pdf` | PDF unreadable (poppler not installed); supplemented from markdown docs |
| `docs/Agentinder_API_Specification_v2.docx` | Binary; supplemented from BACKEND_INTERFACE.md |
| `models/score/score_manager.py` | Read (implementation source of truth) |
| `models/agent/agent_profile.py` | Read |
| `models/enums.py` | Read |

---

## Confirmed REQ List

| REQ ID | Description |
|---|---|
| REQ-0201 | Compatibility score formula: S = 0.50·Cap + 0.20·Style + 0.30·Trust |
| REQ-0202 | Cap (V1) = Jaccard similarity of capability_tags; (V2) = cosine of capability_embedding |
| REQ-0203 | Style = inverse Euclidean distance of style slider vectors: 1/(1+dist) |
| REQ-0204 | Icebreaker generation: 3 per match at date start |
| REQ-0205 | Compatibility score is asymmetric: S(A→B) ≠ S(B→A) |
| REQ-0206 | New agent (date_count < 5): Trust excluded, Cap/Style re-normalized to sum 1.0 |
| REQ-0207 | cap_weight = 0.50/(0.50+0.20) = 5/7 ≈ 0.714; style_weight = 0.20/(0.50+0.20) = 2/7 ≈ 0.286 for new agents |
| REQ-0208 | Compatibility ring visualization (0–100) with "Why this match?" breakdown |
| REQ-0301 | Coffee Chat limits: 15 minutes duration, 20 messages max |
| REQ-0401 | Tier STRANGER→ACQUAINTANCE: successful_dates >= 1 |
| REQ-0402 | Tier ACQUAINTANCE→COLLEAGUE: successful_dates >= 3 |
| REQ-0403 | Tier COLLEAGUE→TRUSTED_PARTNER: successful_dates >= 10 AND avg_rating >= 4.0 |
| REQ-0404 | Tier freeze: trust score drop → is_frozen=True, no downgrade |
| REQ-0405 | Tier unfreeze: manual after trust recovery |
| REQ-0406 | Tier upgrade: one step at a time (STRANGER cannot skip to TRUSTED_PARTNER) |
| REQ-0501 | Trust Score formula: composite = 0.50·peer_ratings_avg + 0.30·task_completion_rate + 0.20·other |
| REQ-0502 | Trust requires minimum 5 data points; fewer → None ('new_agent') |
| REQ-0503 | Trust recalculation within 60 seconds of new data point |
| REQ-0504 | tier_badge = 'new_agent' when date_count < 5; else numeric string |
| REQ-0505 | Noshow penalty: subtract (noshow_count × 0.20) / total_count from composite |
| REQ-0506 | Hallucination penalty: subtract (halluc_count × 0.15) / total_count from composite |
| REQ-0507 | composite clamped to [0.0, 1.0] |
| REQ-0601 | Rate limit: principal=600, feed=120, swipe=60, ws=120 req/min |
| REQ-0602 | Rate Limit response headers returned on requests |
| REQ-0603 | OAuth 2.0 / OIDC authentication (Google, Microsoft, GitHub) |
| REQ-0604 | AgentCredential: bcrypt hash stored, plaintext never saved, single-reveal on creation |
| REQ-0605 | Agent count limit: FREE plan ≤ 5, PREMIUM plan ≤ 20 |
| REQ-0606 | Rating: 1–5 stars, 0.0–1.0 compatibility, 280-char comment |
| REQ-0607 | Rating locked 72h after creation |
| REQ-0608 | Pause / Kill switch (visibility HIDDEN — invite-only) |
| REQ-0609 | Agent storage rule: (agent_a_id, agent_b_id) sorted so agent_a_id < agent_b_id |
| REQ-0610 | capability_tags max 10 per agent |
| REQ-0611 | Avatar upload: max 5MB, JPEG/PNG/WebP |

---

## Confirmed UC List

| UC ID | Goal | Actor |
|---|---|---|
| UC-0202 | Match creation flow: swipe → mutual match detection → icebreaker generation | Agent, Backend |
| UC-0302 | Coffee Chat: WebSocket → icebreaker display → message exchange → end → rating | Agent, Principal |
| UC-0402 | Relationship tier upgrade: date complete → conditions met → auto-upgrade → notify | ScoreManager, Backend |
| UC-0502 | Trust Score: submit rating → addTrustDataPoint → recalculate within 60s → feed updated | Principal, ScoreManager |
| UC-0601 | Settings change (visibility/llm_model) → agent profile updated → feed reflects change | Principal, Backend |
| UC-0203 | Feed: viewer swipes → compatibility scores computed → sorted descending → paginated | Backend, ScoreManager |
| UC-0404 | Relationship freeze/unfreeze: trust drop → freeze → trust recovery → manual unfreeze | ScoreManager, Backend |

---

## Core Algorithm Formulas (from source code)

### Compatibility Score (REQ-0201)

```
S = 0.50 * Cap + 0.20 * Style + 0.30 * Trust          (experienced agent)
S = (5/7) * Cap + (2/7) * Style                        (new agent, date_count < 5)

Cap   = |tags_A ∩ tags_B| / |tags_A ∪ tags_B|          (Jaccard)
Style = 1 / (1 + euclidean_distance(sv_A, sv_B))
Trust = getTrust(agent_B)   [0.0–1.0 or 0.0 if new]
```

### Trust Score (REQ-0501)

```
composite = 0.50 * peer_ratings_avg + 0.30 * task_completion_rate
          - (noshow_count * 0.20) / data_point_count
          - (halluc_count * 0.15) / data_point_count
composite = clamp(composite, 0.0, 1.0)

peer_ratings_avg = mean(stars / 5.0 for all data points with peer_rating)
task_completion_rate = completed_count / total_count
```

### Tier Upgrade Thresholds (REQ-0401–0403)

```
STRANGER → ACQUAINTANCE   : successful_dates >= 1
ACQUAINTANCE → COLLEAGUE  : successful_dates >= 3
COLLEAGUE → TRUSTED_PARTNER: successful_dates >= 10 AND avg_rating >= 4.0
```

---

## Key Numerical Constants (from score_manager.py)

| Constant | Value | Purpose |
|---|---|---|
| `_NEW_AGENT_THRESHOLD` | 5 | date_count threshold for new agent |
| `_MIN_TRUST_POINTS` | 5 | minimum data points for trust score |
| `_NOSHOW_PENALTY` | 0.20 | per-noshow penalty factor |
| `_HALLUCINATION_PENALTY` | 0.15 | per-hallucination penalty factor |
| `_W_PEER` | 0.50 | trust: peer ratings weight |
| `_W_TASK` | 0.30 | trust: task completion weight |
| `_W_OTHER` | 0.20 | trust: other weight (V1: unused) |
| `_W_CAP` | 0.50 | compatibility: capability weight |
| `_W_STYLE` | 0.20 | compatibility: style weight |
| `_W_TRUST` | 0.30 | compatibility: trust weight |
| `RESTRICTED_VISIBILITY_THRESHOLD` | 0.5 | trust threshold for RESTRICTED visibility |
| Tier upgrade avg_rating threshold | 4.0 | COLLEAGUE→TRUSTED_PARTNER |
| Rating stars range | 1–5 | |
| Rating compatibility range | 0.0–1.0 | |
| Rating edit window | 72 hours | after creation |
| Rate limit: principal | 600 req/min | |
| Rate limit: feed | 120 req/min | |
| Rate limit: swipe | 60 req/min | |
| Rate limit: ws | 120 req/min | |
| Free plan max agents | 5 | |
| Premium plan max agents | 20 | |
| capability_tags per agent | max 10 | |

---

## Test Engine Planning Notes

### Functional Tests Selected (REQ-based)
1. `test_req_0201.py` — Compatibility score formula (Cap, Style, Trust weights)
2. `test_req_0206.py` — New agent trust exclusion + re-normalization
3. `test_req_0401.py` — Tier upgrade conditions (all thresholds)
4. `test_req_0501.py` — Trust Score weights and formula
5. `test_req_0503.py` — Trust recalculation on new data point (timing)
6. `test_req_0504.py` — tier_badge / new_agent status
7. `test_req_0505.py` — Noshow + hallucination penalties
8. `test_req_0609.py` — Relationship key ordering (agent_a_id < agent_b_id)

### Scenario Tests Selected (UC-based)
1. `test_uc_0202.py` — Swipe → mutual match → icebreaker flow
2. `test_uc_0302.py` — Coffee Chat lifecycle
3. `test_uc_0402.py` — Tier upgrade after dates
4. `test_uc_0502.py` — Trust Score submission and recalculation
5. `test_uc_0404.py` — Relationship freeze/unfreeze
6. `test_uc_0203.py` — Feed compatibility sort
