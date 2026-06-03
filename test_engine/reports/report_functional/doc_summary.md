# Agentinder — Documentation Summary (Functional Test Generation Experiment)

_Generated for Assignment 4 Functional Experiment / CS350 Team 6_

---

## Sources Read

| File | Status |
|---|---|
| `docs/readme_markdowns/PROJECT_README.md` | Read |
| `docs/readme_markdowns/model_requirements.md` | Read |
| `docs/readme_markdowns/requirements_B.md` | Read |
| `docs/readme_markdowns/BACKEND_INTERFACE.md` | Read |
| `models/score/score_manager.py` | Read (implementation source of truth) |
| `models/agent/agent_profile.py` | Read |
| `models/rating/rating.py` | Read |
| `models/enums.py` | Read |
| `docs/[26S CS350] SRS Team 13.pdf` | PDF unreadable (poppler not installed); supplemented from markdown docs |

---

## REQ List Selected for Test Generation Experiment

| REQ ID | Description | Key Numbers |
|---|---|---|
| REQ-0201 | S = 0.50·Cap + 0.20·Style + 0.30·Trust | weights: 0.50, 0.20, 0.30 |
| REQ-0202 | Cap = Jaccard(tags_A, tags_B) = \|A∩B\| / \|A∪B\| | — |
| REQ-0203 | Style = 1/(1+Euclidean(sv_A, sv_B)) | — |
| REQ-0206 | New agent (date_count<5): Trust excluded, cap_w=5/7, style_w=2/7 | threshold: 5 |
| REQ-0401 | STRANGER→ACQUAINTANCE: successful_dates ≥ 1 | 1 date |
| REQ-0402 | ACQUAINTANCE→COLLEAGUE: successful_dates ≥ 3 | 3 dates |
| REQ-0403 | COLLEAGUE→TRUSTED_PARTNER: successful_dates ≥ 10 AND avg_rating ≥ 4.0 | 10 dates, 4.0 stars |
| REQ-0404 | Freeze: trust drop → is_frozen=True, no tier downgrade | — |
| REQ-0501 | Trust = 0.50·peer_avg + 0.30·task_rate + 0.20·other (V1: other=0) | weights |
| REQ-0502 | Trust requires ≥ 5 data points; fewer → None ('new_agent') | threshold: 5 |
| REQ-0503 | Trust recalculated within 60s of new data point | 60s SLA |
| REQ-0504 | tier_badge='new_agent' when date_count<5; else numeric string | threshold: 5 |
| REQ-0505 | Noshow penalty = noshow_count·0.20 / total_count | 0.20 per noshow |
| REQ-0506 | Hallucination penalty = halluc_count·0.15 / total_count | 0.15 per halluc |
| REQ-0507 | composite clamped to [0.0, 1.0] | — |
| REQ-0606 | Rating: stars 1–5, compatibility 0.0–1.0, comment max 280 chars | — |
| REQ-0607 | Rating locked 72h after creation | 72h = 259200s |

---

## Key Numerical Constants (from score_manager.py)

| Constant | Value |
|---|---|
| `_NEW_AGENT_THRESHOLD` | 5 (date_count < 5 = new agent) |
| `_MIN_TRUST_POINTS` | 5 (minimum data points for trust) |
| `_NOSHOW_PENALTY` | 0.20 |
| `_HALLUCINATION_PENALTY` | 0.15 |
| `_W_PEER` | 0.50 |
| `_W_TASK` | 0.30 |
| `_W_CAP` | 0.50 |
| `_W_STYLE` | 0.20 |
| `_W_TRUST` | 0.30 |
| New agent cap_weight | 0.50/(0.50+0.20) = 5/7 ≈ 0.71429 |
| New agent style_weight | 0.20/(0.50+0.20) = 2/7 ≈ 0.28571 |
| RESTRICTED_VISIBILITY_THRESHOLD | 0.5 |

---

## Helpers Available for Test Code (shared/mock_data.py)

```python
from shared.mock_data import (
    make_profile,           # creates AgentProfile with given tags, style_vector, date_count
    make_score_manager,     # creates fresh ScoreManager
    add_n_trust_points,     # adds N trust data points with given stars
    make_trust_data_point,  # creates TrustDataPoint with is_noshow/hallucination flags
)
```

These helpers are available to generated test code via `sys.path` injection.

---

## Notes for Test Generation Experiment

- All generated test code imports from `models/` package (actual implementation)
- Trust score setup: use `add_n_trust_points(sm, agent_id, n=5, stars=X)`
- Tier setup: use `sm.recordSuccessfulDate(a, b, rating=R)` + `sm.checkUpgrade(a, b)`
- Expected values are derived from the formulas above, not from reverse-engineering the implementation
