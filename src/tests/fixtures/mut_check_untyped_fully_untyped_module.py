"""Fully untyped -- zero type annotations of any kind anywhere in this
module (not even a plain, non-`Mut` one). `"ignored"` mode skips the file
outright, before it's even parsed for violations; `"permissive"` mode still
parses it, but the ratchet's per-scope `Mut` gate empties it out the same
way, since a scope with zero annotations trivially has zero `Mut`
annotations too -- the two modes report identically here. `"strict"` mode
is the one that differs observably: it flags `total`'s reassignment
regardless.
"""


def legacy_function():
    total = 0
    for i in range(5):
        total = total + i
    return total
