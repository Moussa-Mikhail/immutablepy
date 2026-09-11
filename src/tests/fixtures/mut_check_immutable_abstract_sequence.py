"""The immutable-type exemption extends to read-only abstract types.

Per CLAUDE.md's "Generalizes to read-only abstract types": `Sequence[T]` has
no mutating members in its own definition (no `__setitem__`, no `append`) --
`Mut[Sequence[int]]` grants nothing a plain `Sequence[int]` reference
couldn't already do, so an aliased value of this type must satisfy it the
same as a concrete immutable type would. Contrast with
mut_check_mutable_sequence_still_rejected.py, where `MutableSequence[int]`
does declare mutating members and the exemption must not apply.
"""

from collections.abc import Sequence

from immutablepy import Mut


def get_value() -> Sequence[int]:
    return [1, 2, 3]


y: Sequence[int] = get_value()
x: Mut[Sequence[int]] = y
