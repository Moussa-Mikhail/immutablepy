"""The immutable-type exemption extends to tuples.

Per CLAUDE.md, `tuple` is unconditionally immutable as a container -- no item
assignment, no `append`/`pop` -- so a plain `tuple[int, str]` (already
committed to that type by `y`'s own declaration) must satisfy
`Mut[tuple[int, str]]` the same as a plain `int` or `str` would: `Mut[T]` and
`T` grant nothing different for a type with no mutating members. See
mut_check_immutable_tuple_with_mutable_element.py for the same exemption
holding even when an element type is itself mutable.
"""

from immutablepy import Mut


def get_value() -> tuple[int, str]:
    return 1, "hi"


y: tuple[int, str] = get_value()
x: Mut[tuple[int, str]] = y
