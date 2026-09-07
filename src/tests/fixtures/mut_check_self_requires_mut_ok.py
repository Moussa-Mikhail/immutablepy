"""Only meaningful under `mut_check`'s private, intersection-based view.

Control case: the same `self: Mut[Self]` method, called on a `Mut[Counter]`
receiver, must be accepted -- the receiver carries `MutMarker`.
"""

from typing import Self

from immutablepy import Mut


class Counter:
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def increment(self: Mut[Self]) -> None:
        self.value += 1


def call_on_mut_receiver(c: Mut[Counter]) -> None:
    c.increment()
