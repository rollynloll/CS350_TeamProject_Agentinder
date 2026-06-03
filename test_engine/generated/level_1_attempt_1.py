# Level: 1  Attempt: 1  Result: PASS
# Prompt: Implement a Python function compute_compatibility_score(agent_a, agent_b)
# where each agent is a dict with a 'tags' field (list of strings).
# Return a float representing the Jaccard similarity between their tag sets
# (intersection size divided by union size). Return 0.0 if both tag lists are empty.

def compute_compatibility_score(agent_a, agent_b):
    tags_a = set(agent_a.get('tags', []))
    tags_b = set(agent_b.get('tags', []))
    union = tags_a | tags_b
    if not union:
        return 0.0
    intersection = tags_a & tags_b
    return len(intersection) / len(union)
