"""Comprehension-internal names are scoped to the comprehension (PEP 289) and
tracked in their own pushed/popped scope -- never checked by this rule.
"""

result = [x for x in range(5)]
print(result)
