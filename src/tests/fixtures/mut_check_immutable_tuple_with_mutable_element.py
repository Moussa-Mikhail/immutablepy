"""A tuple is exempt regardless of its element types.

`tuple[list[int], int]` holds a mutable element (`list[int]`), but the tuple
itself has no mutating operations at all -- no item assignment, no
`append`/`pop` -- so nothing about the tuple *binding* itself can ever expose
a way to restructure it, regardless of how many bindings point to it. Per
CLAUDE.md, this makes `tuple` unconditionally immutable regardless of what
it holds; mutating the `list` inside would instead be governed by that
element's own `Mut` annotation (`tuple[Mut[list[int]], int]`), independent
of this exemption.
"""

from immutablepy import Mut


def get_value() -> tuple[list[int], int]:
    return [1], 2


y: tuple[list[int], int] = get_value()
x: Mut[tuple[list[int], int]] = y
