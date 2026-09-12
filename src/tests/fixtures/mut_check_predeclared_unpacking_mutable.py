"""Only meaningful under `mut_check`'s private, intersection-based view.

Unlike mut_check_unpacking_without_mut.py, `a` is aliased here (from
`get_values()`, not a literal) and genuinely mutable (`list[int]`, not on
the immutable allowlist) -- so pre-declaring `Mut[list[int]]` is genuinely
needed, and aliasing it via unpacking is still correctly rejected. Not about
"was it modified after" at all; this is the same aliasing hazard as
mut_check_rejects_aliased_t.py, just via unpacking syntax.
"""

from immutablepy import Mut


def get_values() -> tuple[list[int], list[int]]:
    return [1], [2]


a: Mut[list[int]]
b: list[int]
a, b = get_values()
