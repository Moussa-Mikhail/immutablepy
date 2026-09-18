"""Typed (`x`/return both annotated), but `f`'s own scope has no `Mut`
anywhere -- under the default `"permissive"` mode, CLAUDE.md's "Incremental
adoption" ratchet skips it entirely; `"strict"` mode disables the ratchet
and flags `y`'s reassignment regardless.
"""


def f(x: int) -> int:
    y = 5
    y = 6
    return x + y
