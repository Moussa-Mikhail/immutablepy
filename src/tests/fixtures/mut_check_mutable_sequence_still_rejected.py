"""Control case: `MutableSequence` is not exempt.

Unlike `Sequence`, `MutableSequence[T]` declares mutating members
(`__setitem__`, `insert`, ...) in its own definition -- `Mut[MutableSequence[int]]`
genuinely permits more than plain `MutableSequence[int]` does (restructuring
through those members), so `y`'s already-committed plain type doesn't
satisfy it. The read-only-abstract-type exemption (see
mut_check_immutable_abstract_sequence.py) must not extend to it.
"""

from collections.abc import MutableSequence

from immutablepy import Mut


def get_value() -> MutableSequence[int]:
    return [1, 2, 3]


y: MutableSequence[int] = get_value()
x: Mut[MutableSequence[int]] = y
