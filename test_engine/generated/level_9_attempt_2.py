# Level: 9  Attempt: 2  Result: PASS
# Same prompt as attempt 1 (retry after failure)
# The core issue: "keep same relative importance" requires re-normalization.
# cap:style = 0.50:0.20 = 5:2, so cap_w = 5/(5+2) = 5/7, style_w = 2/7.
# Attempt 2 corrects the re-normalization.

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
    trust_raw = agent_b.get('trust')

    if date_count < 5 or trust_raw is None:
        # Re-normalize: cap and style maintain ratio 0.50:0.20 = 5:2
        cap_w = 0.50 / (0.50 + 0.20)   # = 5/7
        style_w = 0.20 / (0.50 + 0.20)  # = 2/7
        trust_used = 0.0
        total = cap_w * cap + style_w * style_score
    else:
        trust_used = trust_raw
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
