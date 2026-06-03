# Assignment 4 — Complexity Level Design

## Function Under Test
`compute_compatibility_score(agent_a, agent_b) -> dict`

Where `agent_a` and `agent_b` are dicts representing AgentProfile-like objects.

---

## Related REQs

| REQ ID | Description | Difficulty |
|---|---|---|
| REQ-0202 | Cap = Jaccard similarity of capability_tags | Low |
| REQ-0203 | Style = 1/(1+Euclidean_distance(style_vectors)) | Medium |
| REQ-0201 | S = 0.50*Cap + 0.20*Style + 0.30*Trust (full formula) | Medium |
| REQ-0205 | Score is asymmetric (Trust of candidate b) | Low |
| REQ-0206 | New agent (date_count < 5): Trust excluded | Medium |
| REQ-0207 | New agent re-normalization: cap_w=5/7, style_w=2/7 | High |

---

## Level Design Table

| Level | Added Requirement | Source REQ | Expected Failure Risk | Failure Rationale |
|---|---|---|---|---|
| 1 | Jaccard similarity of tags only; return single float | REQ-0202 | Low | Simple set math; well-known formula |
| 2 | Add Style score (Euclidean on style dicts); return weighted (0.7*cap + 0.3*style) | REQ-0203 | Low-Medium | Distance formula straightforward, but key union handling tricky |
| 3 | Use correct weights: 0.50*cap + 0.20*style + 0.30*trust; trust as float input | REQ-0201 | Medium | Weight values are specific; easy to swap cap/style weights |
| 4 | New agent branching: if date_count < 5, use only cap and style | REQ-0206 | Medium | Branch condition off-by-one (< vs <=) |
| 5 | New agent re-normalization: cap_w=5/7, style_w=2/7 (NOT 0.5 and 0.2) | REQ-0207 | High | Division for weight normalization non-obvious; model may use 0.5 and 0.5 instead |
| 6 | Return dict with total, capability, style, trust components | REQ-0201 | Medium | Field naming may vary; trust=0.0 for new agents |
| 7 | Return common_tags and complementary_tags | REQ-0202 | Medium-High | Complementary tags = union − intersection; model may return only one side |
| 8 | Clamp total to [0.0, 1.0] | REQ-0507 | Low-Medium | Often forgotten; model may not include max(0, min(1, total)) |

---

## Generation Prompts (Natural Language Only — No Ground Truth)

### Level 1 Prompt
```
Implement a Python function compute_compatibility_score(agent_a, agent_b) where each agent is a dict with a 'tags' field (list of strings). Return a float representing the Jaccard similarity between their tag sets (intersection size divided by union size). Return 0.0 if both tag lists are empty.
```

### Level 2 Prompt
```
Implement a Python function compute_compatibility_score(agent_a, agent_b) where each agent is a dict with 'tags' (list of strings) and 'style' (dict mapping string keys to float values 0.0-1.0). Compute: cap = Jaccard similarity of tags. style = 1.0 / (1.0 + Euclidean distance between style vectors, treating missing keys as 0.0). Return 0.7 * cap + 0.3 * style as a float.
```

### Level 3 Prompt
```
Implement a Python function compute_compatibility_score(agent_a, agent_b) where each agent is a dict with 'tags' (list of strings), 'style' (dict of float values), and 'trust' (float 0.0-1.0). Compute: cap = Jaccard similarity of tags. style = 1.0 / (1.0 + Euclidean distance of style vectors). trust = agent_b['trust']. Return 0.50 * cap + 0.20 * style + 0.30 * trust as a float.
```

### Level 4 Prompt
```
Implement compute_compatibility_score(agent_a, agent_b). Each agent is a dict with 'tags' (list), 'style' (dict of floats), 'trust' (float), 'date_count' (int). cap = Jaccard of tags. style = 1/(1+euclidean of style). trust = agent_b trust score. If agent_b date_count < 5 (new agent), exclude trust: use only cap and style with weights 0.5 and 0.5. Otherwise use 0.50*cap + 0.20*style + 0.30*trust. Return float.
```

### Level 5 Prompt
```
Implement compute_compatibility_score(agent_a, agent_b). Each agent has 'tags' (list), 'style' (dict of floats), 'trust' (float), 'date_count' (int). cap = Jaccard of tags. style = 1/(1+euclidean of style). If agent_b date_count < 5: total = (0.50/(0.50+0.20))*cap + (0.20/(0.50+0.20))*style, trust_used=0.0. Else: total = 0.50*cap + 0.20*style + 0.30*agent_b['trust'], trust_used = agent_b['trust']. Return float.
```

### Level 6 Prompt
```
Implement compute_compatibility_score(agent_a, agent_b). Each agent has 'tags' (list), 'style' (dict of floats), 'trust' (float), 'date_count' (int). Compute cap (Jaccard of tags), style (1/(1+euclidean of style)), trust_used (agent_b trust, or 0.0 if new agent with date_count < 5). For new agent, re-normalize: cap_w=0.50/0.70, style_w=0.20/0.70. Return a dict with keys: 'total' (float), 'capability' (float), 'style' (float), 'trust' (float). Clamp total to [0.0, 1.0].
```

### Level 7 Prompt
```
Implement compute_compatibility_score(agent_a, agent_b). Each agent has 'tags' (list of strings), 'style' (dict of floats), 'trust' (float), 'date_count' (int). Compute: cap = Jaccard of tags; common_tags = sorted intersection; complementary_tags = sorted union minus intersection. style = 1/(1+euclidean of style). For new agent (date_count < 5): total = (5/7)*cap + (2/7)*style, trust=0.0. Else: total = 0.50*cap + 0.20*style + 0.30*agent_b['trust'], trust=agent_b['trust']. Clamp total to [0.0, 1.0]. Return dict with: 'total', 'capability', 'style', 'trust', 'common_tags', 'complementary_tags'.
```

### Level 8 Prompt
```
Implement compute_compatibility_score(agent_a, agent_b). Each agent has: 'tags' (list of strings), 'style' (dict of float values 0.0-1.0), 'trust' (float 0.0-1.0, may be None), 'date_count' (int). Compute: cap = |tags_a ∩ tags_b| / |tags_a ∪ tags_b| (0.0 if both empty). common_tags = sorted intersection; complementary_tags = sorted(union - intersection). style_diff = {k: abs(a.get(k,0)-b.get(k,0)) for all keys in either dict}. style = 1.0 / (1.0 + sqrt(sum of squared style_diffs)). For new agent (date_count < 5 OR trust is None): cap_w=0.50/0.70, style_w=0.20/0.70, trust_val=0.0. Else: cap_w=0.50, style_w=0.20, trust_val=agent_b['trust']. total = max(0.0, min(1.0, cap_w*cap + style_w*style + (0.30 if not new_agent else 0.0)*trust_val)). Return dict: 'total'(float), 'capability'(float), 'style'(float), 'trust'(float), 'common_tags'(list), 'complementary_tags'(list), 'style_diff'(dict).
```

---

## Predicted Failure Point
Most likely definitive failure: **Level 5** (new agent re-normalization with exact division weights).
Alternative failure: **Level 7** (complementary_tags definition or field naming).
