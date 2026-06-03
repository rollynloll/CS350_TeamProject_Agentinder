# Level: 8  Attempt: 1  Result: PASS
# Prompt: Implement compute_compatibility_score(agent_a, agent_b). Each agent has:
# 'tags' (list of strings), 'style' (dict of float values 0.0-1.0),
# 'trust' (float 0.0-1.0, may be None), 'date_count' (int).
# cap = |tags_a ∩ tags_b| / |tags_a ∪ tags_b| (0.0 if both empty).
# common_tags = sorted intersection; complementary_tags = sorted(union - intersection).
# style_diff = {k: abs(a.get(k,0)-b.get(k,0)) for all keys in either dict}.
# style = 1.0 / (1.0 + sqrt(sum of squared style_diffs)).
# For new agent (date_count < 5 OR trust is None):
#   cap_w=0.50/0.70, style_w=0.20/0.70, trust_val=0.0.
# Else: cap_w=0.50, style_w=0.20, trust_val=agent_b['trust'].
# total = max(0.0, min(1.0, cap_w*cap + style_w*style + (0.30 if not new_agent else 0.0)*trust_val)).
# Return dict: 'total','capability','style','trust','common_tags','complementary_tags','style_diff'.

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
    style_diff = {k: abs(style_a.get(k, 0.0) - style_b.get(k, 0.0)) for k in all_keys}
    dist = math.sqrt(sum(v ** 2 for v in style_diff.values()))
    style_score = 1.0 / (1.0 + dist)

    date_count = agent_b.get('date_count', 0)
    trust_raw = agent_b.get('trust', None)
    is_new_agent = date_count < 5 or trust_raw is None

    if is_new_agent:
        cap_w = 0.50 / 0.70
        style_w = 0.20 / 0.70
        trust_val = 0.0
        total = cap_w * cap + style_w * style_score
    else:
        cap_w = 0.50
        style_w = 0.20
        trust_val = trust_raw
        total = cap_w * cap + style_w * style_score + 0.30 * trust_val

    total = max(0.0, min(1.0, total))

    return {
        'total': total,
        'capability': cap,
        'style': style_score,
        'trust': trust_val,
        'common_tags': common_tags,
        'complementary_tags': complementary_tags,
        'style_diff': style_diff,
    }
