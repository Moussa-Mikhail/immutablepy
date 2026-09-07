"""Pins mypy's current bug on `self: Mut[Self]` (see CLAUDE.md).

mypy hard-errors on any generic alias wrapping `Self` in an explicit `self`
annotation -- confirmed to be a mypy bug, not a real constraint (pyright and
`ty` both accept this fine). `mut_method` exists specifically so mutating
methods never need to write this pattern. If mypy ever stops erroring here,
revisit whether `mut_method` is still needed as a workaround.
"""

from typing import Self

from immutablepy import Mut


class Counter:
    def __init__(self, value: int) -> None:
        self.value = value

    def increment(self: Mut[Self]) -> None:
        self.value += 1
