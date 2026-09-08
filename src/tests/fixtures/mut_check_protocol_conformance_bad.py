"""Only meaningful under `mut_check`'s private, intersection-based view.

Native structural Protocol-conformance checking must catch a `Mut`
mismatch: a class with a plain field fails to satisfy a Protocol declaring
that field as `Mut`, with zero custom logic needed -- this is the "resolved
by the intersection-type approach" claim in CLAUDE.md's Protocols section.
"""

from typing import Protocol

from immutablepy import Mut


class HasValue(Protocol):
    value: Mut[int]


class Locked:
    value: int


def use(_x: HasValue) -> None: ...


use(Locked())
