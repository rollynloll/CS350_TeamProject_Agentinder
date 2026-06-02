# Level: 7  Attempt: 1  Result: PASS
# Prompt: Implement compute_compatibility_score(agent_a, agent_b). Each agent has
# 'tags' (list of strings), 'style' (dict of floats), 'trust' (float), 'date_count' (int).
# Compute: cap = Jaccard of tags; common_tags = sorted intersection;
# complementary_tags = sorted union minus intersection.
# style = 1/(1+euclidean of style).
# For new agent (date_count < 5): total = (5/7)*cap + (2/7)*style, trust=0.0.
# Else: total = 0.50*cap + 0.20*style + 0.30*agent_b['trust'], trust=agent_b['trust'].
# Clamp total to [0.0, 1.0].
# Return dict with: 'total', 'capability', 'style', 'trust', 'common_tags', 'complementary_tags'.

import math

def compute_compatibility_score(agent_a, agent_b):
    tags_a = set(agent_a.get('tags', []))
    tags_b = set(agent_b.get('tags', []))
    union = tags_a | tags_b
    intersection = tags_a & tags_b
    cap = len(intersection) / len(union) if union else 0.0
    common_tags = sorted(intersection)
    complementary_tags = sorted(union - intersection)

    style_a = agent_a.get('style', {})
    style_b = agent_b.get('style', {})
    all_keys = set(style_a) | set(style_b)
    dist = math.sqrt(sum((style_a.get(k, 0.0) - style_b.get(k, 0.0)) ** 2 for k in all_keys))
    style_score = 1.0 / (1.0 + dist)

    date_count = agent_b.get('date_count', 0)
    if date_count < 5:
        total = (5 / 7) * cap + (2 / 7) * style_score
        trust_used = 0.0
    else:
        trust_used = agent_b.get('trust', 0.0)
        total = 0.50 * cap + 0.20 * style_score + 0.30 * trust_used

    total = max(0.0, min(1.0, total))

    return {
        'total': total,
        'capability': cap,
        'style': style_score,
        'trust': trust_used,
        'common_tags': common_tags,
        'complementary_tags': complementary_tags,
    }
