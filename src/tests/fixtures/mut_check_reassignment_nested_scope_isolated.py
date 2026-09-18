"""A nested function's local shadows the outer one -- reassigning `x` in
`inner` doesn't touch `outer`'s `x` at all, but `inner`'s own second
assignment to its own `x` is still a real, separate violation, once
`inner`'s own scope is opted in via a `Mut` annotation of its own (`_y`
below) -- per CLAUDE.md's "Incremental adoption" ratchet, each function
scope is gated independently, so `outer` doesn't need its own `Mut` for
`inner`'s violation to be checked.
"""

from immutablepy import Mut


def outer() -> None:
    _x = 1

    # noinspection shadowing-names
    def inner() -> None:
        _x = 2
        _x = 3
        _y: Mut[int] = 0

    inner()
    print(_x)
