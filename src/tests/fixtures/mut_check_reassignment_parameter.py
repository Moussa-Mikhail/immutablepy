"""A parameter is bound from the moment of the call -- unlike a fresh local,
there's no free first assignment inside the body, so even this single
reassignment is a violation without `Mut`, once `f`'s own scope is opted in
via a `Mut` annotation of its own (`_y` below), per CLAUDE.md's
"Incremental adoption" ratchet.
"""

from immutablepy import Mut


def f(_x: int) -> None:
    _y: Mut[int] = 0
    _x = 5
