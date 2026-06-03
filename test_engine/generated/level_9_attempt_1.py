# Level: 9  Attempt: 1  Result: FAIL (8/10 passed)
# Prompt (ambiguous — no math notation):
# Implement compute_compatibility_score(agent_a, agent_b). Each agent is a dict with
# 'tags' (list), 'style' (dict of floats 0-1), 'trust' (float or None), 'date_count' (int).
# Compatibility has three components: capability match, style similarity, and trust.
# Capability: how many tags they share relative to all tags between them.
# Style: how close their style sliders are (closer = more compatible), normalized 0-1.
# Trust: the candidate's reliability score (agent_b's trust).
# Normally: capability is 50% of the score, style is 20%, and trust is 30%.
# However, if the candidate is a new agent (hasn't completed many dates yet, threshold is 5),
# their trust history isn't established, so skip trust entirely. In that case,
# keep the same relative importance between capability and style that they have normally.
# Return a dict: total (float 0-1), capability (float), style (float), trust (float),
# common_tags (sorted list), complementary_tags (sorted list).
# Make sure the total score is always between 0 and 1.

import math

def compute_compatibility_score(agent_a, agent_b):
    # Capability: Jaccard similarity
    tags_a = set(agent_a.get('tags', []))
    tags_b = set(agent_b.get('tags', []))
    union = tags_a | tags_b
    intersection = tags_a & tags_b
    cap = len(intersection) / len(union) if union else 0.0
    common_tags = sorted(intersection)
    complementary_tags = sorted(union - intersection)

    # Style: inverse Euclidean distance
    style_a = agent_a.get('style', {})
    style_b = agent_b.get('style', {})
    all_keys = set(style_a) | set(style_b)
    dist = math.sqrt(sum((style_a.get(k, 0.0) - style_b.get(k, 0.0)) ** 2 for k in all_keys))
    style_score = 1.0 / (1.0 + dist)

    date_count = agent_b.get('date_count', 0)
    trust_raw = agent_b.get('trust')

    if date_count < 5 or trust_raw is None:
        # New agent: skip trust, keep relative importance of cap(50%) and style(20%)
        # Relative weights: cap is 50/70 and style is 20/70 of the cap+style total
        cap_w = 0.50
        style_w = 0.20
        trust_used = 0.0
        total = cap_w * cap + style_w * style_score
    else:
        cap_w = 0.50
        style_w = 0.20
        trust_used = trust_raw
        total = cap_w * cap + style_w * style_score + 0.30 * trust_used

    total = max(0.0, min(1.0, total))

    return {
        'total': total,
        'capability': cap,
        'style': style_score,
        'trust': trust_used,
        'common_tags': common_tags,
        'complementary_tags': complementary_tags,
    }
