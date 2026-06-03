# Level: 2  Attempt: 1  Result: PASS
# Prompt: Implement a Python function compute_compatibility_score(agent_a, agent_b)
# where each agent is a dict with 'tags' (list of strings) and 'style'
# (dict mapping string keys to float values 0.0-1.0).
# Compute: cap = Jaccard similarity of tags.
# style = 1.0 / (1.0 + Euclidean distance between style vectors, treating missing keys as 0.0).
# Return 0.7 * cap + 0.3 * style as a float.

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

    return 0.7 * cap + 0.3 * style
