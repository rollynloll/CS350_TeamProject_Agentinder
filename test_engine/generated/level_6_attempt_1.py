# Level: 6  Attempt: 1  Result: PASS
# Prompt: Implement compute_compatibility_score(agent_a, agent_b). Each agent has
# 'tags' (list), 'style' (dict of floats), 'trust' (float), 'date_count' (int).
# Compute cap (Jaccard of tags), style (1/(1+euclidean of style)),
# trust_used (agent_b trust, or 0.0 if new agent with date_count < 5).
# For new agent, re-normalize: cap_w=0.50/0.70, style_w=0.20/0.70.
# Return a dict with keys: 'total' (float), 'capability' (float), 'style' (float), 'trust' (float).
# Clamp total to [0.0, 1.0].

import math

def compute_compatibility_score(agent_a, agent_b):
    tags_a = set(agent_a.get('tags', []))
    tags_b = set(agent_b.get('tags', []))
    union = tags_a | tags_b
    cap = len(tags_a & tags_b) / len(union) if union else 0.0

    style_a = agent_a.get('style', {})
    style_b = agent_b.get('style', {})
    all_keys = set(style_a) | set(style_b)
    dist = math.sqrt(sum((style_a.get(k, 0.0) - style_b.get(k, 0.0)) ** 2 for k in all_keys))
    style_score = 1.0 / (1.0 + dist)

    date_count = agent_b.get('date_count', 0)
    if date_count < 5:
        cap_w = 0.50 / 0.70
        style_w = 0.20 / 0.70
        trust_used = 0.0
        total = cap_w * cap + style_w * style_score
    else:
        trust_used = agent_b.get('trust', 0.0)
        total = 0.50 * cap + 0.20 * style_score + 0.30 * trust_used

    total = max(0.0, min(1.0, total))

    return {
        'total': total,
        'capability': cap,
        'style': style_score,
        'trust': trust_used,
    }
