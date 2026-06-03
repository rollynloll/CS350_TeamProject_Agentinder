# Level: 4  Attempt: 1  Result: PASS
# Prompt: Implement compute_compatibility_score(agent_a, agent_b). Each agent is a dict
# with 'tags' (list), 'style' (dict of floats), 'trust' (float), 'date_count' (int).
# cap = Jaccard of tags. style = 1/(1+euclidean of style).
# If agent_b date_count < 5 (new agent), exclude trust: use only cap and style
# but keep the same relative proportions between cap and style weights.
# Normally: 0.50*cap + 0.20*style + 0.30*trust
# Return float.

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
    style = 1.0 / (1.0 + dist)

    date_count = agent_b.get('date_count', 0)
    if date_count < 5:
        # Exclude trust; keep relative proportions of cap (0.50) and style (0.20)
        # Normalized: cap_w = 0.50/0.70, style_w = 0.20/0.70
        cap_w = 0.50 / 0.70
        style_w = 0.20 / 0.70
        return cap_w * cap + style_w * style
    else:
        trust = agent_b.get('trust', 0.0)
        return 0.50 * cap + 0.20 * style + 0.30 * trust
