"""Exercises ordinary `Mut[T]` usage patterns.

Used by test_checker_compat.py to prove that mypy/pyright/plain-`ty` resolve
`Mut[T]` to plain `T` and raise zero diagnostics because of it — the whole
point of shipping a transparent public alias. `mut` and `mut_method` must be
just as transparent: real checkers see a plain identity decorator and a
plain identity function, respectively.

Deliberately excludes `Mut[Self]` on an *explicit* `self` parameter: mypy
hard-errors on any generic alias wrapping `Self` there (see CLAUDE.md). The
`@mut_method` decorator exists precisely so mutating methods never need that
explicit annotation in the first place — see `Counter.increment` below.
"""

from immutablepy import Mut, mut, mut_method


def append_one(numbers: Mut[list[int]]) -> None:
    numbers.append(1)


def make_numbers() -> Mut[list[int]]:
    return [1, 2, 3]


# noinspection type-hints
def nested(matrix: Mut[list[Mut[list[int]]]]) -> None:
    matrix.append([1])
    matrix[0].append(2)


class Counter:
    value: Mut[int]

    def __init__(self, value: int) -> None:
        self.value = value

    @mut_method
    def increment(self) -> None:
        self.value += 1


def reassign_local() -> int:
    total: Mut[int] = 0
    for i in range(3):
        total += i
    return total


def borrow_as_mut(counter: Counter) -> None:
    mutable_counter: Mut[Counter] = mut(counter)
    mutable_counter.increment()
