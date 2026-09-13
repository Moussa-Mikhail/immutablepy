"""Only meaningful under `mut_check`'s private, intersection-based view.

A `return` statement returning a freshly-created value (here, a list
comprehension) must satisfy a `Mut[...]`-declared return type -- the same
construction exemption as an `AnnAssign`, just at a different syntactic
position. `ty`'s diagnostic points at the returned expression's own
position regardless of it being a `return` value, so the same
position-matching logic covers this without any special-casing.
"""

from immutablepy import Mut


def make_evens() -> Mut[list[int]]:
    return [x for x in range(10) if x % 2 == 0]
