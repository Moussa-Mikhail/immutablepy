"""Immutable-type exemption target for `mut_check`'s diagnostic filter.

Per CLAUDE.md's "Immutable types always satisfy `Mut[T]`": a plain `int` --
not a literal, not locally constructed, already committed to plain `int` by
`y`'s own declaration -- assigned to a `Mut[int]`-declared binding must still
type-check clean. `Mut[int]` and `int` grant exactly the same set of possible
operations (`int` has no mutating members at all), so there's no permission
gap for `Mut[int]` to protect in the first place. This is a different
exemption from the construction/literal one in test_mut_check_filter.py --
it's driven by the *type* being immutable, not by the value being freshly
constructed.
"""

from immutablepy import Mut


def get_value() -> int:
    return 5


y: int = get_value()
x: Mut[int] = y
