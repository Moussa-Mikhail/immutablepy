"""Only meaningful under `mut_check`'s private, intersection-based view.

Regression: an ordinary function call must not be treated as fresh just
because it's a bare-name call. `get_list`'s *declared* return type is plain
`list[int]` -- that it happens to construct a fresh list internally is
invisible to (and irrelevant for) the caller; only a class-instantiation
call or a built-in mutable-container constructor carries a language-level
freshness guarantee. An earlier version of this filter treated any
bare-name call as fresh, which suppressed this correctly-real diagnostic
by inferring freshness from `get_list`'s body rather than its signature.
"""

from immutablepy import Mut


def get_list() -> list[int]:
    return [1, 2, 3]


x: Mut[list[int]] = get_list()
