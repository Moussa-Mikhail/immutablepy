"""Control case: a set/dict comprehension, a generator expression and a
lambda each get their own pushed/popped scope, so none of their targets or
parameters leak into the enclosing function -- the plain assignments below
reuse those same names, and each is that name's *first* binding in `f`'s
own scope (free), not a reassignment. `f` opts in via `_opt_in`, per
CLAUDE.md's "Incremental adoption" ratchet.
"""

from immutablepy import Mut


def f() -> None:
    _opt_in: Mut[int] = 0
    _squares = {n for n in range(3)}
    _identity = {k: k for k in range(3)}
    _total = sum(m for m in range(3))
    print(sorted([3, 1], key=lambda v: v * 2))
    n = 5
    k = 6
    m = 7
    v = 8
    print(n, k, m, v, _squares, _identity, _total)
