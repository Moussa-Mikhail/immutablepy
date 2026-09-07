"""Only meaningful under the tool's private, intersection-based `ty` view.

`ty`'s own structural Protocol-conformance checking must catch a `Mut`
mismatch natively: a class with a plain field fails to satisfy a Protocol
declaring that field as `Mut`, with zero custom logic needed -- this is the
"resolved by the intersection-type approach" claim in CLAUDE.md's Protocols
section.
"""

from typing import Protocol

from immutablepy import Mut


class HasValue(Protocol):
    value: Mut[int]


class Locked:
    value: int


def use(x: HasValue) -> None: ...


use(Locked())
