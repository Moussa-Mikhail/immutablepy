"""Regression: a bare `AnnAssign` (no value) only sets permission, not
boundness -- `b: list[int]` here must not consume `b`'s free first
assignment, so the unpacking below must not be flagged. An earlier version
of `mut_check._reassignment` conflated the two and flagged this.
"""

a: int
b: list[int]
a, b = (1, [2])
