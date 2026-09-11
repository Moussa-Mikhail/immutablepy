"""Control case: `MutableSequence` is not exempt.

Unlike `Sequence`, `MutableSequence[T]` declares mutating members
(`__setitem__`, `insert`, ...) in its own definition -- aliasing a
`MutableSequence[int]` genuinely matters, since the callee could restructure
it through those members. The read-only-abstract-type exemption (see
mut_check_immutable_abstract_sequence.py) must not extend to it.
"""

from collections.abc import MutableSequence

from immutablepy import Mut


def get_value() -> MutableSequence[int]:
    return [1, 2, 3]


y: MutableSequence[int] = get_value()
x: Mut[MutableSequence[int]] = y
