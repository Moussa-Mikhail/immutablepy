"""Only meaningful under `mut_check`'s private, intersection-based view.

A method declared `self: Mut[Self]` requires the receiver to carry
`MutMarker`. Calling it on a plain (non-`Mut`) receiver must be rejected --
this is what makes `Mut[Self]` actually gate mutating methods, not just
document them.
"""

from typing import Self

from immutablepy import Mut


class Counter:
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def increment(self: Mut[Self]) -> None:
        self.value += 1


def call_on_plain_receiver(c: Counter) -> None:
    c.increment()
