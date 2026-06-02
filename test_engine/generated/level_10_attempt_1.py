# Level: 10  Attempt: 1  Result: PASS
# Prompt (most ambiguous — no math at all, from stakeholder perspective):
# Implement compute_compatibility_score(agent_a, agent_b). Agents are dicts with
# 'tags', 'style', 'trust', 'date_count'.
# Score how compatible two agents are based on:
# 1. How much they overlap in capabilities (tags)
# 2. How similar their communication styles are (style sliders, lower distance = better)
# 3. How trustworthy the candidate (agent_b) is
# Capability should have the highest weight, trust the second most, style the least.
# If the candidate has few dates (under 5) or no trust score, ignore trust.
# When ignoring trust, redistribute its weight proportionally to cap and style.
# Return: {'total': float, 'capability': float, 'style': float, 'trust': float,
#          'common_tags': list, 'complementary_tags': list}
# Clamp total to [0, 1].

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

    # Weights: cap > trust > style
    # Prompt says "capability highest, trust second, style least"
    # This contradicts the SRS which says cap=50%, style=20%, trust=30%
    # Naive implementation from prompt description: cap=50%, trust=30%, style=20% → correct order
    # But "redistribute trust proportionally to cap and style" when new agent
    if date_count < 5 or trust_raw is None:
        # Redistribute trust (30%) proportionally: cap gets 30*50/70, style gets 30*20/70
        cap_w = 0.50 + 0.30 * (0.50 / 0.70)
        style_w = 0.20 + 0.30 * (0.20 / 0.70)
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
