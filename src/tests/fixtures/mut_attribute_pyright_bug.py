"""Pins pyright's current bug on a `Mut[...]`-typed instance attribute (see
test_pyright_bugs.py).

pyright rejects any instance attribute annotated `Mut[T]` (the public,
transparent `type Mut[T] = T` alias) with "Attribute type cannot use type
variable ... scoped to local method" -- it treats the alias's own type
parameter as bound to the local application site, not valid for something
that outlives it. Confirmed to be a pyright bug, not a real constraint (mypy
and `ty` both accept this fine).
"""

from immutablepy import Mut


class Box:
    def __init__(self) -> None:
        self.items: Mut[list[int]] = []
