"""Immutable-type exemption target for `mut_check`'s diagnostic filter.

Per CLAUDE.md's "Immutable types always satisfy `Mut[T]`, aliased or not":
an aliased plain `int` -- not a fresh literal, not locally constructed --
assigned to a `Mut[int]`-declared binding must still type-check clean.
There's no mutation hazard to protect against: nothing can mutate an `int`
through any reference. This is a different exemption from the construction/
literal one in test_mut_check_filter.py -- it's driven by the *type* being
immutable, not by the value being freshly constructed.
"""

from immutablepy import Mut


def get_value() -> int:
    return 5


y: int = get_value()
x: Mut[int] = y
